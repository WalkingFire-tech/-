"""
SelfModel — 系统的自我意识入口

所有自我认知汇聚的地方。系统第一次有了"我是谁"的统一认知。

设计原则：
- 不改任何现有模块的逻辑，只加"连接"代码
- 每个数据源都是可选的，缺失时优雅降级
- 线程安全，可在 async 和 sync 上下文中使用
- 轻量：snapshot() 是只读快照，update() 是增量写入
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SelfModel:
    """
    系统的自我意识 — 统一所有自我认知的入口

    聚合 12 大数据源，形成一致的自我表征：
    1. 身份层 — SpiritCore 原则合规率
    2. 感知层 — SelfPerceptionModule 健康度/置信度/能量
    3. 存在层 — ExistenceLayer 运行状态
    4. 评估层 — ContinuousSelfAssessment 评估得分与趋势
    5. 关系层 — RelationshipModel 信任/亲密/理解
    6. 进化层 — AdaptiveEvolutionGoal 进化目标与进度
    7. 学习层 — 认知节奏/学习信号
    8. 内省层 — IntrospectionEngine 系统状态
    9. 反思层 — SelfReflection 交互反思
    10. 能力层 — CapabilityIntrospection 能力注册
    11. 记忆层 — StereoMemory 自我维度
    12. 认知层 — CognitivePlanner L1-L6 循环数据
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._init_time = datetime.now()
        self._update_count = 0

        self.values: Dict[str, Any] = {}
        self.health: Dict[str, Any] = {}
        self.presence: Dict[str, Any] = {}
        self.assessment: Dict[str, Any] = {}
        self.relationship: Dict[str, Any] = {}
        self.evolution: Dict[str, Any] = {}
        self.learning: Dict[str, Any] = {}
        self.introspection: Dict[str, Any] = {}
        self.reflection: Dict[str, Any] = {}
        self.capabilities: Dict[str, Any] = {}
        self.memory_self: Dict[str, Any] = {}
        self.cognitive_layers: Dict[str, Any] = {}

        self.current_thinking: List[Dict[str, Any]] = []
        self.recent_learning: List[Dict[str, Any]] = []
        self.growth_edges: List[Dict[str, Any]] = []

    def update(self, category: str, data: Dict[str, Any]) -> None:
        """增量更新某个认知维度"""
        if not isinstance(data, dict):
            return
        with self._lock:
            target = getattr(self, category, None)
            if target is not None and isinstance(target, dict):
                target.update(data)
            self._update_count += 1

    def append(self, category: str, item: Any, max_len: int = 50) -> None:
        """向列表类维度追加条目"""
        with self._lock:
            target = getattr(self, category, None)
            if target is not None and isinstance(target, list):
                target.append(item)
                if len(target) > max_len:
                    del target[:len(target) - max_len]
            self._update_count += 1

    def snapshot(self) -> Dict[str, Any]:
        """获取当前自我模型的只读快照"""
        with self._lock:
            result = {}
            for key in (
                "values", "health", "presence", "assessment", "relationship",
                "evolution", "learning", "introspection", "reflection",
                "capabilities", "memory_self", "cognitive_layers",
            ):
                val = getattr(self, key, None)
                if val is not None:
                    result[key] = dict(val) if isinstance(val, dict) else val

            result["current_thinking"] = list(self.current_thinking)
            result["recent_learning"] = list(self.recent_learning)
            result["growth_edges"] = list(self.growth_edges)
            result["_meta"] = {
                "init_time": self._init_time.isoformat(),
                "update_count": self._update_count,
                "snapshot_time": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self._init_time).total_seconds(),
            }
            return result

    def sync_from_cognitive_planner(self, cp) -> None:
        """从 CognitivePlanner 同步所有子组件状态"""
        if cp is None:
            return

        try:
            self.update("values", self._extract_spirit(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync spirit failed: {e}")

        try:
            self.update("health", self._extract_health(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync health failed: {e}")

        try:
            self.update("presence", self._extract_presence(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync presence failed: {e}")

        try:
            self.update("relationship", self._extract_relationship(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync relationship failed: {e}")

        try:
            self.update("evolution", self._extract_evolution(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync evolution failed: {e}")

        try:
            self.update("introspection", self._extract_introspection(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync introspection failed: {e}")

        try:
            self.update("capabilities", self._extract_capabilities(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync capabilities failed: {e}")

        try:
            self.update("learning", self._extract_learning(cp))
        except Exception as e:
            logger.debug(f"SelfModel sync learning failed: {e}")

    def record_cognitive_cycle(
        self,
        perception: Optional[Dict] = None,
        learning: Optional[Dict] = None,
        integration: Optional[Dict] = None,
        validation: Optional[Dict] = None,
        introspection: Optional[Dict] = None,
    ) -> None:
        """记录一次认知循环的结果到 SelfModel"""
        ts = datetime.now().isoformat()

        if perception:
            self.update("cognitive_layers", {"L1_perception": perception, "last_perception_time": ts})
            self.append("current_thinking", {
                "phase": perception.get("intent", "unknown"),
                "confidence": perception.get("confidence", 0.0),
                "emotion": perception.get("emotion", "neutral"),
                "urgency": perception.get("urgency", 0.0),
                "timestamp": ts,
            }, max_len=20)

        if learning:
            self.update("cognitive_layers", {"L2_learning": learning})
            if learning.get("knowledge_gained"):
                self.append("recent_learning", {
                    "summary": str(learning.get("knowledge_gained", ""))[:200],
                    "source": "L2_learning",
                    "confidence": learning.get("confidence", 0.5),
                    "timestamp": ts,
                }, max_len=30)

        if integration:
            self.update("cognitive_layers", {"L3_integration": integration})

        if validation:
            self.update("cognitive_layers", {"L4_validation": validation})

        if introspection:
            self.update("cognitive_layers", {"L6_introspection": introspection})

    def get_status_summary(self) -> Dict[str, Any]:
        """获取简短状态摘要，用于 SSE 推送和 API 响应"""
        snap = self.snapshot()
        return {
            "health_score": snap.get("health", {}).get("score", 0.0),
            "confidence": snap.get("health", {}).get("confidence", 0.0),
            "energy": snap.get("health", {}).get("energy", 0.0),
            "presence_state": snap.get("presence", {}).get("state", "unknown"),
            "trust_level": snap.get("relationship", {}).get("trust", 0.0),
            "relationship_phase": snap.get("relationship", {}).get("phase", "initial"),
            "evolution_progress": snap.get("evolution", {}).get("progress", 0.0),
            "learning_count": len(snap.get("recent_learning", [])),
            "thinking_count": len(snap.get("current_thinking", [])),
            "growth_edges_count": len(snap.get("growth_edges", [])),
            "update_count": snap.get("_meta", {}).get("update_count", 0),
            "uptime_seconds": snap.get("_meta", {}).get("uptime_seconds", 0.0),
        }

    def _extract_spirit(self, cp) -> Dict[str, Any]:
        """从 SpiritCore 提取原则状态"""
        try:
            from core.spirit_core import spirit_core
            status = spirit_core.get_spirit_status()
            return {
                "principles_count": len(status.get("core_principles", [])),
                "abilities_count": len(status.get("abilities", {})),
                "violations_count": len(status.get("violations", [])),
                "lessons_count": len(status.get("lessons_learned", [])),
            }
        except Exception:
            return {}

    def _extract_health(self, cp) -> Dict[str, Any]:
        """从 SelfPerceptionModule 提取健康状态"""
        sp = getattr(cp, 'self_perception', None)
        if sp and hasattr(sp, 'perceive'):
            try:
                result = sp.perceive()
                if hasattr(result, 'health_score'):
                    return {
                        "score": result.health_score,
                        "confidence": result.confidence_level,
                        "energy": result.energy_level,
                        "knowledge_growth": result.knowledge_growth,
                        "relationship_health": result.relationship_health,
                    }
            except Exception:
                pass
        return {}

    def _extract_presence(self, cp) -> Dict[str, Any]:
        """从 ExistenceLayer 提取存在状态"""
        ex = getattr(cp, 'existence', None)
        if ex:
            state = "unknown"
            if hasattr(ex, '_state'):
                state = ex._state.value if hasattr(ex._state, 'value') else str(ex._state)
            metrics = {}
            if hasattr(ex, '_metrics') and ex._metrics:
                m = ex._metrics
                metrics = {
                    "uptime_seconds": m.uptime_seconds,
                    "total_cycles": m.total_cycles,
                    "signals_processed": m.signals_processed,
                    "memories_consolidated": m.memories_consolidated,
                }
            return {"state": state, **metrics}
        return {}

    def _extract_relationship(self, cp) -> Dict[str, Any]:
        """从 RelationshipModel 提取关系状态"""
        rm = getattr(cp, 'relationship_model', None)
        if rm and hasattr(rm, 'get_metrics'):
            try:
                metrics = rm.get_metrics()
                phase = "initial"
                if hasattr(rm, 'get_relationship_phase'):
                    phase = rm.get_relationship_phase()
                return {
                    "trust": metrics.get("trust", 0.0),
                    "intimacy": metrics.get("intimacy", 0.0),
                    "phase": phase,
                }
            except Exception:
                pass
        return {}

    def _extract_evolution(self, cp) -> Dict[str, Any]:
        """从 AdaptiveEvolutionGoal 提取进化状态"""
        ge = getattr(cp, 'goal_engine', None)
        if ge and hasattr(ge, 'get_top_priorities'):
            try:
                priorities = ge.get_top_priorities(3)
                progress = 0.0
                if priorities:
                    progress = sum(
                        getattr(p, 'progress', 0.0) for p in priorities
                    ) / len(priorities)
                return {
                    "progress": progress,
                    "top_priorities_count": len(priorities),
                }
            except Exception:
                pass
        return {}

    def _extract_introspection(self, cp) -> Dict[str, Any]:
        """从 L6 内省层提取内省状态"""
        l6 = getattr(cp, 'l6', None)
        if l6 and hasattr(l6, 'get_introspection_status'):
            try:
                return l6.get_introspection_status()
            except Exception:
                pass
        return {}

    def _extract_capabilities(self, cp) -> Dict[str, Any]:
        """从 CapabilityIntrospection 提取能力状态"""
        try:
            from core.capability_introspection import CapabilityIntrospection
            ci = CapabilityIntrospection()
            if hasattr(ci, 'get_capability_summary'):
                return ci.get_capability_summary()
        except Exception:
            pass
        return {}

    def _extract_learning(self, cp) -> Dict[str, Any]:
        """从学习层提取学习状态"""
        l2 = getattr(cp, 'l2', None)
        if l2:
            info = {}
            if hasattr(l2, 'get_learning_stats'):
                try:
                    info = l2.get_learning_stats()
                except Exception:
                    pass
            return info
        return {}

    def evaluate_and_act(self) -> List[Dict[str, Any]]:
        """
        反馈回路核心：检测 SelfModel 状态变化，触发系统行为

        规则：
        1. 健康度持续低 → 触发自修复
        2. 置信度持续低 → 触发外部学习
        3. 关系信任下降 → 增强主动交互
        4. 进化停滞 → 触发进化岛沙盒运行
        """
        actions = []
        snap = self.snapshot()

        health_score = snap.get("health", {}).get("score", 0.0)
        confidence = snap.get("health", {}).get("confidence", 0.0)
        trust = snap.get("relationship", {}).get("trust", 0.0)
        evolution_progress = snap.get("evolution", {}).get("progress", 0.0)

        if health_score > 0 and health_score < 0.3:
            actions.append({
                "action": "self_repair",
                "reason": f"健康度过低({health_score:.1%})",
                "handler": self._action_self_repair,
            })

        if confidence > 0 and confidence < 0.3:
            actions.append({
                "action": "external_learning",
                "reason": f"置信度过低({confidence:.1%})",
                "handler": self._action_external_learning,
            })

        capability_gaps = snap.get("capabilities", {}).get("gaps", [])
        if capability_gaps and len(capability_gaps) > 0:
            actions.append({
                "action": "capability_gap_learning",
                "reason": f"检测到{len(capability_gaps)}个能力缺失: {[g.get('gap_type','') for g in capability_gaps[:3]]}",
                "handler": self._action_capability_gap_learning,
            })

        if trust > 0 and trust < 0.2:
            actions.append({
                "action": "proactive_engage",
                "reason": f"关系信任度低({trust:.1%})",
                "handler": self._action_proactive_engage,
            })

        if 0 < evolution_progress < 0.1 and snap.get("_meta", {}).get("update_count", 0) > 10:
            actions.append({
                "action": "trigger_evolution",
                "reason": f"进化停滞(progress={evolution_progress:.1%})",
                "handler": self._action_trigger_evolution,
            })

        for a in actions:
            try:
                a["handler"]()
                a["executed"] = True
            except Exception as e:
                a["executed"] = False
                a["error"] = str(e)
            del a["handler"]

        if actions:
            logger.info(f"🪞 SelfModel 反馈回路触发 {len(actions)} 个动作: {[a['action'] for a in actions]}")

        return actions

    def _action_self_repair(self):
        try:
            from core.introspection_engine import IntrospectionEngine
            engine = IntrospectionEngine()
            engine.heal()
        except Exception as e:
            logger.debug(f"SelfModel self_repair failed: {e}")

    def _action_external_learning(self):
        try:
            from core.external_learner import external_learner
            if hasattr(external_learner, 'learn_from_external'):
                external_learner.learn_from_external(
                    user_input="系统自动触发外部学习",
                    context={},
                    trigger_reason="confidence_low"
                )
            elif hasattr(external_learner, 'learn_and_integrate'):
                external_learner.learn_and_integrate(
                    user_input="系统自动触发外部学习",
                    context={}
                )
        except Exception as e:
            logger.debug(f"SelfModel external_learning failed: {e}")

    def _action_capability_gap_learning(self):
        try:
            from core.learning.capability_gap_learner import capability_gap_learner
            db = DatabaseManager.get("data/capability_gaps.db")
            rows = db.query("SELECT query, gap_type, failed_paths FROM capability_gaps WHERE resolved=0 ORDER BY attempts DESC LIMIT 3")
            for row in rows:
                gap = {"query": row[0], "gap_type": row[1], "failed_paths": row[2]}
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(capability_gap_learner.try_resolve_gap(gap))
                    else:
                        loop.run_until_complete(capability_gap_learner.try_resolve_gap(gap))
                except RuntimeError:
                    asyncio.run(capability_gap_learner.try_resolve_gap(gap))
        except Exception as e:
            logger.debug(f"SelfModel capability_gap_learning failed: {e}")

    def _action_proactive_engage(self):
        try:
            from core.presence.proactivity import get_proactivity_engine
            engine = get_proactivity_engine()
            if hasattr(engine, 'suggest_engagement'):
                engine.suggest_engagement()
        except Exception as e:
            logger.debug(f"SelfModel proactive_engage failed: {e}")

    def _action_trigger_evolution(self):
        try:
            from core.evolution.meta_learning import MetaLearner
            ml = MetaLearner()
            if hasattr(ml, 'trigger_sandbox_evolution'):
                ml.trigger_sandbox_evolution()
        except Exception as e:
            logger.debug(f"SelfModel trigger_evolution failed: {e}")


_self_model_instance: Optional[SelfModel] = None
_self_model_lock = threading.Lock()


def get_self_model() -> SelfModel:
    """获取 SelfModel 全局单例"""
    global _self_model_instance
    if _self_model_instance is None:
        with _self_model_lock:
            if _self_model_instance is None:
                _self_model_instance = SelfModel()
                logger.info("🪞 SelfModel 已创建 — 系统第一次有了'我是谁'的统一认知")
    return _self_model_instance