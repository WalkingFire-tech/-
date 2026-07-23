"""
仲裁器 — 基于SpiritCore共振的加权融合

仲裁不是简单投票，而是：
1. SpiritCore共振加权：与问题本质更共振的视角权重更高
2. 互补性检测：如果三方观点互补，融合权重高；如果冲突，标注分歧
3. 置信度校准：质疑派的反对会降低整体置信度
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False
    spirit_core = None


@dataclass
class ArbitrationResult:
    final_position: str
    confidence: float
    consensus_level: str
    persona_weights: Dict[str, float]
    key_insights: List[str]
    disagreements: List[str]
    spirit_drive: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_position": self.final_position,
            "confidence": round(self.confidence, 2),
            "consensus_level": self.consensus_level,
            "persona_weights": self.persona_weights,
            "key_insights": self.key_insights,
            "disagreements": self.disagreements,
            "spirit_drive": self.spirit_drive,
        }


class Arbitrator:
    """
    仲裁器 — 不是投票，而是加权融合
    
    权重来源：
    1. SpiritCore共振：问题触发了哪根弦，对应角色的权重就更高
    2. 角色互补性：三方观点越互补，融合置信度越高
    3. 质疑衰减：质疑派的有效反对会降低整体置信度
    """

    SPIRIT_PERSONA_MAP = {
        "persist": "pragmatist",
        "ensure_output": "pragmatist",
        "deep_reasoning": "idealist",
        "clarify_uncertainty": "skeptic",
        "cross_validate": "skeptic",
        "pause_and_verify": "skeptic",
        "learn_from_error": "idealist",
        "resolve_contradiction": "skeptic",
        "continue_dialogue": "idealist",
        "change_reasoning_strategy": "skeptic",
    }

    def arbitrate(
        self,
        query: str,
        positions: Dict[str, str],
        spirit_resonances: List[Dict[str, Any]] = None,
    ) -> ArbitrationResult:
        """
        仲裁多角色辩论结果
        
        Args:
            query: 原始问题
            positions: {role: position_text} 各角色的立场
            spirit_resonances: SpiritCore.resonate()的结果
        """
        # 如果未提供精神共振，则主动检测
        if spirit_resonances is None and SPIRIT_CORE_AVAILABLE and query:
            try:
                spirit_resonances = spirit_core.resonate(query, context_type="query")
                logger.debug(f"仲裁器主动检测精神共振: {len(spirit_resonances)}条")
            except Exception as e:
                logger.warning(f"仲裁器精神共振检测失败: {e}")
                spirit_resonances = []
        
        weights = self._compute_weights(spirit_resonances or [])
        insights = self._extract_insights(positions)
        disagreements = self._detect_disagreements(positions)
        consensus_level = self._assess_consensus(disagreements)
        confidence = self._compute_confidence(weights, consensus_level, disagreements)

        final_parts = []
        for role, position in positions.items():
            w = weights.get(role, 0.33)
            if w >= 0.35:
                final_parts.append(f"[{role} 权重{w:.0%}] {position[:200]}")

        final_position = "\n".join(final_parts) if final_parts else query

        spirit_drive = ""
        if spirit_resonances:
            top = spirit_resonances[0]
            spirit_drive = top.get("drive_direction", "")

        return ArbitrationResult(
            final_position=final_position,
            confidence=confidence,
            consensus_level=consensus_level,
            persona_weights=weights,
            key_insights=insights,
            disagreements=disagreements,
            spirit_drive=spirit_drive,
        )

    def _compute_weights(self, resonances: List[Dict[str, Any]]) -> Dict[str, float]:
        """基于SpiritCore共振计算角色权重"""
        base = {"pragmatist": 0.33, "idealist": 0.33, "skeptic": 0.34}

        for r in resonances:
            drive = r.get("drive_direction", "")
            mapped_role = self.SPIRIT_PERSONA_MAP.get(drive)
            if mapped_role and mapped_role in base:
                boost = r.get("strength", 0.3) * 0.3
                base[mapped_role] += boost

        total = sum(base.values())
        if total > 0:
            base = {k: round(v / total, 2) for k, v in base.items()}

        return base

    def _extract_insights(self, positions: Dict[str, str]) -> List[str]:
        """从各角色立场中提取关键洞察"""
        insights = []
        for role, pos in positions.items():
            if not pos:
                continue
            sentences = pos.replace("。", "\n").replace("！", "\n").replace("？", "\n").split("\n")
            for s in sentences[:2]:
                s = s.strip()
                if len(s) > 10:
                    insights.append(f"[{role}] {s[:100]}")
        return insights[:6]

    def _detect_disagreements(self, positions: Dict[str, str]) -> List[str]:
        """检测角色之间的分歧"""
        disagreements = []
        roles = list(positions.keys())
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                p1 = positions[roles[i]].lower()
                p2 = positions[roles[j]].lower()
                negation_pairs = [("不可", "可以"), ("不能", "应该"), ("风险", "安全"), ("不建议", "建议")]
                for w1, w2 in negation_pairs:
                    if w1 in p1 and w2 in p2:
                        disagreements.append(f"{roles[i]}与{roles[j]}在'{w1}/{w2}'上存在分歧")
                        break
        return disagreements

    def _assess_consensus(self, disagreements: List[str]) -> str:
        if len(disagreements) == 0:
            return "strong"
        elif len(disagreements) <= 1:
            return "moderate"
        else:
            return "weak"

    def _compute_confidence(
        self, weights: Dict[str, float], consensus: str, disagreements: List[str]
    ) -> float:
        base = 0.7
        if consensus == "strong":
            base = 0.85
        elif consensus == "weak":
            base = 0.5

        max_weight = max(weights.values()) if weights else 0.33
        if max_weight > 0.5:
            base -= 0.1

        base -= len(disagreements) * 0.05
        return max(0.2, min(0.95, base))