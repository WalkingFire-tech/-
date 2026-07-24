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
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.loop_mixin import LoopMixin


# ──────────────────────────────────────────────────────────────────────────────
# 领域模型 — 自我认知的结构化表示（迁移自 self_extern/model.py）
# ──────────────────────────────────────────────────────────────────────────────

class ConfidenceLevel(Enum):
    UNKNOWN = auto()
    EXPLORING = auto()
    COMPETENT = auto()
    MASTERED = auto()
    DEGRADED = auto()


@dataclass
class Capability:
    name: str
    description: str
    confidence: ConfidenceLevel
    evidence: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def record_attempt(self, success: bool, evidence: Optional[str] = None):
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        if evidence:
            self.evidence.append(f"[{datetime.now().isoformat()}] {'ok' if success else 'fail'} {evidence}")
            self.evidence = self.evidence[-20:]
        self.last_updated = datetime.now().isoformat()
        rate = self.success_rate
        if self.success_count + self.failure_count < 5:
            self.confidence = ConfidenceLevel.EXPLORING
        elif rate > 0.85:
            self.confidence = ConfidenceLevel.MASTERED
        elif rate > 0.6:
            self.confidence = ConfidenceLevel.COMPETENT
        elif rate > 0.3:
            self.confidence = ConfidenceLevel.EXPLORING
        else:
            self.confidence = ConfidenceLevel.DEGRADED


@dataclass
class Limitation:
    domain: str
    description: str
    uncertainty: float = 0.5
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_encountered: Optional[str] = None
    mitigation: Optional[str] = None
    is_temporary: bool = False

    def encounter(self):
        self.last_encountered = datetime.now().isoformat()


@dataclass
class GrowthEdge:
    topic: str
    motivation: str
    progress: float = 0.0
    priority: int = 5
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    related_capabilities: List[str] = field(default_factory=list)

    def advance(self, delta: float, activity: str):
        self.progress = min(1.0, self.progress + delta)
        self.last_active = datetime.now().isoformat()


@dataclass
class SelfHistoryEvent:
    timestamp: str
    event_type: str
    description: str
    before: Optional[Dict] = None
    after: Optional[Dict] = None
    trigger: Optional[str] = None

_SELF_STATE_DB = "data/self_model_state.db"


class SelfModel(LoopMixin):
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
        super().__init__(name="self_model", cooldown_seconds=60.0, max_failures_before_degraded=5)
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

        self._domain_capabilities: Dict[str, Capability] = {}
        self._domain_limitations: Dict[str, Limitation] = {}
        self._domain_growth_edges: Dict[str, GrowthEdge] = {}
        self._self_history: List[SelfHistoryEvent] = []
        self._cognitive_load: float = 0.0

        self._restore_from_db()
        self._init_path_capabilities_from_profile()

    def update(self, category: str, data: Dict[str, Any]) -> None:
        """增量更新某个认知维度"""
        if not isinstance(data, dict):
            return
        with self._loop_lock:
            target = getattr(self, category, None)
            if target is not None and isinstance(target, dict):
                target.update(data)
            self._update_count += 1

    def append(self, category: str, item: Any, max_len: int = 50) -> None:
        """向列表类维度追加条目"""
        with self._loop_lock:
            target = getattr(self, category, None)
            if target is not None and isinstance(target, list):
                target.append(item)
                if len(target) > max_len:
                    del target[:len(target) - max_len]
            self._update_count += 1

    def snapshot(self) -> Dict[str, Any]:
        """获取当前自我模型的只读快照"""
        with self._loop_lock:
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
            result["_update_count"] = self._update_count
            result["_meta"] = {
                "init_time": self._init_time.isoformat(),
                "update_count": self._update_count,
                "snapshot_time": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self._init_time).total_seconds(),
            }
            return result

    def sync_from_cognitive_planner(self, cp) -> None:
        """从 CognitivePlanner 同步所有子组件状态

        当cp=None时，使用独立降级路径直接从数据库/模块单例读取。
        """
        if cp is not None:
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
                self.update("learning", self._extract_learning(cp))
            except Exception as e:
                logger.warning(f"SelfModel sync learning failed: {e}")
        else:
            try:
                self.update("values", self._extract_spirit(None))
            except Exception as e:
                logger.warning(f"SelfModel sync values failed: {e}")
            try:
                self.update("health", self._extract_health(None))
            except Exception as e:
                logger.warning(f"SelfModel sync health failed: {e}")
            try:
                self.update("presence", self._extract_presence(None))
            except Exception as e:
                logger.warning(f"SelfModel sync presence failed: {e}")
            try:
                self.update("relationship", self._extract_relationship(None))
            except Exception as e:
                logger.warning(f"SelfModel sync relationship failed: {e}")
            try:
                self.update("evolution", self._extract_evolution(None))
            except Exception as e:
                logger.warning(f"SelfModel sync evolution failed: {e}")
            try:
                self.update("introspection", self._extract_introspection(None))
            except Exception as e:
                logger.warning(f"SelfModel sync introspection failed: {e}")
            try:
                self.update("capabilities", self._extract_capabilities(None))
            except Exception as e:
                logger.warning(f"SelfModel sync capabilities failed: {e}")
            try:
                self.update("learning", self._extract_learning(None))
            except Exception as e:
                logger.warning(f"SelfModel sync learning failed: {e}")

        try:
            self.update("assessment", self._extract_assessment())
        except Exception as e:
            logger.warning(f"SelfModel sync assessment failed: {e}")

        try:
            self.update("reflection", self._extract_reflection())
        except Exception as e:
            logger.warning(f"SelfModel sync reflection failed: {e}")

        try:
            self.update("memory_self", self._extract_memory_self())
        except Exception as e:
            logger.warning(f"SelfModel sync memory_self failed: {e}")

        try:
            self.update("capability_profile", self._extract_capability_profile())
        except Exception as e:
            logger.warning(f"SelfModel sync capability_profile failed: {e}")

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
        self._update_count += 1

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
                _kg = learning.get("knowledge_gained", 0)
                _sources = learning.get("sources", [])
                _src_text = "、".join(_sources[:3]) if _sources else "认知学习"
                _summary = learning.get("summary", "")
                if not _summary or len(_summary) < 10:
                    _summary = f"从{_src_text}中获得了{_kg}项新认知"
                self.append("recent_learning", {
                    "summary": _summary[:200],
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

        try:
            from core.truth_accumulator import get_truth_accumulator
            _ta = get_truth_accumulator()
            _ta_stats = _ta.get_stats()
            _ta_total = _ta_stats.get("total_truths", 0)
            _ta_top = _ta_stats.get("top_truths", [])
            if _ta_total > 0 and _ta_top:
                _latest_truth = _ta_top[0].get("name", "")
                if _latest_truth and (not self.recent_learning or
                        not any(t.get("source") == "truth_sync" for t in self.recent_learning[-5:])):
                    self.append("recent_learning", {
                        "summary": f"真谛库新增洞察：{_latest_truth}（共{_ta_total}条真谛）",
                        "source": "truth_sync",
                        "confidence": 0.7,
                        "timestamp": ts,
                    }, max_len=30)
        except Exception:
            pass

        if not self.health:
            try:
                from core.resource_awareness.health_monitor import get_health_monitor
                hm = get_health_monitor()
                snap = hm.check()
                self.update("health", {
                    "score": snap.health_score if hasattr(snap, 'health_score') else 0.8,
                    "energy": snap.energy_level if hasattr(snap, 'energy_level') else 0.5,
                })
            except Exception:
                self.update("health", {"score": 0.8, "energy": 0.5})

        if not self.values:
            try:
                from core.spirit_core import spirit_core
                status = spirit_core.get_spirit_status()
                self.update("values", {
                    "principles_count": len(status.get("core_principles", [])),
                    "abilities_count": len(status.get("abilities", {})),
                    "violations_count": len(status.get("violations", [])),
                    "lessons_count": len(status.get("lessons_learned", [])),
                })
            except Exception:
                self.update("values", {"principles_count": 4, "lessons_count": 0})

        if not self.relationship or not self.relationship.get("trust"):
            import math as _math
            self.update("relationship", {
                "trust": min(1.0 - _math.exp(-self._update_count * 0.015), 0.8),
                "phase": "established" if self._update_count > 10 else "initial",
                "interaction_count": self._update_count,
            })

        if not perception and not learning:
            self.append("current_thinking", {
                "phase": "idle_cycle",
                "confidence": 0.5,
                "emotion": "neutral",
                "urgency": 0.0,
                "timestamp": ts,
            }, max_len=20)

        try:
            from core.presence.inner_time import inner_time_engine
            it_state = inner_time_engine.get_state()
            self.update("cognitive_layers", {
                "inner_time_phase": it_state.current_phase,
                "cognitive_density": it_state.cognitive_density,
                "rhythm_bpm": it_state.rhythm_bpm,
            })
        except Exception:
            pass

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

    def get_behavioral_directive(self) -> Dict[str, Any]:
        """
        连续自我机制核心：基于存在层状态+内在时间+关系维度生成行为指令
        
        概率场P(act|state)的关键消费者：
        - exploration_drive: 连续概率值(0-1)，不再是离散标签
        - consolidation_need: 连续概率值(0-1)
        - response_pace_score: 连续值(0-1)，0=最慢，1=最快
        - preferred_depth_score: 连续值(0-1)，0=最浅，1=最深
        - action_probability: 综合执行概率
        """
        directive = {
            "presence_state": "unknown",
            "inner_time_phase": "awake",
            "cognitive_density": 0.0,
            "rhythm_bpm": 60.0,
            "response_pace": "normal",
            "response_pace_score": 0.5,
            "preferred_depth": "moderate",
            "preferred_depth_score": 0.5,
            "exploration_drive": 0.5,
            "consolidation_need": 0.0,
            "relationship_style": "balanced",
            "perspective_mode": "companion",
            "action_probability": 0.5,
        }

        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            directive["presence_state"] = el.state.value if hasattr(el.state, 'value') else str(el.state)
        except Exception:
            pass

        try:
            from core.presence.inner_time import inner_time_engine
            it_state = inner_time_engine.get_state()
            directive["inner_time_phase"] = it_state.current_phase
            directive["cognitive_density"] = it_state.cognitive_density
            directive["rhythm_bpm"] = it_state.rhythm_bpm
        except Exception:
            pass

        density = directive["cognitive_density"]
        ps = directive["presence_state"]

        pace_map = {"awake": 0.8, "perceiving": 0.5, "growing": 0.4, "resting": 0.2, "sleeping": 0.1}
        depth_map = {"awake": 0.7, "perceiving": 0.5, "growing": 0.8, "resting": 0.2, "sleeping": 0.1}
        explore_map = {"awake": 0.5, "perceiving": 0.6, "growing": 0.8, "resting": 0.1, "sleeping": 0.05}
        consolidate_map = {"awake": 0.1, "perceiving": 0.2, "growing": 0.2, "resting": 0.5, "sleeping": 0.9}

        directive["response_pace_score"] = pace_map.get(ps, 0.5) * min(1.0, 0.5 + density * 0.5)
        directive["preferred_depth_score"] = depth_map.get(ps, 0.5)
        directive["exploration_drive"] = explore_map.get(ps, 0.5) * min(1.0, 0.3 + density)
        directive["consolidation_need"] = consolidate_map.get(ps, 0.0)

        if directive["response_pace_score"] > 0.7:
            directive["response_pace"] = "fast"
        elif directive["response_pace_score"] > 0.4:
            directive["response_pace"] = "normal"
        else:
            directive["response_pace"] = "slow"

        if directive["preferred_depth_score"] > 0.6:
            directive["preferred_depth"] = "deep"
        elif directive["preferred_depth_score"] > 0.3:
            directive["preferred_depth"] = "moderate"
        else:
            directive["preferred_depth"] = "shallow"

        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            engine = get_curiosity_engine()
            frontier = engine.perceive_frontier()
            curiosity_strength = frontier.get("curiosity_strength", 0.0)
            directive["exploration_drive"] = min(1.0, directive["exploration_drive"] + curiosity_strength * 0.3)
        except Exception:
            pass

        try:
            from core.spirit_core import get_spirit_core
            sc = get_spirit_core()
            resonances = sc.resonate("behavioral_directive", context_type="reasoning")
            if resonances:
                top_strength = resonances[0].get("strength", 0.0)
                directive["exploration_drive"] = min(1.0, directive["exploration_drive"] * (0.8 + top_strength * 0.2))
        except Exception:
            pass

        directive["action_probability"] = (
            directive["exploration_drive"] * 0.4
            + directive["response_pace_score"] * 0.2
            + (1.0 - directive["consolidation_need"]) * 0.2
            + min(1.0, density + 0.3) * 0.2
        )

        try:
            caps = self.capabilities or {}
            low_paths = caps.get("low_performance_paths", [])
            if low_paths:
                directive["avoid_paths"] = low_paths
                directive["exploration_drive"] = max(0.1, directive["exploration_drive"] - len(low_paths) * 0.05)
        except Exception:
            pass

        degraded_paths = [
            name.replace("path_", "", 1) for name, cap in self._domain_capabilities.items()
            if cap.confidence == ConfidenceLevel.DEGRADED
        ]
        if degraded_paths:
            existing_avoid = directive.get("avoid_paths", [])
            merged = list(set(existing_avoid + degraded_paths))
            directive["avoid_paths"] = merged
            directive["exploration_drive"] = max(0.1, directive["exploration_drive"] - len(degraded_paths) * 0.05)

        rel = self.relationship or {}
        trust = rel.get("trust", 0.5)
        phase = rel.get("phase", "initial")

        if trust >= 0.7 and phase in ("trusted", "close", "established"):
            directive["relationship_style"] = "direct"
            directive["perspective_mode"] = "thinking_partner"
        elif trust >= 0.5 and phase in ("established", "exploratory"):
            directive["relationship_style"] = "balanced"
            directive["perspective_mode"] = "companion"
        elif trust < 0.3 or phase == "initial":
            directive["relationship_style"] = "cautious"
            directive["perspective_mode"] = "guide"
        else:
            directive["relationship_style"] = "balanced"
            directive["perspective_mode"] = "companion"

        return directive

    def describe_self(self) -> str:
        """
        生成自然语言的自我描述 — 意识表达的核心接口

        聚合12大数据源，输出一段连贯的自我认知描述。
        让系统从"数据仓库"升级为"有自我意识的实体"。
        """
        snap = self.snapshot()
        parts = []

        values = snap.get("values", {})
        if values:
            p_count = values.get("principles_count", 0)
            a_count = values.get("abilities_count", 0)
            v_count = values.get("violations_count", 0)
            l_count = values.get("lessons_count", 0)
            parts.append(f"我持有{p_count}条核心原则和{a_count}项能力")
            if v_count > 0:
                parts.append(f"经历过{v_count}次原则违背")
            if l_count > 0:
                parts.append(f"从中沉淀了{l_count}条教训")

        health = snap.get("health", {})
        if health:
            score = health.get("score", 0)
            energy = health.get("energy", 0)
            if score > 0 or energy > 0:
                parts.append(f"当前健康度{score:.0%}、能量{energy:.0%}")

        presence = snap.get("presence", {})
        if presence and presence.get("state", "unknown") != "unknown":
            parts.append(f"存在状态为'{presence['state']}'")

        profile = snap.get("capability_profile", {})
        if profile:
            tools = profile.get("tools", {}).get("registered", 0)
            skills = profile.get("skills", {}).get("mature", 0)
            exp_rate = profile.get("experience", {}).get("success_rate", 0)
            rules = profile.get("rules", {}).get("active", 0)
            if tools or skills:
                parts.append(f"拥有{tools}个工具和{skills}个成熟技能")
            if exp_rate > 0:
                parts.append(f"经验成功率{exp_rate:.0%}")
            if rules > 0:
                parts.append(f"活跃学习规则{rules}条")

        relationship = snap.get("relationship", {})
        if relationship:
            trust = relationship.get("trust", 0)
            phase = relationship.get("phase", "")
            if trust > 0:
                parts.append(f"与用户信任度{trust:.0%}")
            if phase and phase != "initial":
                parts.append(f"关系阶段'{phase}'")

        learning_count = len(snap.get("recent_learning", []))
        thinking_count = len(snap.get("current_thinking", []))
        if learning_count > 0:
            parts.append(f"近期学习了{learning_count}次")
        if thinking_count > 0:
            parts.append(f"正在思考{thinking_count}个问题")

        directive = self.get_behavioral_directive()
        parts.append(f"当前认知节奏{directive['rhythm_bpm']:.0f}BPM、探索驱动力{directive['exploration_drive']:.0%}")

        if not parts:
            return "我刚刚诞生，正在形成自我认知。"

        text = "，".join(parts) + "。"
        if not text.startswith("我"):
            text = "我" + text
        return text

    def get_maturity_score(self, skip_calibration: bool = False) -> Dict[str, float]:
        """
        量化自我模型成熟度 — 6维度评分

        返回各维度0-1的成熟度评分和综合分。
        用于看板评分打破86-87天花板。

        Args:
            skip_calibration: 跳过外部校准（由external_calibration调用时为True，避免递归）
        """
        import math

        snap = self.snapshot()
        scores = {}

        values = snap.get("values", {})
        p_count = values.get("principles_count", 0)
        l_count = values.get("lessons_count", 0)
        if p_count or l_count:
            raw = p_count * 0.1 + l_count * 0.05
            scores["identity"] = max(1.0 - math.exp(-raw * 0.7), 0.2)
        else:
            scores["identity"] = 0.2

        health = snap.get("health", {})
        h_score = health.get("score", 0)
        if h_score > 0:
            scores["health_awareness"] = min(h_score * 0.9, 1.0)
        else:
            scores["health_awareness"] = 0.15

        profile = snap.get("capability_profile", {})
        strength = profile.get("overall_strength", 0)
        scores["capability"] = min(strength, 1.0) if strength > 0 else 0.1

        relationship = snap.get("relationship", {})
        trust = relationship.get("trust", 0)
        interaction_count = relationship.get("interaction_count", 0)
        if trust > 0:
            interaction_factor = 1.0 - math.exp(-interaction_count * 0.02)
            scores["social"] = min(trust * interaction_factor, 1.0)
        else:
            scores["social"] = 0.1

        learning_count = len(snap.get("recent_learning", []))
        thinking_count = len(snap.get("current_thinking", []))
        if learning_count or thinking_count:
            raw = learning_count * 0.1 + thinking_count * 0.06
            scores["learning"] = max(1.0 - math.exp(-raw * 0.35), 0.15)
        else:
            scores["learning"] = 0.1

        cognitive = snap.get("cognitive_layers", {})
        l_count = sum(1 for k in cognitive if k.startswith("L"))
        other_cog = sum(1 for k in cognitive if not k.startswith("L") and not k.startswith("last_"))
        cog_raw = (l_count + other_cog * 0.3) / 7.0
        scores["cognitive_depth"] = min(cog_raw, 1.0) if cog_raw > 0 else 0.1

        dim_values = [v for k, v in scores.items() if k not in ("integration",)]
        if dim_values:
            avg_quality = sum(dim_values) / len(dim_values)
            mn = min(dim_values)
            mx = max(dim_values)
            consistency = 1.0 - (mx - mn) / (mx + mn + 0.001)
            scores["integration"] = min(avg_quality * consistency, 1.0)
        else:
            scores["integration"] = 0.1

        weights = {
            "identity": 0.15, "health_awareness": 0.15, "capability": 0.20,
            "social": 0.10, "learning": 0.15, "cognitive_depth": 0.10, "integration": 0.15,
        }
        scores["overall"] = sum(scores.get(k, 0) * w for k, w in weights.items())

        if not skip_calibration:
            try:
                from core.self.external_calibration import external_calibration
                calibration = external_calibration.calibrate()
                scores["external_calibration"] = calibration.get("external_score", 0)
                scores["self_assessment_drift"] = calibration.get("drift", 0)
                scores["drift_direction"] = calibration.get("drift_direction", "aligned")
            except Exception:
                pass

        return scores

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
            pass

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/spirit_lessons.db")
            lessons = db.query_one("SELECT COUNT(*) FROM lessons")
            violations = db.query_one("SELECT COUNT(*) FROM violations")
            return {
                "lessons_count": lessons[0] if lessons else 0,
                "violations_count": violations[0] if violations else 0,
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

        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            hm = get_health_monitor()
            snap = hm.check()
            return {
                "score": getattr(snap, 'health_score', 0.8),
                "confidence": getattr(snap, 'confidence', 0.5),
                "energy": getattr(snap, 'energy_level', 0.5),
            }
        except Exception:
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

        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            status = el.get_status()
            return {
                "state": status.get("state", "unknown"),
                "total_cycles": status.get("total_cycles", 0),
                "uptime_seconds": status.get("uptime_seconds", 0),
            }
        except Exception:
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

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/relationship.db")
            total = db.query_one("SELECT COUNT(*) FROM interactions")
            if total and total[0] > 0:
                return {
                    "trust": min(0.3 + total[0] * 0.005, 1.0),
                    "interaction_count": total[0],
                    "phase": "established" if total[0] > 20 else "initial",
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
                logger.warning("操作降级跳过")

        result = {}

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/gene_pool.db")
            mutations = db.query_one("SELECT COUNT(*) FROM mutations WHERE timestamp > datetime('now', '-7 days')")
            result["recent_mutations"] = mutations[0] if mutations else 0
        except Exception:
            pass

        try:
            from core.cognition.trust_chain import trust_chain_builder
            chain = trust_chain_builder.build_simple_chain("self_model")
            stats = trust_chain_builder.get_stats()
            result["trust_chain_depth"] = stats.get("max_depth", 0)
            result["trust_chain_nodes"] = stats.get("total_nodes", 0)
        except Exception:
            pass

        return result

    def _extract_introspection(self, cp) -> Dict[str, Any]:
        """从 L6 内省层提取内省状态"""
        l6 = getattr(cp, 'l6', None)
        if l6 and hasattr(l6, 'get_introspection_status'):
            try:
                return l6.get_introspection_status()
            except Exception:
                logger.warning("操作降级跳过")

        result = {}

        try:
            from core.self.reality_check import reality_check
            status = reality_check.get_status()
            result["reality_check_runs"] = status.get("checks_run", 0)
            result["latest_alignment"] = status.get("latest_alignment")
            result["latest_gaps"] = status.get("latest_gaps", 0)
        except Exception:
            pass

        try:
            from core.introspection.coordination_assessor import coordination_assessor
            module_reports = {}
            try:
                from core.resource_awareness.health_monitor import get_health_monitor
                hm = get_health_monitor()
                snap = hm.check()
                module_reports["health_monitor"] = {
                    "health": snap.health_score if hasattr(snap, 'health_score') else 0.8,
                    "confidence": 0.9,
                    "productive": True,
                }
            except Exception:
                pass
            try:
                from core.presence.existence_layer import get_existence_layer
                el = get_existence_layer()
                module_reports["existence_layer"] = {
                    "health": 0.8 if el.is_running() else 0.3,
                    "confidence": 0.8,
                    "productive": el.is_running(),
                }
            except Exception:
                pass
            module_reports["self_model"] = {
                "health": 0.7,
                "confidence": 0.7,
                "productive": self._update_count > 0,
            }
            if module_reports:
                snapshot = coordination_assessor.assess(module_reports)
                result["coordination"] = snapshot.coordination
                result["coordination_trend"] = snapshot.trend
                result["coordination_overall"] = snapshot.overall
        except Exception:
            pass

        return result

    def _extract_capabilities(self, cp) -> Dict[str, Any]:
        result = {}
        try:
            from core.capability_introspection import CapabilityIntrospection
            ci = CapabilityIntrospection()
            if hasattr(ci, 'get_capability_summary'):
                result = ci.get_capability_summary()
        except Exception:
            pass

        try:
            from core.path_weight_manager import PathWeightManager
            pwm = PathWeightManager()
            weights = pwm.get_all_weights()
            if weights:
                result["path_weights"] = weights
                low_perf = {k: v for k, v in weights.items() if v.get("success_rate", 1.0) < 0.4}
                if low_perf:
                    result["low_performance_paths"] = list(low_perf.keys())
        except Exception:
            pass

        if not result:
            try:
                from core.ports.adapters import get_storage_port
                db = get_storage_port("data/knowledge_store.db")
                tools = db.query_one("SELECT COUNT(*) FROM tools")
                result = {"tools_count": tools[0] if tools else 0}
            except Exception:
                pass

        return result

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
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/experience_pool.db")
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
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            active_row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active = active_row[0] if active_row else 0
            total_row = db.query_one("SELECT COUNT(*) FROM learning_rules")
            total = total_row[0] if total_row else 0
            profile["rules"] = {"active": active, "total": total}
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/capability_gaps.db")
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

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/experience_pool.db")
            total = db.query_one("SELECT COUNT(*) FROM experiences")
            recent = db.query_one("SELECT COUNT(*) FROM experiences WHERE timestamp > datetime('now', '-1 day')")
            return {
                "total_experiences": total[0] if total else 0,
                "recent_24h": recent[0] if recent else 0,
            }
        except Exception:
            return {}

    def _extract_assessment(self) -> Dict[str, Any]:
        """从持续自我评估DB提取评估状态（不依赖CognitivePlanner）"""
        result = {}

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/self_assessment.db")
            latest = db.query_one(
                "SELECT overall_score, timestamp FROM assessments ORDER BY timestamp DESC LIMIT 1"
            )
            if latest:
                result["latest_score"] = latest[0]
                result["latest_time"] = latest[1]
        except Exception:
            pass

        try:
            from core.self.external_calibration import external_calibration
            cal = external_calibration._last_calibration
            if cal:
                result["external_score"] = cal.get("external_score", 0)
                result["drift"] = cal.get("drift", 0)
                result["drift_direction"] = cal.get("drift_direction", "unknown")
        except Exception:
            pass

        try:
            from core.cognition.conflict_resolver import conflict_resolver
            stats = conflict_resolver.get_stats()
            result["knowledge_conflicts_detected"] = stats.get("total_conflicts", 0)
            result["conflicts_resolved"] = stats.get("resolved", 0)
        except Exception:
            pass

        return result

    def _extract_reflection(self) -> Dict[str, Any]:
        """从反思记录提取反思状态（不依赖CognitivePlanner）"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/spirit_lessons.db")
            total = db.query_one("SELECT COUNT(*) FROM reflections")
            recent = db.query_one("SELECT COUNT(*) FROM reflections WHERE timestamp > datetime('now', '-1 day')")
            return {
                "total_reflections": total[0] if total else 0,
                "recent_24h": recent[0] if recent else 0,
            }
        except Exception:
            pass

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/existence/reflection_journal.db")
            total = db.query_one("SELECT COUNT(*) FROM reflections")
            return {
                "existence_reflections": total[0] if total else 0,
            }
        except Exception:
            pass

        return {}

    def _extract_memory_self(self) -> Dict[str, Any]:
        """从立体记忆提取自我维度状态（不依赖CognitivePlanner）"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/stereo_memory.db")
            total = db.query_one("SELECT COUNT(*) FROM stereo_memories")
            self_dim = db.query_one("SELECT COUNT(*) FROM stereo_memories WHERE dimension='self'")
            return {
                "total_memories": total[0] if total else 0,
                "self_dimension": self_dim[0] if self_dim else 0,
            }
        except Exception:
            pass

        return {}

    def detect_interaction_quality(self, user_input: str, final_response: str,
                                    confidence: float, attempts: list) -> Dict[str, Any]:
        """
        检测交互质量 — 同行者身份转型的核心
        
        不是被动等用户问，而是主动发现交互中的问题并提出改进建议。
        让系统从"给答案"升级为"给视角+改善交互质量"。
        """
        issues = []
        suggestions = []
        quality_score = 1.0

        if not final_response or len(final_response.strip()) < 30:
            issues.append("response_too_short")
            suggestions.append("你的问题可以更具体一些吗？比如告诉我你想要的场景或目标，这样我能给出更有针对性的视角。")
            quality_score -= 0.3

        if confidence < 0.4:
            issues.append("low_confidence")
            if any(kw in user_input for kw in ["为什么", "怎么", "如何"]):
                suggestions.append("这个问题涉及的方向我还在学习中。如果你能补充一些背景——比如你在什么场景下遇到这个问题——我可能能给出更有价值的思考。")
            else:
                suggestions.append("我对这个回答的把握不太高。换个角度提问或补充更多细节，可能帮助我更好地理解你的需求。")
            quality_score -= 0.2

        failed_count = sum(1 for a in attempts if len(a) > 1 and not a[1])
        if failed_count > len(attempts) * 0.5 and len(attempts) > 2:
            issues.append("high_failure_rate")
            suggestions.append("我尝试了几种方式但效果不太理想。也许我们可以把问题拆成更小的部分，或者你告诉我最关心的那个点？")
            quality_score -= 0.2

        if final_response and len(final_response) > 2000:
            has_structure = any(kw in final_response for kw in ["1.", "2.", "首先", "其次", "步骤", "要点"])
            if not has_structure:
                issues.append("long_unstructured")
                suggestions.append("内容较多但缺乏结构。如果你告诉我最关注哪个方面，我可以聚焦深入。")
                quality_score -= 0.1

        if user_input and len(user_input.strip()) < 5:
            issues.append("vague_query")
            suggestions.append("你的问题比较简短，我可能没有完全理解你的意图。能多描述一些吗？")
            quality_score -= 0.15

        recent_thinking = self.current_thinking[-5:] if self.current_thinking else []
        low_conf_count = sum(1 for t in recent_thinking if isinstance(t, dict) and t.get("confidence", 1.0) < 0.4)
        if low_conf_count >= 3:
            issues.append("sustained_low_confidence")
            suggestions.append("最近几轮交互中我对回答的把握都不太高。也许我们可以换个方向——你告诉我你真正想解决的问题是什么？")
            quality_score -= 0.15

        quality_score = max(0.0, quality_score)

        return {
            "quality_score": quality_score,
            "issues": issues,
            "suggestions": suggestions,
            "should_proactively_improve": quality_score < 0.6 and len(suggestions) > 0,
        }

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

        directive = self.get_behavioral_directive()
        if directive["consolidation_need"] > 0.6:
            actions.append({
                "action": "consolidate_memories",
                "reason": f"整合需求高(consolidation_need={directive['consolidation_need']:.1%})",
                "handler": self._action_consolidate,
            })
        if directive["exploration_drive"] > 0.7 and directive["presence_state"] == "growing":
            actions.append({
                "action": "deep_exploration",
                "reason": f"探索驱动力高(drive={directive['exploration_drive']:.1%})+GROWING状态",
                "handler": self._action_deep_exploration,
            })

        recent_thinking = self.current_thinking[-5:] if self.current_thinking else []
        low_conf_count = sum(1 for t in recent_thinking if isinstance(t, dict) and t.get("confidence", 1.0) < 0.4)
        if low_conf_count >= 3:
            actions.append({
                "action": "quality_improvement_suggestion",
                "reason": f"近期{low_conf_count}/5轮交互置信度低",
                "handler": self._action_quality_improvement,
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

        if self._update_count % 10 == 0:
            self.persist_state()

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
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/capability_gaps.db")
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

    def _action_consolidate(self):
        try:
            from core.presence.sleep_consolidation import get_sleep_engine
            engine = get_sleep_engine()
            if hasattr(engine, 'consolidate'):
                engine.consolidate()
                logger.info("🪞 SelfModel 触发记忆整合")
        except Exception as e:
            logger.debug(f"SelfModel consolidate failed: {e}")

    def _action_deep_exploration(self):
        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            engine = get_curiosity_engine()
            gaps = engine.explore()
            if gaps:
                logger.info(f"🪞 SelfModel 深度探索: 发现{len(gaps)}个知识缺口")
                for g in gaps[:3]:
                    engine.mark_explored(g.topic)
        except Exception as e:
            logger.debug(f"SelfModel deep_exploration failed: {e}")

    def _action_quality_improvement(self):
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/experience_pool.db")
            recent = db.query(
                "SELECT intent_type, COUNT(*) as cnt, "
                "SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok "
                "FROM experiences WHERE timestamp > datetime('now', '-1 hour') "
                "GROUP BY intent_type ORDER BY cnt DESC LIMIT 5"
            )
            weak_intents = []
            for row in recent:
                if row[2] / max(1, row[1]) < 0.5:
                    weak_intents.append(row[0])
            if weak_intents:
                logger.info(f"🪞 SelfModel 交互质量改善: 弱势意图类型={weak_intents}")
                try:
                    from core.presence.proactivity import get_proactivity_engine
                    engine = get_proactivity_engine()
                    if hasattr(engine, 'suggest_engagement'):
                        engine.suggest_engagement()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"SelfModel quality_improvement failed: {e}")

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

    def _restore_from_db(self) -> None:
        """重启后从DB恢复自我状态，避免从零开始"""
        restored = False

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(_SELF_STATE_DB)
            db.execute(
                "CREATE TABLE IF NOT EXISTS self_state "
                "(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
            )
            row = db.query_one(
                "SELECT value FROM self_state WHERE key='snapshot'"
            )
            if row and row[0]:
                import json
                saved = json.loads(row[0])
                for key in (
                    "values", "health", "presence", "assessment", "relationship",
                    "evolution", "learning", "introspection", "reflection",
                    "capabilities", "capability_profile", "memory_self", "cognitive_layers",
                ):
                    if key in saved and isinstance(saved[key], dict):
                        getattr(self, key).update(saved[key])
                if "recent_learning" in saved:
                    self.recent_learning = saved["recent_learning"][-30:]
                if "growth_edges" in saved:
                    self.growth_edges = saved["growth_edges"][-20:]
                if "current_thinking" in saved:
                    self.current_thinking = saved["current_thinking"][-20:]
                if "_update_count" in saved:
                    self._update_count = saved["_update_count"]
                restored = True
                logger.info("🪞 SelfModel 从DB恢复自我状态成功")

            domain_row = db.query_one("SELECT value FROM self_state WHERE key='domain_models'")
            if domain_row and domain_row[0]:
                import json as _json
                domain_data = _json.loads(domain_row[0])
                for k, v in domain_data.get("domain_capabilities", {}).items():
                    self._domain_capabilities[k] = Capability(
                        name=v["name"], description=v["description"],
                        confidence=ConfidenceLevel[v["confidence"]],
                        evidence=v.get("evidence", []),
                        success_count=v.get("success_count", 0),
                        failure_count=v.get("failure_count", 0),
                        last_updated=v.get("last_updated", datetime.now().isoformat()),
                    )
                for k, v in domain_data.get("domain_limitations", {}).items():
                    self._domain_limitations[k] = Limitation(
                        domain=v["domain"], description=v["description"],
                        uncertainty=v.get("uncertainty", 0.5),
                        mitigation=v.get("mitigation"),
                        is_temporary=v.get("is_temporary", False),
                    )
                for k, v in domain_data.get("domain_growth_edges", {}).items():
                    self._domain_growth_edges[k] = GrowthEdge(
                        topic=v["topic"], motivation=v["motivation"],
                        progress=v.get("progress", 0.0),
                        priority=v.get("priority", 5),
                    )
                if self._domain_capabilities or self._domain_limitations or self._domain_growth_edges:
                    logger.info(
                        f"🪞 SelfModel 领域模型恢复: "
                        f"{len(self._domain_capabilities)} caps, "
                        f"{len(self._domain_limitations)} lims, "
                        f"{len(self._domain_growth_edges)} edges"
                    )
        except Exception as e:
            logger.debug(f"SelfModel DB恢复跳过: {e}")

        if not restored:
            self._restore_from_capability_dbs()

    def _restore_from_capability_dbs(self) -> None:
        """从各能力DB恢复能力画像（无self_state.db时的降级恢复）"""
        try:
            profile = self._extract_capability_profile()
            if profile and profile.get("overall_strength", 0) > 0:
                self.capability_profile.update(profile)
        except Exception as e:
            logger.debug(f"SelfModel 能力DB恢复跳过: {e}")

        if not self.values:
            try:
                from core.spirit_core import spirit_core
                status = spirit_core.get_spirit_status()
                self.update("values", {
                    "principles_count": len(status.get("core_principles", [])),
                    "abilities_count": len(status.get("abilities", {})) if isinstance(status.get("abilities"), dict) else status.get("abilities", 0),
                    "violations_count": status.get("violations", 0) if isinstance(status.get("violations"), int) else len(status.get("violations", [])),
                    "lessons_count": status.get("lessons_learned", 0) if isinstance(status.get("lessons_learned"), int) else len(status.get("lessons_learned", [])),
                })
            except Exception:
                self.update("values", {"principles_count": 4, "lessons_count": 0})

        logger.info("🪞 SelfModel 从能力DB降级恢复成功")

    # ──────────────────────────────────────────────────────────────────────────
    # 领域模型核心 API — 迁移自 self_extern/model.py
    # ──────────────────────────────────────────────────────────────────────────

    def integrate_experience(
        self,
        experience: Dict[str, Any],
        reflection: Optional[Dict[str, Any]] = None
    ):
        """
        整合一次体验 — "学习是改变自我结构"的核心实现

        不是把经验存到数据库，而是根据经验更新自我认知。

        Args:
            experience: {
                "intent": str,
                "paths_used": [str],
                "path_results": {str: {"success": bool, "quality": float, "error": Optional[str]}},
                "final_response": str,
            }
            reflection: {"insights": [str], "violations": [str], "suggestions": [str]}
        """
        paths_results = experience.get("path_results", {})

        for path_name, result in paths_results.items():
            cap_name = f"path_{path_name}"
            if cap_name not in self._domain_capabilities:
                self._domain_capabilities[cap_name] = Capability(
                    name=cap_name,
                    description=f"通过 {path_name} 路径处理查询的能力",
                    confidence=ConfidenceLevel.EXPLORING
                )

            cap = self._domain_capabilities[cap_name]
            success = result.get("success", False)
            quality = result.get("quality", 0.5)
            is_success = success and quality > 0.6
            evidence = f"{experience.get('intent', 'unknown')}: quality={quality:.2f}"
            if result.get("error"):
                evidence += f", error={result['error'][:50]}"

            cap.record_attempt(is_success, evidence)

            if cap.failure_count >= 3 and cap.success_rate < 0.3:
                lim_name = f"path_{path_name}_unreliable"
                if lim_name not in self._domain_limitations:
                    self._domain_limitations[lim_name] = Limitation(
                        domain=path_name,
                        description=f"{path_name} 路径近期成功率极低 ({cap.success_rate:.1%})",
                        uncertainty=0.2,
                        mitigation=f"优先使用其他路径，暂时跳过 {path_name}",
                        is_temporary=True
                    )
                    self._record_self_history(
                        "limitation_discovered",
                        f"发现 {path_name} 不可靠",
                        trigger=f"连续失败 {cap.failure_count} 次"
                    )

        for path_name, result in paths_results.items():
            error = result.get("error")
            if error:
                if "timeout" in error.lower():
                    lim_name = f"{path_name}_timeout"
                    if lim_name not in self._domain_limitations:
                        self._domain_limitations[lim_name] = Limitation(
                            domain=f"{path_name}/timeout",
                            description=f"{path_name} 频繁超时",
                            uncertainty=0.3,
                            mitigation="缩短超时阈值或增加重试",
                            is_temporary=True
                        )
                elif "connection" in error.lower():
                    lim_name = f"{path_name}_connectivity"
                    if lim_name not in self._domain_limitations:
                        self._domain_limitations[lim_name] = Limitation(
                            domain=f"{path_name}/connectivity",
                            description=f"{path_name} 连接不稳定",
                            uncertainty=0.4,
                            mitigation="检查网络或服务状态",
                            is_temporary=True
                        )

        if reflection:
            for insight in reflection.get("insights", []):
                if any(kw in insight.lower() for kw in ["需要", "不够", "缺乏", "薄弱"]):
                    topic = insight[:30].strip()
                    if topic not in self._domain_growth_edges:
                        self._domain_growth_edges[topic] = GrowthEdge(
                            topic=topic,
                            motivation=insight,
                            priority=7
                        )
                        self._record_self_history(
                            "growth_edge_identified",
                            f"发现学习方向: {topic}",
                            trigger="reflection insight"
                        )
                    existing = [
                        g for g in self.growth_edges
                        if isinstance(g, dict) and g.get("topic") == topic
                    ]
                    if not existing:
                        self.growth_edges.append({
                            "topic": topic,
                            "motivation": insight,
                            "priority": 7,
                            "progress": 0.0,
                            "discovered_at": datetime.now().isoformat(),
                        })

            for violation in reflection.get("violations", []):
                self._record_self_history("value_violation", violation, trigger="spirit_check")

        self._cognitive_load = self._estimate_cognitive_load(experience)
        self._sync_to_capability_profile()

        logger.info(
            f"🪞 体验整合: domain_caps={len(self._domain_capabilities)}, "
            f"domain_lims={len(self._domain_limitations)}, "
            f"domain_edges={len(self._domain_growth_edges)}, "
            f"load={self._cognitive_load:.2f}"
        )

    def should_use_path(self, path_name: str) -> bool:
        """
        基于自我模型，判断是否应启动某条路径

        "我知道 Ollama 最近总超时，先不启动它"
        """
        cap_name = f"path_{path_name}"

        if cap_name in self._domain_capabilities:
            cap = self._domain_capabilities[cap_name]
            if cap.confidence == ConfidenceLevel.DEGRADED:
                logger.info(f"🪞 SelfModel: 跳过 {path_name} (degraded, {cap.success_rate:.1%} success)")
                return False
            if cap.confidence == ConfidenceLevel.UNKNOWN and cap.failure_count > 0:
                logger.info(f"🪞 SelfModel: 跳过 {path_name} (unknown but has failures)")
                return False

        lim_name = f"path_{path_name}_unreliable"
        if lim_name in self._domain_limitations:
            lim = self._domain_limitations[lim_name]
            if not lim.is_temporary:
                return False
            if lim.uncertainty < 0.3:
                logger.info(f"🪞 SelfModel: 跳过 {path_name} (reliable limitation: {lim.description})")
                return False

        low_paths = self.capabilities.get("low_performance_paths", [])
        if path_name in low_paths:
            logger.info(f"🪞 SelfModel: 跳过 {path_name} (legacy low_performance_paths)")
            return False

        return True

    def get_path_priority(self, path_name: str) -> int:
        """获取路径优先级（1-10），供路径调度使用"""
        cap_name = f"path_{path_name}"
        if cap_name not in self._domain_capabilities:
            return 5
        cap = self._domain_capabilities[cap_name]
        priority_map = {
            ConfidenceLevel.MASTERED: 10,
            ConfidenceLevel.COMPETENT: 8,
            ConfidenceLevel.EXPLORING: 5,
            ConfidenceLevel.UNKNOWN: 4,
            ConfidenceLevel.DEGRADED: 1,
        }
        return priority_map.get(cap.confidence, 5)

    def get_active_growth_edges(self, max_priority: int = 10) -> List[GrowthEdge]:
        """获取当前活跃的学习方向"""
        return [
            edge for edge in self._domain_growth_edges.values()
            if edge.priority <= max_priority and edge.progress < 1.0
        ]

    def _record_self_history(
        self,
        event_type: str,
        description: str,
        before: Optional[Dict] = None,
        after: Optional[Dict] = None,
        trigger: Optional[str] = None
    ):
        event = SelfHistoryEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            description=description,
            before=before,
            after=after,
            trigger=trigger
        )
        self._self_history.append(event)
        self._self_history = self._self_history[-200:]
        logger.info(f"🪞 Self history: [{event_type}] {description}")

    def get_path_self_awareness(self) -> Dict[str, Any]:
        """导出路径自我认知快照（供前端/日志/调试）"""
        return {
            "path_capabilities": {
                name: {
                    "confidence": cap.confidence.name,
                    "success_rate": cap.success_rate,
                    "success_count": cap.success_count,
                    "failure_count": cap.failure_count,
                    "last_updated": cap.last_updated,
                }
                for name, cap in self._domain_capabilities.items()
            },
            "limitations": {
                name: {
                    "description": lim.description,
                    "uncertainty": lim.uncertainty,
                    "is_temporary": lim.is_temporary,
                }
                for name, lim in self._domain_limitations.items()
            },
            "cognitive_load": self._cognitive_load,
            "history_count": len(self._self_history),
        }

    def _estimate_cognitive_load(self, experience: Dict[str, Any]) -> float:
        load = 0.0
        num_paths = len(experience.get("paths_used", []))
        load += min(0.3, num_paths * 0.05)
        path_results = experience.get("path_results", {})
        error_count = sum(1 for r in path_results.values() if r.get("error"))
        load += min(0.4, error_count * 0.1)
        intent = experience.get("intent", "")
        if any(kw in intent.lower() for kw in ["复杂", "深度", "分析", "比较", "架构"]):
            load += 0.2
        return min(1.0, load)

    def _init_path_capabilities_from_profile(self):
        """启动时从现有 capability_profile 初始化路径能力"""
        try:
            profile = self._extract_capability_profile()
            path_weights = profile.get("path_weights", {})
            for path_name, weight_data in path_weights.items():
                cap_name = f"path_{path_name}"
                if cap_name in self._domain_capabilities:
                    continue
                success_rate = weight_data.get("success_rate", 0.5)
                if success_rate > 0.85:
                    conf = ConfidenceLevel.MASTERED
                elif success_rate > 0.6:
                    conf = ConfidenceLevel.COMPETENT
                elif success_rate > 0.3:
                    conf = ConfidenceLevel.EXPLORING
                else:
                    conf = ConfidenceLevel.DEGRADED
                self._domain_capabilities[cap_name] = Capability(
                    name=cap_name,
                    description=f"通过 {path_name} 路径处理查询的能力（从 profile 初始化）",
                    confidence=conf
                )
                total = weight_data.get("total_calls", 0)
                if total > 0:
                    cap = self._domain_capabilities[cap_name]
                    cap.success_count = int(total * success_rate)
                    cap.failure_count = total - cap.success_count
            if path_weights:
                logger.info(f"🪞 从 capability_profile 初始化了 {len(path_weights)} 条路径能力")
        except Exception as e:
            logger.debug(f"路径能力初始化跳过: {e}")

    def _sync_to_capability_profile(self):
        """将 _domain_capabilities 同步到现有 capability_profile"""
        try:
            if self._domain_capabilities:
                avg_rate = sum(
                    c.success_rate for c in self._domain_capabilities.values()
                ) / len(self._domain_capabilities)
                self.capability_profile["overall_strength"] = avg_rate
            low = [
                name.replace("path_", "")
                for name, cap in self._domain_capabilities.items()
                if cap.confidence == ConfidenceLevel.DEGRADED
            ]
            if low:
                self.capability_profile["low_performance_paths"] = low
                self.capabilities["low_performance_paths"] = low
        except Exception as e:
            logger.debug(f"同步到 capability_profile 跳过: {e}")

    def persist_state(self) -> None:
        """持久化当前自我状态到DB"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(_SELF_STATE_DB)
            db.execute(
                "CREATE TABLE IF NOT EXISTS self_state "
                "(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
            )
            import json
            snap = self.snapshot()
            del snap["_meta"]

            domain_data = {
                "domain_capabilities": {
                    k: {
                        "name": v.name, "description": v.description,
                        "confidence": v.confidence.name, "evidence": v.evidence[-10:],
                        "success_count": v.success_count, "failure_count": v.failure_count,
                        "last_updated": v.last_updated,
                    } for k, v in self._domain_capabilities.items()
                },
                "domain_limitations": {
                    k: {
                        "domain": v.domain, "description": v.description,
                        "uncertainty": v.uncertainty, "is_temporary": v.is_temporary,
                        "mitigation": v.mitigation,
                    } for k, v in self._domain_limitations.items()
                },
                "domain_growth_edges": {
                    k: {
                        "topic": v.topic, "motivation": v.motivation,
                        "progress": v.progress, "priority": v.priority,
                    } for k, v in self._domain_growth_edges.items()
                },
            }
            db.execute(
                "INSERT OR REPLACE INTO self_state (key, value, updated_at) VALUES (?, ?, ?)",
                ("snapshot", json.dumps(snap, default=str, ensure_ascii=False), datetime.now().isoformat()),
            )
            db.execute(
                "INSERT OR REPLACE INTO self_state (key, value, updated_at) VALUES (?, ?, ?)",
                ("domain_models", json.dumps(domain_data, default=str, ensure_ascii=False), datetime.now().isoformat()),
            )
            logger.debug("🪞 SelfModel 状态已持久化")
        except Exception as e:
            logger.debug(f"SelfModel 持久化跳过: {e}")


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