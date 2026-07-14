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
        self.capability_profile: Dict[str, Any] = {}
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
                "capabilities", "capability_profile", "memory_self", "cognitive_layers",
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
            logger.warning(f"SelfModel sync spirit failed: {e}")

        try:
            self.update("health", self._extract_health(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync health failed: {e}")

        try:
            self.update("presence", self._extract_presence(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync presence failed: {e}")

        try:
            self.update("relationship", self._extract_relationship(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync relationship failed: {e}")

        try:
            self.update("evolution", self._extract_evolution(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync evolution failed: {e}")

        try:
            self.update("introspection", self._extract_introspection(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync introspection failed: {e}")

        try:
            self.update("capabilities", self._extract_capabilities(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync capabilities failed: {e}")

        try:
            self.update("capability_profile", self._extract_capability_profile())
        except Exception as e:
            logger.warning(f"SelfModel sync capability_profile failed: {e}")

        try:
            self.update("learning", self._extract_learning(cp))
        except Exception as e:
            logger.warning(f"SelfModel sync learning failed: {e}")

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
        snap = self.snapshot()
        profile = snap.get("capability_profile", {})
        return {
            "health_score": snap.get("health", {}).get("score", 0.0),
            "confidence": snap.get("health", {}).get("confidence", 0.0),
            "energy": snap.get("health", {}).get("energy", 0.0),
            "presence_state": snap.get("presence", {}).get("state", "unknown"),
            "trust_level": snap.get("relationship", {}).get("trust", 0.0),
            "relationship_phase": snap.get("relationship", {}).get("phase", "initial"),
            "evolution_progress": snap.get("evolution", {}).get("progress", 0.0),
            "capability_strength": profile.get("overall_strength", 0.0),
            "tools_registered": profile.get("tools", {}).get("registered", 0),
            "skills_mature": profile.get("skills", {}).get("mature", 0),
            "experience_success_rate": profile.get("experience", {}).get("success_rate", 0.0),
            "rules_active": profile.get("rules", {}).get("active", 0),
            "capability_gaps": len(profile.get("gaps", [])),
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
                logger.warning("操作降级跳过")
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
                logger.warning("操作降级跳过")
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
                logger.warning("操作降级跳过")
        return {}

    def _extract_introspection(self, cp) -> Dict[str, Any]:
        """从 L6 内省层提取内省状态"""
        l6 = getattr(cp, 'l6', None)
        if l6 and hasattr(l6, 'get_introspection_status'):
            try:
                return l6.get_introspection_status()
            except Exception:
                logger.warning("操作降级跳过")
        return {}

    def _extract_capabilities(self, cp) -> Dict[str, Any]:
        try:
            from core.capability_introspection import CapabilityIntrospection
            ci = CapabilityIntrospection()
            if hasattr(ci, 'get_capability_summary'):
                return ci.get_capability_summary()
        except Exception:
            logger.warning("操作降级跳过")
        return {}

    def _extract_capability_profile(self) -> Dict[str, Any]:
        """聚合各学习模块的运行时能力画像"""
        profile = {
            "tools": {},
            "skills": {},
            "experience": {},
            "rules": {},
            "gaps": [],
            "overall_strength": 0.0,
        }

        try:
            from core.tool_registry import tool_registry
            tools = tool_registry.list_tools()
            tool_stats = tool_registry.tool_executor.get_stats() if hasattr(tool_registry, 'tool_executor') else {}
            profile["tools"] = {
                "registered": len(tools),
                "categories": list(set(t.get("category", "other") for t in tools)) if tools else [],
                "top_by_usage": sorted(
                    [{"name": n, "calls": s.get("calls", 0), "success_rate": s.get("success_rate", 0)}
                     for n, s in tool_stats.items()],
                    key=lambda x: x["calls"], reverse=True
                )[:5] if tool_stats else [],
            }
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from core.skill_emergence import skill_emergence
            stats = skill_emergence.get_skill_stats()
            profile["skills"] = {
                "total": stats.get("total_skills", 0),
                "mature": stats.get("mature_skills", 0),
                "top": stats.get("top_skills", []),
            }
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/experience_pool.db")
            total_row = db.query_one("SELECT COUNT(*) FROM experiences")
            total = total_row[0] if total_row else 0
            success_row = db.query_one("SELECT COUNT(*) FROM experiences WHERE success=1")
            success = success_row[0] if success_row else 0
            intent_rows = db.query(
                "SELECT intent_type, COUNT(*) as cnt, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok "
                "FROM experiences GROUP BY intent_type ORDER BY cnt DESC LIMIT 10"
            )
            by_intent = {}
            for row in intent_rows:
                by_intent[row[0]] = {"total": row[1], "success": row[2], "rate": row[2] / max(1, row[1])}
            profile["experience"] = {
                "total": total,
                "success": success,
                "success_rate": success / max(1, total),
                "by_intent": by_intent,
            }
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/learning_rules.db")
            active_row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active = active_row[0] if active_row else 0
            total_row = db.query_one("SELECT COUNT(*) FROM learning_rules")
            total = total_row[0] if total_row else 0
            profile["rules"] = {"active": active, "total": total}
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/capability_gaps.db")
            gap_rows = db.query(
                "SELECT gap_type, COUNT(*) as cnt FROM capability_gaps WHERE resolved=0 GROUP BY gap_type ORDER BY cnt DESC LIMIT 5"
            )
            profile["gaps"] = [{"type": r[0], "count": r[1]} for r in gap_rows]
        except Exception:
            logger.warning("操作降级跳过")

        strength_parts = []
        if profile["tools"].get("registered", 0) > 0:
            strength_parts.append(min(profile["tools"]["registered"] / 10, 1.0) * 0.25)
        if profile["skills"].get("mature", 0) > 0:
            strength_parts.append(min(profile["skills"]["mature"] / 5, 1.0) * 0.25)
        if profile["experience"].get("success_rate", 0) > 0:
            strength_parts.append(profile["experience"]["success_rate"] * 0.25)
        if profile["rules"].get("active", 0) > 0:
            strength_parts.append(min(profile["rules"]["active"] / 20, 1.0) * 0.25)
        profile["overall_strength"] = sum(strength_parts) if strength_parts else 0.0

        return profile

    def _extract_learning(self, cp) -> Dict[str, Any]:
        """从学习层提取学习状态"""
        l2 = getattr(cp, 'l2', None)
        if l2:
            info = {}
            if hasattr(l2, 'get_learning_stats'):
                try:
                    info = l2.get_learning_stats()
                except Exception:
                    logger.warning("操作降级跳过")
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
        profile_gaps = snap.get("capability_profile", {}).get("gaps", [])
        all_gaps = capability_gaps + profile_gaps
        if all_gaps:
            gap_types = set()
            for g in all_gaps:
                gt = g.get("gap_type", g.get("type", ""))
                if gt:
                    gap_types.add(gt)
            actions.append({
                "action": "capability_gap_learning",
                "reason": f"检测到{len(all_gaps)}个能力缺失: {list(gap_types)[:3]}",
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

        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            curiosity = get_curiosity_engine()
            gaps = curiosity.perceive_gaps()
            if gaps:
                high_urgency = [g for g in gaps if g.urgency.value in ("high", "critical")]
                if high_urgency:
                    actions.append({
                        "action": "curiosity_driven_learning",
                        "reason": f"好奇心驱动: {len(high_urgency)}个高紧急度知识缺口",
                        "handler": self._action_curiosity_driven_learning,
                    })
        except Exception:
            pass

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
            logger.warning(f"SelfModel self_repair failed: {e}")

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
            logger.warning(f"SelfModel external_learning failed: {e}")

    def _action_capability_gap_learning(self):
        try:
            from core.learning.capability_gap_learner import capability_gap_learner
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/capability_gaps.db")
            rows = db.query("SELECT query, gap_type, failed_paths FROM capability_gaps WHERE resolved=0 ORDER BY attempts DESC LIMIT 3")
            for row in rows:
                gap = {"query": row[0], "gap_type": row[1], "failed_paths": row[2]}
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(capability_gap_learner.try_resolve_gap(gap))
                        try:
                            from core.capability_creation_loop import capability_creation_loop
                            asyncio.ensure_future(
                                capability_creation_loop.handle(row[0], context={"intent_type": row[1], "trigger": "self_model_gap"})
                            )
                        except Exception:
                            pass
                    else:
                        loop.run_until_complete(capability_gap_learner.try_resolve_gap(gap))
                        try:
                            from core.capability_creation_loop import capability_creation_loop
                            loop.run_until_complete(
                                capability_creation_loop.handle(row[0], context={"intent_type": row[1], "trigger": "self_model_gap"})
                            )
                        except Exception:
                            pass
                except RuntimeError:
                    asyncio.run(capability_gap_learner.try_resolve_gap(gap))
        except Exception as e:
            logger.warning(f"SelfModel capability_gap_learning failed: {e}")

    def _action_proactive_engage(self):
        try:
            from core.presence.proactivity import get_proactivity_engine
            engine = get_proactivity_engine()
            if hasattr(engine, 'suggest_engagement'):
                engine.suggest_engagement()
        except Exception as e:
            logger.warning(f"SelfModel proactive_engage failed: {e}")

    def _action_trigger_evolution(self):
        try:
            from core.evolution.meta_learning import MetaLearner
            ml = MetaLearner()
            if hasattr(ml, 'trigger_sandbox_evolution'):
                ml.trigger_sandbox_evolution()
        except Exception as e:
            logger.warning(f"SelfModel trigger_evolution failed: {e}")

    def _action_curiosity_driven_learning(self):
        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            engine = get_curiosity_engine()
            actions = engine.generate_learning_actions()
            for action in actions[:3]:
                if action.action_type == "create_capability":
                    try:
                        from core.capability_creation_loop import capability_creation_loop
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(
                                capability_creation_loop.handle(action.content, context={"intent_type": "curiosity", "trigger": "curiosity_driven"})
                            )
                        else:
                            loop.run_until_complete(
                                capability_creation_loop.handle(action.content, context={"intent_type": "curiosity", "trigger": "curiosity_driven"})
                            )
                    except Exception as e:
                        logger.debug(f"好奇心能力创造跳过: {e}")
                elif action.action_type == "search_external":
                    try:
                        from core.external_learner import external_learner
                        if hasattr(external_learner, 'learn_from_external'):
                            external_learner.learn_from_external(
                                user_input=action.content,
                                context={"trigger": "curiosity"},
                                trigger_reason="curiosity_driven"
                            )
                    except Exception as e:
                        logger.debug(f"好奇心外部学习跳过: {e}")
                elif action.action_type == "reflect_internal":
                    try:
                        from core.self_modification.loop import self_modification_loop
                        if self_modification_loop.can_run():
                            mod_result = self_modification_loop.run_from_lessons()
                            if mod_result.triggered:
                                logger.info(
                                    f"🔍 好奇心反思→L5自触发: "
                                    f"缺陷={mod_result.defects_found}, "
                                    f"补丁={mod_result.patches_generated}, "
                                    f"安全={mod_result.patches_safe}, "
                                    f"提案={mod_result.proposals_created}"
                                )
                            else:
                                logger.info(f"🔍 好奇心反思: 无缺陷待处理")
                        else:
                            logger.debug("好奇心反思: L5自触发冷却中，跳过")
                    except Exception as e:
                        logger.debug(f"好奇心反思跳过: {e}")
        except Exception as e:
            logger.warning(f"SelfModel curiosity_driven_learning failed: {e}")


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