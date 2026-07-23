"""
路径选择解释器 — 为认知路由决策生成解释

覆盖决策点：
1. 资源保护快速路径
2. 意图识别路由（fast/slow/learning）
3. 紧迫度覆盖路由
4. 快速路径分支选择
"""

from typing import Any, Dict, List, Optional

from core.explainability.explanation_types import DecisionDomain, Explanation
from core.explainability.decision_explainer import explain


class PathExplainer:
    """路径选择决策解释器"""

    DOMAIN = DecisionDomain.PATH_SELECTION

    @staticmethod
    def explain_resource_protection(
        triggered: bool,
        memory_usage: float = 0.0,
        health_score: float = 1.0,
        reason: str = "",
    ) -> Explanation:
        if not triggered:
            reasoning = f"资源正常: 内存{memory_usage:.1%}, 健康度{health_score:.1%}"
        else:
            reasoning = f"资源保护触发: {reason or f'内存{memory_usage:.1%}/健康度{health_score:.1%}'}，走轻量响应"

        return explain(
            domain=PathExplainer.DOMAIN,
            decision="resource_protection",
            outcome="lightweight" if triggered else "normal",
            reasoning=reasoning,
            inputs={"memory_usage": memory_usage, "health_score": health_score},
        )

    @staticmethod
    def explain_route_decision(
        route: str,
        intent_type: str,
        complexity: float = 0.0,
        confidence: float = 0.0,
        learning_threshold: float = 0.5,
    ) -> Explanation:
        route_reasons = {
            "fast": f"意图'{intent_type}'属于简单类型，走快速路径",
            "slow": f"意图'{intent_type}'需要完整认知流程(复杂度{complexity:.2f})",
            "learning": f"置信度{confidence:.2f}<学习阈值{learning_threshold:.2f}或学习触发，走学习路径",
        }
        reasoning = route_reasons.get(route, f"路由到'{route}'")

        return explain(
            domain=PathExplainer.DOMAIN,
            decision="route_decision",
            outcome=route,
            reasoning=reasoning,
            inputs={"intent_type": intent_type, "complexity": complexity, "confidence": confidence},
            context={"learning_threshold": learning_threshold},
            alternatives=[r for r in ["fast", "slow", "learning"] if r != route],
        )

    @staticmethod
    def explain_urgency_override(
        original_route: str,
        overridden_route: str,
        urgency: float,
        urgency_source: str = "keyword",
    ) -> Explanation:
        reasoning = (
            f"高紧迫度({urgency:.1f})覆盖: {original_route}→{overridden_route}"
            f"（来源: {urgency_source}）"
        )

        return explain(
            domain=PathExplainer.DOMAIN,
            decision="urgency_override",
            outcome=overridden_route,
            reasoning=reasoning,
            inputs={"original_route": original_route, "urgency": urgency},
            context={"urgency_source": urgency_source},
        )

    @staticmethod
    def explain_fast_path_branch(
        intent_type: str,
        handler: str,
        handled: bool = True,
        fallback_reason: str = "",
    ) -> Explanation:
        if handled:
            reasoning = f"快速路径处理'{intent_type}': {handler}"
        else:
            reasoning = f"快速路径无法处理'{intent_type}': {fallback_reason or '无匹配处理器'}，降级到慢路径"

        return explain(
            domain=PathExplainer.DOMAIN,
            decision="fast_path_branch",
            outcome=handler if handled else "fallback_slow",
            reasoning=reasoning,
            inputs={"intent_type": intent_type, "handled": handled},
        )