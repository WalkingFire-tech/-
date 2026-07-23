"""
LLM-符号混合推理器 — 符号规则优先，LLM兜底

推理策略：
1. 先用符号规则引擎求值（可靠、可解释、快速）
2. 若符号规则无匹配，再调用LLM推理（灵活、但不可靠）
3. 混合决策：符号规则置信度 * weight_symbolic + LLM置信度 * weight_llm

设计原则：
- 符号规则优先（R1: 可验证性优先）
- LLM仅作为兜底，不替代规则
- 推理过程通过explain()生成解释
- 渐进迁移：各模块按需使用，不强制
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.symbolic.rule import RuleDomain, RuleResult
from core.symbolic.engine import SymbolicRuleEngine, symbolic_engine

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.explainability.decision_explainer import explain
    from core.explainability.explanation_types import DecisionDomain
except ImportError:
    explain = None
    DecisionDomain = None


@dataclass
class HybridResult:
    source: str
    action: str
    confidence: float
    rule_name: str = ""
    llm_reasoning: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "action": self.action,
            "confidence": round(self.confidence, 3),
            "rule_name": self.rule_name,
            "llm_reasoning": self.llm_reasoning[:200] if self.llm_reasoning else "",
            "details": self.details,
        }


class HybridReasoner:
    """LLM-符号混合推理器"""

    def __init__(self, engine: SymbolicRuleEngine = None,
                 symbolic_weight: float = 0.8,
                 llm_weight: float = 0.2):
        self._engine = engine or symbolic_engine
        self.symbolic_weight = symbolic_weight
        self.llm_weight = llm_weight

    def reason(self, facts: Dict[str, Any],
               domain: Optional[RuleDomain] = None,
               llm_fallback: bool = True) -> HybridResult:
        """
        混合推理：符号优先，LLM兜底
        
        Args:
            facts: 事实字典
            domain: 可选规则域过滤
            llm_fallback: 是否在符号规则无匹配时使用LLM兜底
        
        Returns:
            HybridResult
        """
        symbolic_results = self._engine.evaluate(facts, domain)

        if symbolic_results:
            best = symbolic_results[0]
            result = HybridResult(
                source="symbolic",
                action=best.action,
                confidence=best.confidence * self.symbolic_weight,
                rule_name=best.rule_name,
                details={"evaluation_detail": best.evaluation_detail},
            )
            if explain and DecisionDomain:
                explain(
                    domain=DecisionDomain.PATH_SELECTION,
                    decision="hybrid_reason_symbolic",
                    outcome=best.action,
                    reasoning=f"符号规则'{best.rule_name}'匹配: {best.evaluation_detail}",
                    inputs=facts,
                    context={"confidence": best.confidence, "rule_name": best.rule_name},
                )
            return result

        if llm_fallback:
            llm_result = self._llm_infer(facts, domain)
            if llm_result:
                return llm_result

        return HybridResult(
            source="none",
            action="no_match",
            confidence=0.0,
            details={"reason": "符号规则和LLM均无匹配"},
        )

    def _llm_infer(self, facts: Dict[str, Any],
                   domain: Optional[RuleDomain] = None) -> Optional[HybridResult]:
        """LLM兜底推理（当符号规则无匹配时）"""
        try:
            from infrastructure.ollama_client import get_ollama_client
            client = get_ollama_client()
            if not client:
                return None

            domain_hint = domain.value if domain else "general"
            prompt = (
                f"Based on these facts, determine the best action.\n"
                f"Domain: {domain_hint}\n"
                f"Facts: {facts}\n"
                f"Respond with: ACTION: <action_name> CONFIDENCE: <0-1> REASONING: <brief explanation>"
            )

            response = client.chat(prompt, model="qwen2.5-coder:7b", timeout=10)
            if not response:
                return None

            action, confidence, reasoning = self._parse_llm_response(response)
            if not action:
                return None

            result = HybridResult(
                source="llm",
                action=action,
                confidence=confidence * self.llm_weight,
                llm_reasoning=reasoning,
            )

            if explain and DecisionDomain:
                explain(
                    domain=DecisionDomain.PATH_SELECTION,
                    decision="hybrid_reason_llm",
                    outcome=action,
                    reasoning=f"LLM兜底推理: {reasoning[:100]}",
                    inputs=facts,
                    context={"confidence": confidence, "domain": domain_hint},
                )

            return result

        except Exception as e:
            logger.debug(f"LLM兜底推理跳过: {e}")
            return None

    @staticmethod
    def _parse_llm_response(response: str) -> tuple:
        """解析LLM响应为(action, confidence, reasoning)"""
        action = ""
        confidence = 0.5
        reasoning = ""

        for line in response.split("\n"):
            line = line.strip()
            if line.upper().startswith("ACTION:"):
                action = line.split(":", 1)[1].strip()
            elif line.upper().startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            elif line.upper().startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        return (action, confidence, reasoning)


hybrid_reasoner = HybridReasoner()