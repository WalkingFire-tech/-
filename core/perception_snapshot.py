"""
统一感知快照 - 让所有模块共享同一个"我正在感知什么"的状态

核心洞察：proactivity/introspector/spirit_core各自独立感知系统状态，
没有共享的"系统感知快照"。本模块提供统一的感知接口，
让任何模块都能获取一致的当前系统状态。

设计原则：
1. 轻量级 - 只读取，不修改
2. 缓存 - 30秒内返回缓存结果，避免频繁查询
3. 按需 - 各维度独立获取，不强制加载所有维度
"""
import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class PerceptionSnapshot:
    timestamp: float = 0.0
    resource: Dict[str, Any] = field(default_factory=dict)
    knowledge: Dict[str, Any] = field(default_factory=dict)
    interaction: Dict[str, Any] = field(default_factory=dict)
    existence: Dict[str, Any] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=dict)
    identity: Dict[str, Any] = field(default_factory=dict)
    action_trace: Dict[str, Any] = field(default_factory=dict)

    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def summary(self) -> str:
        parts = []
        if self.resource:
            mem = self.resource.get("memory_usage", 0)
            parts.append(f"MEM={mem:.0%}")
        if self.knowledge:
            exp = self.knowledge.get("experience_count", 0)
            parts.append(f"EXP={exp}")
        if self.interaction:
            trust = self.interaction.get("trust_level", 0)
            parts.append(f"TRUST={trust:.1f}")
        if self.existence:
            state = self.existence.get("state", "?")
            parts.append(f"STATE={state}")
        if self.health:
            score = self.health.get("overall_score", 0)
            parts.append(f"HEALTH={score:.2f}")
        if self.action_trace:
            parts.append(f"ACTIONS={self.action_trace.get('total_actions', 0)}")
        return " | ".join(parts) if parts else "empty"


_ACTION_TRACE_LOCK = threading.Lock()
_ACTION_TRACE: Dict[str, Any] = {
    "last_action": "",
    "last_belief": "",
    "last_intent": "",
    "last_confidence": 0.0,
    "last_route": "",
    "total_actions": 0,
    "recent_actions": [],
    "belief_updates": [],
}


def update_action_trace(action: str, belief: str = "", intent: str = "",
                        confidence: float = 0.0, route: str = ""):
    global _ACTION_TRACE
    with _ACTION_TRACE_LOCK:
        _ACTION_TRACE["last_action"] = action
        _ACTION_TRACE["last_belief"] = belief
        _ACTION_TRACE["last_intent"] = intent
        _ACTION_TRACE["last_confidence"] = confidence
        _ACTION_TRACE["last_route"] = route
        _ACTION_TRACE["total_actions"] = _ACTION_TRACE.get("total_actions", 0) + 1
        
        recent = _ACTION_TRACE.get("recent_actions", [])
        recent.append({
            "action": action[:80],
            "belief": belief[:80],
            "intent": intent,
            "confidence": confidence,
            "route": route,
            "timestamp": time.time(),
        })
        _ACTION_TRACE["recent_actions"] = recent[-20:]
        
        if belief:
            beliefs = _ACTION_TRACE.get("belief_updates", [])
            beliefs.append({"belief": belief[:100], "timestamp": time.time()})
            _ACTION_TRACE["belief_updates"] = beliefs[-10:]


_CACHE: Optional[PerceptionSnapshot] = None
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 30.0


def _collect_resource() -> Dict[str, Any]:
    try:
        from core.resource_awareness.health_monitor import get_health_monitor
        hm = get_health_monitor()
        snap = hm.check()
        return {
            "memory_usage": snap.memory_usage,
            "thread_count": snap.thread_count,
            "mode": snap.mode.value,
            "cpu_percent": getattr(snap, 'cpu_percent', 0),
        }
    except Exception:
        return {}


def _collect_knowledge() -> Dict[str, Any]:
    result = {}
    try:
        db = DatabaseManager.get("data/experience_pool.db")
        result["experience_count"] = db.query_one("SELECT COUNT(*) FROM experiences")[0]
        result["recent_experiences"] = db.query_one("SELECT COUNT(*) FROM experiences WHERE timestamp > datetime('now', '-7 days')")[0]
    except Exception:
        pass
    try:
        db = DatabaseManager.get("data/truths.db")
        result["truth_count"] = db.query_one("SELECT COUNT(*) FROM truths")[0]
    except Exception:
        pass
    try:
        from core.knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()
        stats = kg.get_stats()
        result["graph_nodes"] = stats.get("total_nodes", 0)
        result["graph_connections"] = stats.get("total_connections", 0)
    except Exception:
        pass
    try:
        db = DatabaseManager.get("data/knowledge_store.db")
        result["knowledge_items"] = db.query_one("SELECT COUNT(*) FROM knowledge_items")[0]
    except Exception:
        pass
    return result


def _collect_interaction() -> Dict[str, Any]:
    try:
        from core.relationship.model import get_relationship_model
        rm = get_relationship_model()
        summary = rm.get_relationship_summary()
        return {
            "trust_level": summary.get("trust_level", 0.5),
            "total_interactions": summary.get("total_interactions", 0),
            "engagement": summary.get("engagement_score", 0.5),
        }
    except Exception:
        return {}


def _collect_existence() -> Dict[str, Any]:
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        metrics = el.metrics
        if metrics:
            return {
                "state": el.state.value if hasattr(el.state, 'value') else str(el.state),
                "silence_duration": metrics.silence_duration,
                "uptime_seconds": metrics.uptime_seconds,
                "total_cycles": metrics.total_cycles,
            }
    except Exception:
        pass
    return {}


def _collect_health() -> Dict[str, Any]:
    try:
        from core.self_assessment import self_assessment
        report = self_assessment.assess()
        overall = report.get("overall", {})
        return {
            "overall_score": overall.get("score", 0),
            "level": overall.get("level", "unknown"),
            "dimension_scores": overall.get("dimension_scores", {}),
        }
    except Exception:
        return {}


def _collect_identity() -> Dict[str, Any]:
    result = {}
    try:
        db = DatabaseManager.get("data/alignment_violations.db")
        result["open_deviations"] = db.query_one("SELECT COUNT(*) FROM deviations WHERE status='open'")[0]
        result["corrected_deviations"] = db.query_one("SELECT COUNT(*) FROM deviations WHERE status='corrected'")[0]
    except Exception:
        pass
    try:
        from core.spirit_core import spirit_core
        result["spirit_lessons"] = len(spirit_core.get_lessons_for_reflection())
    except Exception:
        pass
    return result


def _collect_action_trace() -> Dict[str, Any]:
    with _ACTION_TRACE_LOCK:
        trace = dict(_ACTION_TRACE)
        trace["recent_actions"] = [
            {**a, "age_seconds": round(time.time() - a.get("timestamp", time.time()), 1)}
            for a in trace.get("recent_actions", [])[-5:]
        ]
        return trace


def get_snapshot(force_refresh: bool = False) -> PerceptionSnapshot:
    global _CACHE
    with _CACHE_LOCK:
        if _CACHE and not force_refresh and _CACHE.age_seconds() < _CACHE_TTL:
            return _CACHE

        snapshot = PerceptionSnapshot(
            timestamp=time.time(),
            resource=_collect_resource(),
            knowledge=_collect_knowledge(),
            interaction=_collect_interaction(),
            existence=_collect_existence(),
            health=_collect_health(),
            identity=_collect_identity(),
            action_trace=_collect_action_trace(),
        )
        _CACHE = snapshot
        return snapshot


def get_dimension(dimension: str) -> Dict[str, Any]:
    snapshot = get_snapshot()
    return getattr(snapshot, dimension, {})