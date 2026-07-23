"""
系统元认知快照 — 跨模块状态聚合

复用现有数据源，不新建收集器：
- SelfModel.snapshot(): 12维认知维度
- ResourceSnapshot: 资源状态
- AdaptiveGovernor决策日志: 资源分配决策
- CognitiveDispatcher调度历史: 路由决策
- LoopMixin指标: 各模块闭环运行状态
- Explainability: 最近决策解释
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ModuleHealth:
    name: str
    status: str = "unknown"
    consecutive_failures: int = 0
    last_success_rate: float = 0.0
    avg_cycle_duration_ms: float = 0.0
    cooldown_remaining_s: float = 0.0


@dataclass
class ResourceTrend:
    memory_direction: str = "stable"
    cpu_direction: str = "stable"
    gpu_vram_direction: str = "stable"
    mode_trend: str = "normal"
    oom_events: int = 0


@dataclass
class DispatchStats:
    total_dispatches: int = 0
    fast_ratio: float = 0.0
    slow_ratio: float = 0.0
    learning_ratio: float = 0.0
    avg_elapsed_ms: float = 0.0
    urgency_overrides: int = 0


@dataclass
class L5Stats:
    total_runs: int = 0
    patches_generated: int = 0
    auto_approved: int = 0
    completed: int = 0
    failed: int = 0
    success_rate: float = 0.0
    strategy_adjustments: int = 0


@dataclass
class SystemMetacognitiveSnapshot:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    overall_health: float = 0.5
    operating_mode: str = "normal"
    self_model_health: float = 0.5
    self_model_confidence: float = 0.5

    resource: ResourceTrend = field(default_factory=ResourceTrend)
    dispatch: DispatchStats = field(default_factory=DispatchStats)
    l5: L5Stats = field(default_factory=L5Stats)

    module_healths: List[ModuleHealth] = field(default_factory=list)
    recent_explanations_count: int = 0
    active_alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_health": round(self.overall_health, 3),
            "operating_mode": self.operating_mode,
            "self_model_health": round(self.self_model_health, 3),
            "self_model_confidence": round(self.self_model_confidence, 3),
            "resource": {
                "memory_direction": self.resource.memory_direction,
                "cpu_direction": self.resource.cpu_direction,
                "gpu_vram_direction": self.resource.gpu_vram_direction,
                "mode_trend": self.resource.mode_trend,
                "oom_events": self.resource.oom_events,
            },
            "dispatch": {
                "total": self.dispatch.total_dispatches,
                "fast_ratio": round(self.dispatch.fast_ratio, 3),
                "slow_ratio": round(self.dispatch.slow_ratio, 3),
                "learning_ratio": round(self.dispatch.learning_ratio, 3),
                "avg_elapsed_ms": round(self.dispatch.avg_elapsed_ms, 1),
                "urgency_overrides": self.dispatch.urgency_overrides,
            },
            "l5": {
                "total_runs": self.l5.total_runs,
                "completed": self.l5.completed,
                "failed": self.l5.failed,
                "success_rate": round(self.l5.success_rate, 3),
                "strategy_adjustments": self.l5.strategy_adjustments,
            },
            "module_healths": [
                {"name": m.name, "status": m.status, "failures": m.consecutive_failures, "success_rate": round(m.last_success_rate, 3)}
                for m in self.module_healths
            ],
            "recent_explanations_count": self.recent_explanations_count,
            "active_alerts": self.active_alerts,
        }

    @staticmethod
    def collect() -> "SystemMetacognitiveSnapshot":
        snap = SystemMetacognitiveSnapshot()

        try:
            from core.self.model import get_self_model
            sm = get_self_model().snapshot()
            snap.self_model_health = sm.get("health", {}).get("score", 0.5)
            snap.self_model_confidence = sm.get("health", {}).get("confidence", 0.5)
        except Exception:
            pass

        try:
            from core.resource_awareness.health_monitor import health_monitor
            rs = health_monitor.check()
            snap.operating_mode = rs.mode.value if hasattr(rs.mode, "value") else str(rs.mode)
            snap.resource.memory_direction = "rising" if rs.memory_usage > 0.8 else "stable"
            snap.resource.cpu_direction = "high" if rs.cpu_percent > 80 else "normal"
            snap.resource.gpu_vram_direction = "tight" if rs.gpu_vram_total_gb > 0 and rs.gpu_vram_used_gb / rs.gpu_vram_total_gb > 0.85 else "ok"
        except Exception:
            pass

        try:
            from core.resource_awareness.adaptive_governor import adaptive_governor
            log = adaptive_governor.get_decision_log(20)
            recent_modes = [d.get("mode", "normal") for d in log]
            if recent_modes.count("emergency") > len(recent_modes) * 0.3:
                snap.resource.mode_trend = "degrading"
            elif recent_modes.count("normal") > len(recent_modes) * 0.7:
                snap.resource.mode_trend = "stable"
        except Exception:
            pass

        try:
            from core.explainability.decision_explainer import get_recent_explanations
            exps = get_recent_explanations(limit=50)
            snap.recent_explanations_count = len(exps)
        except Exception:
            pass

        snap.overall_health = (snap.self_model_health + snap.self_model_confidence) / 2
        if snap.operating_mode == "emergency":
            snap.overall_health *= 0.5
        elif snap.operating_mode == "conservative":
            snap.overall_health *= 0.8

        return snap