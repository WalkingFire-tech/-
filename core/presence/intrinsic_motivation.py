"""
IntrinsicMotivationEngine — 内在动机引擎

不是定时器，是"我想做什么"。
读取 SelfModel 的成长方向和路径自信度，生成主动探索计划。

与 CuriosityEngine 的区别：
- CuriosityEngine: 发现"我不知道什么"（缺口感知）
- IntrinsicMotivationEngine: 决定"我要去做什么"（行动决策）

设计原则：
- 动机来源于SelfModel，不来源于随机数
- 在GROWING状态时执行，不抢占AWAKE状态
- 执行结果回馈SelfModel，形成闭环
"""
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MotivationType(Enum):
    GROWTH_EDGE_PURSUIT = auto()
    CAPABILITY_RECOVERY = auto()
    KNOWLEDGE_GAP_FILL = auto()
    SKILL_CONSOLIDATION = auto()


@dataclass
class Motivation:
    motivation_type: MotivationType
    topic: str
    reason: str
    priority: float
    source: str
    created_at: float = field(default_factory=time.time)
    executed: bool = False
    result: Optional[str] = None


class IntrinsicMotivationEngine:
    """
    内在动机引擎 — 基于SelfModel状态生成主动探索计划

    核心循环：
    1. 读取SelfModel的成长方向和路径自信度
    2. 生成动机列表（按优先级排序）
    3. 在GROWING状态时执行top动机
    4. 执行结果回馈SelfModel
    """

    def __init__(self):
        self._motivations: List[Motivation] = []
        self._execution_history: List[Dict[str, Any]] = []
        self._last_generation: float = 0.0
        self._generation_interval: float = 30.0
        self._update_count: int = 0

    def generate_motivations(self) -> List[Motivation]:
        """
        从SelfModel状态生成动机列表

        动机来源：
        1. growth_edges — "我想学什么"
        2. DEGRADED capabilities — "我需要恢复什么"
        3. limitations — "我知道什么边界"
        """
        self._update_count += 1
        now = time.time()

        if now - self._last_generation < self._generation_interval:
            return self._motivations

        self._last_generation = now
        new_motivations = []

        try:
            from core.self.model import get_self_model, ConfidenceLevel
            sm = get_self_model()

            for edge in sm.get_active_growth_edges():
                new_motivations.append(Motivation(
                    motivation_type=MotivationType.GROWTH_EDGE_PURSUIT,
                    topic=edge.topic,
                    reason="growth_edge: {}".format(edge.motivation[:80]),
                    priority=edge.priority / 10.0,
                    source="SelfModel.growth_edges",
                ))

            for name, cap in sm._domain_capabilities.items():
                if cap.confidence == ConfidenceLevel.DEGRADED:
                    path_name = name.replace("path_", "")
                    new_motivations.append(Motivation(
                        motivation_type=MotivationType.CAPABILITY_RECOVERY,
                        topic=path_name,
                        reason="degraded: {} ({:.1%} success)".format(path_name, cap.success_rate),
                        priority=0.8,
                        source="SelfModel._domain_capabilities",
                    ))

            for name, lim in sm._domain_limitations.items():
                if lim.is_temporary and lim.uncertainty < 0.5:
                    new_motivations.append(Motivation(
                        motivation_type=MotivationType.KNOWLEDGE_GAP_FILL,
                        topic=lim.domain,
                        reason="limitation: {}".format(lim.description[:80]),
                        priority=0.6,
                        source="SelfModel._domain_limitations",
                    ))

        except Exception as e:
            logger.debug("IntrinsicMotivation generate failed: {}".format(e))

        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            curiosity = get_curiosity_engine()
            gaps = curiosity.perceive_gaps()
            for gap in gaps[:3]:
                if hasattr(gap, 'topic') and hasattr(gap, 'urgency'):
                    new_motivations.append(Motivation(
                        motivation_type=MotivationType.KNOWLEDGE_GAP_FILL,
                        topic=gap.topic,
                        reason="curiosity_gap: {}".format(gap.topic[:80]),
                        priority=0.5,
                        source="CuriosityEngine",
                    ))
        except Exception:
            pass

        new_motivations.sort(key=lambda m: m.priority, reverse=True)
        self._motivations = new_motivations[:10]

        if self._motivations:
            logger.debug(
                "IntrinsicMotivation: {} motivations generated, top={}".format(
                    len(self._motivations),
                    self._motivations[0].topic[:40] if self._motivations else "none"
                )
            )

        return self._motivations

    def execute_top_motivation(self) -> Optional[Dict[str, Any]]:
        """
        执行优先级最高的动机

        在GROWING状态时由ExistenceLayer调用
        """
        motivations = self.generate_motivations()
        if not motivations:
            return None

        pending = [m for m in motivations if not m.executed]
        if not pending:
            return None

        motivation = pending[0]
        result = self._execute(motivation)
        motivation.executed = True
        motivation.result = result.get("status", "unknown")

        self._execution_history.append({
            "type": motivation.motivation_type.name,
            "topic": motivation.topic,
            "result": motivation.result,
            "timestamp": time.time(),
        })
        self._execution_history = self._execution_history[-50:]

        return result

    def _execute(self, motivation: Motivation) -> Dict[str, Any]:
        """根据动机类型执行不同策略"""
        if motivation.motivation_type == MotivationType.CAPABILITY_RECOVERY:
            return self._execute_capability_recovery(motivation)
        elif motivation.motivation_type == MotivationType.GROWTH_EDGE_PURSUIT:
            return self._execute_growth_pursuit(motivation)
        elif motivation.motivation_type == MotivationType.KNOWLEDGE_GAP_FILL:
            return self._execute_knowledge_gap(motivation)
        elif motivation.motivation_type == MotivationType.SKILL_CONSOLIDATION:
            return self._execute_skill_consolidation(motivation)
        return {"status": "unknown_type", "topic": motivation.topic}

    def _execute_capability_recovery(self, motivation: Motivation) -> Dict[str, Any]:
        """尝试恢复降级路径 — 检查路径是否已恢复"""
        try:
            from core.self.model import get_self_model, ConfidenceLevel
            sm = get_self_model()
            cap_name = "path_{}".format(motivation.topic)
            cap = sm._domain_capabilities.get(cap_name)
            if cap and cap.confidence != ConfidenceLevel.DEGRADED:
                return {"status": "recovered", "topic": motivation.topic}
            return {"status": "still_degraded", "topic": motivation.topic,
                    "suggestion": "postpone retry or switch to alternative"}
        except Exception as e:
            return {"status": "error", "topic": motivation.topic, "error": str(e)}

    def _execute_growth_pursuit(self, motivation: Motivation) -> Dict[str, Any]:
        """追求成长方向 — 尝试外部学习"""
        try:
            from core.presence.gap_growth import get_gap_growth_engine
            gge = get_gap_growth_engine()
            from core.presence.gap_growth import SignalType
            gge.submit_signal(
                signal_type=SignalType.KNOWLEDGE_GAP,
                content=motivation.topic,
                source="intrinsic_motivation",
                priority=2,
            )
            return {"status": "signal_submitted", "topic": motivation.topic}
        except Exception as e:
            return {"status": "error", "topic": motivation.topic, "error": str(e)}

    def _execute_knowledge_gap(self, motivation: Motivation) -> Dict[str, Any]:
        """填补知识缺口 — 尝试外部搜索"""
        try:
            from backend.services.path_handlers.external_api_path import fetch_external_learning
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(fetch_external_learning(motivation.topic, ""))
                    return {"status": "async_submitted", "topic": motivation.topic}
                else:
                    return {"status": "deferred", "topic": motivation.topic,
                            "reason": "no running event loop"}
            except RuntimeError:
                return {"status": "deferred", "topic": motivation.topic}
        except Exception as e:
            return {"status": "error", "topic": motivation.topic, "error": str(e)}

    def _execute_skill_consolidation(self, motivation: Motivation) -> Dict[str, Any]:
        """技能整合 — 触发记忆整合"""
        try:
            from core.presence.sleep_consolidation import get_sleep_engine
            engine = get_sleep_engine()
            if hasattr(engine, 'consolidate'):
                engine.consolidate()
                return {"status": "consolidated", "topic": motivation.topic}
        except Exception:
            pass
        return {"status": "skipped", "topic": motivation.topic}

    def get_status(self) -> Dict[str, Any]:
        return {
            "motivation_count": len(self._motivations),
            "pending_count": len([m for m in self._motivations if not m.executed]),
            "execution_count": len(self._execution_history),
            "last_generation": self._last_generation,
            "top_motivation": (
                {"type": self._motivations[0].motivation_type.name, "topic": self._motivations[0].topic}
                if self._motivations else None
            ),
        }


_intrinsic_motivation_engine: Optional[IntrinsicMotivationEngine] = None


def get_intrinsic_motivation_engine() -> IntrinsicMotivationEngine:
    global _intrinsic_motivation_engine
    if _intrinsic_motivation_engine is None:
        _intrinsic_motivation_engine = IntrinsicMotivationEngine()
        logger.info("IntrinsicMotivationEngine initialized — 存在层有了内在动机")
    return _intrinsic_motivation_engine