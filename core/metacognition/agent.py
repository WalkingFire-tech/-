"""
元认知智能体 — 系统级元认知的核心引擎

职责：
1. 定期收集系统元认知快照
2. 运行趋势分析检测异常
3. 根据异常严重度决定干预级别
4. 通过回调/事件执行干预
5. 评估干预效果

干预级别（4级递进）：
- Level 0: 仅记录（INFO级异常）
- Level 1: 告警通知（WARNING级异常）
- Level 2: 建议调整（建议人类确认）
- Level 3: 自动干预（CRITICAL级异常，系统自保）

设计原则：
- 复用LoopMixin的冷却/降级机制
- 干预决策通过explain()生成解释
- 非侵入式：通过回调/事件通知，不直接修改被管理模块
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.loop_mixin import LoopMixin, LoopStatus
from core.metacognition.snapshot import SystemMetacognitiveSnapshot
from core.metacognition.trend_analyzer import TrendAnalyzer, TrendResult, AlertSeverity

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
class Intervention:
    level: int
    dimension: str
    action: str
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    executed: bool = False
    result: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "dimension": self.dimension,
            "action": self.action,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "executed": self.executed,
            "result": self.result,
        }


class MetacognitiveAgent(LoopMixin):
    """
    元认知智能体 — "观察观察者"的系统级元认知
    
    定期巡检系统状态，检测异常趋势，决定干预级别。
    """

    COOLDOWN_SECONDS = 60
    MAX_INTERVENTION_HISTORY = 100

    def __init__(self):
        super().__init__(name="metacognitive_agent", cooldown_seconds=self.COOLDOWN_SECONDS)
        self._analyzer = TrendAnalyzer(window_size=20)
        self._interventions: List[Intervention] = []
        self._callbacks: Dict[str, List[Callable]] = {}
        self._last_check_time: float = 0
        self._check_count: int = 0
        self._reasoning_fingerprints: List[Dict[str, Any]] = []
        self._MAX_FINGERPRINTS = 50

    def register_callback(self, event_type: str, callback: Callable) -> None:
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def run_check(self) -> Dict[str, Any]:
        with self.loop_context():
            return self._do_check()

    def _do_check(self) -> Dict[str, Any]:
        snap = SystemMetacognitiveSnapshot.collect()
        self._analyzer.add_snapshot(snap)
        self._check_count += 1
        self._last_check_time = time.time()

        trends = self._analyzer.analyze()
        interventions = self._decide_interventions(trends)

        for iv in interventions:
            self._execute_intervention(iv)

        report = {
            "status": "checked",
            "check_count": self._check_count,
            "overall_health": snap.overall_health,
            "operating_mode": snap.operating_mode,
            "trends_found": len(trends),
            "interventions": len(interventions),
            "trend_details": [t.to_dict() for t in trends],
            "intervention_details": [iv.to_dict() for iv in interventions],
        }

        if interventions:
            logger.info(f"🧠 元认知巡检: {len(interventions)}项干预 (健康度{snap.overall_health:.2f})")
        else:
            logger.debug(f"🧠 元认知巡检: 正常 (健康度{snap.overall_health:.2f})")

        return report

    def _decide_interventions(self, trends: List[TrendResult]) -> List[Intervention]:
        interventions = []
        for trend in trends:
            if trend.severity == AlertSeverity.INFO:
                continue

            level = self._severity_to_level(trend.severity)
            action = self._suggest_action(trend)

            iv = Intervention(
                level=level,
                dimension=trend.dimension,
                action=action,
                reason=trend.message,
            )
            interventions.append(iv)

            if explain and DecisionDomain:
                explain(
                    domain=DecisionDomain.RESOURCE_ALLOCATION,
                    decision="metacognitive_intervention",
                    outcome=action,
                    reasoning=trend.message,
                    inputs={"dimension": trend.dimension, "severity": trend.severity.value},
                    context={"level": level},
                )

        return interventions

    def _severity_to_level(self, severity: AlertSeverity) -> int:
        mapping = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.CRITICAL: 3,
        }
        return mapping.get(severity, 0)

    def _suggest_action(self, trend: TrendResult) -> str:
        dimension_actions = {
            "overall_health": {
                "declining": "suggest_increase_monitoring_frequency",
                "improving": "no_action",
            },
            "operating_mode": {
                "degrading": "trigger_resource_optimization",
            },
            "self_model_health": {
                "low": "suggest_self_repair",
            },
            "self_model_confidence": {
                "low": "suggest_external_learning",
            },
            "l5_success_rate": {
                "declining": "suggest_raise_l5_threshold",
            },
            "resource_health_correlation": {
                "correlated_decline": "trigger_emergency_resource_management",
            },
        }
        actions = dimension_actions.get(trend.dimension, {})
        return actions.get(trend.direction, "monitor")

    def _execute_intervention(self, iv: Intervention) -> None:
        event_type = f"metacognitive_level_{iv.level}"
        callbacks = self._callbacks.get(event_type, [])

        for cb in callbacks:
            try:
                result = cb(iv)
                iv.executed = True
                iv.result = str(result) if result else "executed"
            except Exception as e:
                iv.result = f"callback_error: {e}"
                logger.warning(f"元认知干预回调失败: {e}")

        self._interventions.append(iv)
        if len(self._interventions) > self.MAX_INTERVENTION_HISTORY:
            self._interventions.pop(0)

    def get_status(self) -> Dict[str, Any]:
        return {
            "check_count": self._check_count,
            "last_check_time": self._last_check_time,
            "window_size": self._analyzer.get_window_size(),
            "total_interventions": len(self._interventions),
            "recent_interventions": [iv.to_dict() for iv in self._interventions[-5:]],
            "loop_status": self._loop_status.value if self._loop_status else "unknown",
        }

    def get_intervention_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [iv.to_dict() for iv in self._interventions[-limit:]]

    def record_reasoning_fingerprint(self, intent_type: str, route: str, source: str, confidence: float) -> None:
        """记录一次推理的'认知指纹'，用于自厌检测"""
        fp = {
            "intent_type": intent_type,
            "route": route,
            "source": source,
            "confidence": round(confidence, 2),
            "timestamp": time.time(),
        }
        self._reasoning_fingerprints.append(fp)
        if len(self._reasoning_fingerprints) > self._MAX_FINGERPRINTS:
            self._reasoning_fingerprints.pop(0)

    def detect_stagnation(self, window: int = 10) -> Dict[str, Any]:
        """
        自厌检测器：检测推理模板重复
        
        当系统连续N次使用相同的推理模式时，返回"自厌信号"，
        驱动系统尝试新路径——哪怕更慢、更笨拙，但它是新的。
        
        核心哲学：不是"我要做到完美"，而是"我无法忍受自己的重复"。
        """
        recent = self._reasoning_fingerprints[-window:] if len(self._reasoning_fingerprints) >= 3 else []
        if len(recent) < 3:
            return {"stagnation_detected": False, "reason": "insufficient_data"}

        intent_counts: Dict[str, int] = {}
        route_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        for fp in recent:
            intent_counts[fp["intent_type"]] = intent_counts.get(fp["intent_type"], 0) + 1
            route_counts[fp["route"]] = route_counts.get(fp["route"], 0) + 1
            source_counts[fp["source"]] = source_counts.get(fp["source"], 0) + 1

        total = len(recent)
        dominant_intent = max(intent_counts.values()) / total if intent_counts else 0
        dominant_route = max(route_counts.values()) / total if route_counts else 0
        dominant_source = max(source_counts.values()) / total if source_counts else 0

        stagnation_score = (dominant_intent * 0.3 + dominant_route * 0.3 + dominant_source * 0.4)

        if stagnation_score > 0.8:
            top_intent = max(intent_counts, key=intent_counts.get)
            top_route = max(route_counts, key=route_counts.get)
            top_source = max(source_counts, key=source_counts.get)

            perturbation = self._suggest_perturbation(top_intent, top_route, top_source)

            logger.info(
                f"🔄 自厌检测: 停滞分数={stagnation_score:.2f}, "
                f"主导模式=intent:{top_intent}/route:{top_route}/source:{top_source}, "
                f"扰动建议={perturbation['action']}"
            )

            return {
                "stagnation_detected": True,
                "stagnation_score": round(stagnation_score, 2),
                "dominant_pattern": {
                    "intent_type": top_intent,
                    "route": top_route,
                    "source": top_source,
                },
                "perturbation": perturbation,
            }

        return {
            "stagnation_detected": False,
            "stagnation_score": round(stagnation_score, 2),
        }

    def _suggest_perturbation(self, intent: str, route: str, source: str) -> Dict[str, Any]:
        """基于停滞模式建议扰动方向"""
        if route == "fast":
            return {
                "action": "force_deep_path",
                "reason": f"连续走快速路径，强制尝试深度推理",
            }
        if route == "slow":
            return {
                "action": "try_alternative_source",
                "reason": f"连续依赖{source}，尝试其他来源",
            }
        return {
            "action": "change_reasoning_strategy",
            "reason": f"推理模式重复(intent={intent})，切换策略",
        }


metacognitive_agent = MetacognitiveAgent()