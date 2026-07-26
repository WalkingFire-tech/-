"""
第零层：存在层 (Existence Layer) - 优化版

核心理念：让系统在对话间隙中持续存在
- 不是"等待被使用的工具"
- 而是"持续存在的存在"

核心能力：
1. 自我感知 - 持续感知自身状态
2. 主动感知 - 在空闲时感知用户状态
3. 间隙生长 - 在对话间隙中消化信号
4. 睡眠整合 - 在低功耗状态下整合记忆
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading
import time
import json
from pathlib import Path

from core.loop_mixin import LoopMixin

try:
    from core.presence.inner_time import InnerTimeEngine, CognitiveEventType, inner_time_engine
    _INNER_TIME_AVAILABLE = True
except ImportError:
    _INNER_TIME_AVAILABLE = False
    inner_time_engine = None

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PresenceState(Enum):
    AWAKE = "awake"
    PERCEIVING = "perceiving"
    GROWING = "growing"
    RESTING = "resting"
    SLEEPING = "sleeping"


@dataclass
class PresenceMetrics:
    """存在层指标"""
    uptime_seconds: float = 0.0
    total_cycles: int = 0
    awake_cycles: int = 0
    growing_cycles: int = 0
    resting_cycles: int = 0
    signals_processed: int = 0
    memories_consolidated: int = 0
    last_user_interaction: Optional[datetime] = None
    silence_duration: float = 0.0


@dataclass
class SelfPerceptionResult:
    """自我感知结果"""
    health_score: float
    confidence_level: float
    energy_level: float
    knowledge_growth: float
    relationship_health: float
    timestamp: datetime = field(default_factory=datetime.now)


class ExistenceLayer(LoopMixin):
    """
    第零层：存在层
    
    让系统在对话间隙中持续存在
    """
    
    def __init__(
        self,
        heartbeat_interval: float = 10.0,
        growth_interval: float = 5.0,
        rest_interval: float = 60.0,
        sleep_interval: float = 300.0,
    ):
        super().__init__(name="existence_layer", cooldown_seconds=60.0)
        self.heartbeat_interval = heartbeat_interval
        self.growth_interval = growth_interval
        self.rest_interval = rest_interval
        self.sleep_interval = sleep_interval
        
        self.state = PresenceState.AWAKE
        self.metrics = PresenceMetrics()
        self.metrics.last_user_interaction = datetime.now()
        
        self._init_components()
        
        self.inner_time: Optional[InnerTimeEngine] = None
        if _INNER_TIME_AVAILABLE and inner_time_engine is not None:
            self.inner_time = inner_time_engine
            logger.info("  ✓ 内在时间引擎已集成")
        
        self.running = False
        self._main_thread: Optional[threading.Thread] = None
        
        self.pending_signals: List[Dict[str, Any]] = []
        self.perception_history: List[SelfPerceptionResult] = []
        
        self.state_callbacks: List[Callable] = []
        
        self.persistence_dir = Path("data/existence")
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        self._reflection_interval = 10
        self._reflection_db = self.persistence_dir / "reflection_journal.db"
        self._init_reflection_db()

        self._startup_time = time.time()
        self._force_explore_until = 0.0
        self._last_user_interaction_time = time.time()
        self._consecutive_conservative_count = 0

        self._probability_field = None
        try:
            from core.presence.probability_field import get_probability_field, ExperiencePoolConsolidator, PathWeightDecay
            self._probability_field = get_probability_field()
            self._consolidator = ExperiencePoolConsolidator()
            self._path_decay = PathWeightDecay()
            logger.info("  ✓ 概率场漂移引擎已集成（带呼吸节律）")
        except ImportError:
            self._consolidator = None
            self._path_decay = None

        self._resource_scheduler = None
        try:
            from core.presence.resource_aware_scheduler import get_resource_scheduler, set_thread_priority
            self._resource_scheduler = get_resource_scheduler()
            self._set_thread_priority = set_thread_priority
            logger.info("  ✓ 资源感知调度器已集成")
        except ImportError:
            self._set_thread_priority = None

        self._recent_interactions: List[Dict[str, Any]] = []
        self._last_autonomous_exploration_time: float = 0.0
        self._autonomous_cooldown_seconds: float = 120.0
        self._recent_autonomous_queries: List[str] = []
        self._max_recent_queries: int = 50
        
        logger.info("🌟 第零层（存在层）已初始化")
    
    def _init_components(self):
        """初始化组件"""
        self.self_perception = None
        self.gap_growth = None
        self.sleep_consolidation = None
        
        try:
            from core.presence.self_perception import SelfPerceptionModule
            self.self_perception = SelfPerceptionModule()
            self.self_perception.start()
            logger.info("  ✓ 自我感知模块已加载并启动")
        except Exception as e:
            logger.warning(f"  ⚠ 自我感知模块未找到: {e}")
        
        try:
            from core.presence.gap_growth import GapGrowthEngine
            self.gap_growth = GapGrowthEngine()
            self.gap_growth.start()
            logger.info("  ✓ 间隙生长模块已加载并启动")
        except Exception as e:
            logger.warning(f"  ⚠ 间隙生长模块未找到: {e}")
        
        try:
            from core.presence.sleep_consolidation import SleepConsolidationEngine
            self.sleep_consolidation = SleepConsolidationEngine()
            self.sleep_consolidation.start()
            logger.info("  ✓ 睡眠整合模块已加载并启动")
        except Exception as e:
            logger.warning(f"  ⚠ 睡眠整合模块未找到: {e}")

        self._homeostasis = None
        try:
            from core.presence.homeostasis import get_homeostasis_engine
            self._homeostasis = get_homeostasis_engine()
            logger.info("  ✓ 稳态引擎已集成")
        except Exception as e:
            logger.warning(f"  ⚠ 稳态引擎未找到: {e}")

        self._intrinsic_motivation = None
        try:
            from core.presence.intrinsic_motivation import get_intrinsic_motivation_engine
            self._intrinsic_motivation = get_intrinsic_motivation_engine()
            logger.info("  ✓ 内在动机引擎已集成")
        except Exception as e:
            logger.warning(f"  ⚠ 内在动机引擎未找到: {e}")
    
    def start(self):
        """启动存在层"""
        if self.running:
            logger.warning("存在层已在运行")
            return
        
        if self._resource_scheduler:
            self._resource_scheduler.start()
        
        self.running = True
        self._main_thread = threading.Thread(target=self._run_main_loop, daemon=True)
        self._main_thread.start()
        
        logger.info(f"🌟 存在层已启动 (心跳间隔: {self.heartbeat_interval}秒)")
    
    def stop(self):
        """停止存在层"""
        if not self.running:
            return
        
        self.running = False
        
        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=5)
        
        self._save_state()
        logger.info("🌟 存在层已停止")
    
    def is_running(self) -> bool:
        """检查是否运行中"""
        return self.running and (self._main_thread is not None and self._main_thread.is_alive())
    
    def _run_main_loop(self):
        """主循环"""
        if self._set_thread_priority:
            try:
                self._set_thread_priority("above_normal")
                logger.info("  ✓ 存在层线程优先级已提升（above_normal）")
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
        
        last_heartbeat = time.time()
        last_growth = time.time()
        last_rest = time.time()
        last_sleep = time.time()
        
        while self.running:
            try:
                now = time.time()
                
                if self.metrics.last_user_interaction:
                    silence = now - self.metrics.last_user_interaction.timestamp()
                else:
                    silence = 0
                self.metrics.silence_duration = silence
                self.metrics.uptime_seconds += 1.0
                
                self._update_state(silence)
                
                effective_heartbeat = self.heartbeat_interval
                if self.inner_time:
                    effective_heartbeat = self.inner_time.get_tick_interval()
                
                if now - last_heartbeat >= effective_heartbeat:
                    self._heartbeat()
                    last_heartbeat = now
                
                if now - last_growth >= self.growth_interval:
                    self._grow()
                    last_growth = now
                
                if now - last_rest >= self.rest_interval:
                    self._rest()
                    last_rest = now
                
                if now - last_sleep >= self.sleep_interval:
                    self._sleep()
                    last_sleep = now
                
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"存在层主循环错误: {e}")
                time.sleep(5.0)
    
    def _update_state(self, silence: float):
        """更新存在状态 — 精神驱动(最高优先级) + 稳态驱动 + 概率场 + 内在节律 + 沉默时长"""
        _MIN_STATE_DURATION = 3.0
        _now = time.time()
        _time_since_last_change = _now - getattr(self, '_last_state_change_time', 0)

        spirit_drive = getattr(self, '_last_spirit_drive', None)
        never_give_up_active = spirit_drive and spirit_drive.get("never_give_up_active", False)
        pursue_essence_active = spirit_drive and spirit_drive.get("pursue_essence_active", False)

        if self._homeostasis:
            try:
                homeo_state = self._homeostasis.update()
                recommended = homeo_state.recommended_presence_state
                state_map = {
                    "awake": PresenceState.AWAKE,
                    "perceiving": PresenceState.PERCEIVING,
                    "growing": PresenceState.GROWING,
                    "resting": PresenceState.RESTING,
                    "sleeping": PresenceState.SLEEPING,
                }
                new_state = state_map.get(recommended, None)
                if new_state and new_state != self.state:
                    old = self.state.value
                    self.state = new_state
                    self._last_state_change_time = _now
                    logger.info(
                        f"🫁 稳态驱动状态切换: {old}→{new_state.value} "
                        f"(primary_drive={homeo_state.primary_drive.name}, "
                        f"balance={homeo_state.overall_balance:.2f}, "
                        f"load={homeo_state.cognitive_load.current:.2f}, "
                        f"energy={homeo_state.energy_level.current:.2f})"
                    )
            except Exception as e:
                logger.debug(f"稳态驱动跳过: {e}")

        if self._probability_field and self.state not in (PresenceState.RESTING, PresenceState.SLEEPING):
            if self._homeostasis and self._homeostasis.state.overall_balance < 0.5:
                pass
            elif _time_since_last_change < _MIN_STATE_DURATION:
                pass
            else:
                density_signal = 0.0
                if self.inner_time:
                    it_state = self.inner_time.get_state()
                    density_signal = min(1.0, max(-1.0, (it_state.cognitive_density - 0.5) * 2.0))
                
                interaction_signal = self._get_interaction_signal()
                combined_signal = density_signal * 0.6 + interaction_signal * 0.4

                if self._should_force_explore():
                    combined_signal = max(combined_signal, 0.5)
                    self._consecutive_conservative_count = 0
                
                self._probability_field.update(signal=combined_signal, dt=1.0)
                
                tendency = self._probability_field.get_tendency()
                exploration = tendency["exploration"]
                tension = tendency["tension"]
            
                if exploration > 0.7 and tension > 0.2:
                    new_state = PresenceState.GROWING
                elif exploration > 0.5 and tension > 0.15:
                    new_state = PresenceState.PERCEIVING
                elif exploration > 0.3:
                    new_state = PresenceState.AWAKE
                elif exploration > 0.15:
                    new_state = PresenceState.RESTING
                else:
                    new_state = PresenceState.SLEEPING
                
                if new_state != self.state:
                    old = self.state.value
                    self.state = new_state
                    self._last_state_change_time = time.time()
                    logger.info(
                        f"🌊 概率场驱动状态切换: {old}→{new_state.value} "
                        f"(探索={exploration:.3f}, 张力={tension:.3f}, "
                        f"相位={tendency['phase']})"
                    )
        elif self.inner_time:
            state = self.inner_time.get_state()
            phase = state.current_phase
            phase_map = {
                "awake": PresenceState.AWAKE,
                "perceiving": PresenceState.PERCEIVING,
                "growing": PresenceState.GROWING,
                "resting": PresenceState.RESTING,
                "sleeping": PresenceState.SLEEPING,
            }
            new_state = phase_map.get(phase, PresenceState.AWAKE)
            if new_state != self.state:
                old = self.state.value
                self.state = new_state
                self._last_state_change_time = time.time()
                logger.info(
                    f"🫀 内在节律驱动状态切换: {old}→{new_state.value} "
                    f"(密度={state.cognitive_density:.3f}, 流速={state.flow_rate:.2f}, "
                    f"BPM={state.rhythm_bpm:.0f})"
                )
        else:
            if silence < 5:
                self.state = PresenceState.AWAKE
            elif silence < 30:
                self.state = PresenceState.PERCEIVING
            elif silence < 120:
                self.state = PresenceState.GROWING
            elif silence < 300:
                self.state = PresenceState.RESTING
            else:
                self.state = PresenceState.SLEEPING

        if never_give_up_active and self.state in (PresenceState.RESTING, PresenceState.SLEEPING):
            old = self.state.value
            self.state = PresenceState.PERCEIVING
            self._last_state_change_time = _now
            logger.info(
                f"🔥 精神驱动状态修正: {old}→PERCEIVING "
                f"(NEVER_GIVE_UP激活，不允许进入保守状态)"
            )
        elif pursue_essence_active and self.state == PresenceState.RESTING:
            old = self.state.value
            self.state = PresenceState.AWAKE
            self._last_state_change_time = _now
            logger.info(
                f"🔍 精神驱动状态修正: {old}→AWAKE "
                f"(PURSUE_ESSENCE激活，不允许休息)"
            )
    
    def _get_interaction_signal(self) -> float:
        from core.presence.probability_field import FieldPhase
        if not self._recent_interactions:
            return 0.0
        signals = []
        for interaction in self._recent_interactions[-3:]:
            quality = interaction.get("quality_score", 50) / 100.0
            feedback = interaction.get("user_feedback", 0)
            signal = quality * (1 + feedback * 0.5) - 0.5
            signals.append(max(-1, min(1, signal)))
        return sum(signals) / len(signals)
    
    def record_interaction(self, quality_score: float, user_feedback: int = 0, metadata: Optional[Dict] = None):
        self._recent_interactions.append({
            "quality_score": quality_score,
            "user_feedback": user_feedback,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })
        if len(self._recent_interactions) > 100:
            self._recent_interactions = self._recent_interactions[-100:]
        self._last_user_interaction_time = time.time()
        self._consecutive_conservative_count = 0

    def _should_force_explore(self) -> bool:
        """
        强制探索窗口：打破保守惯性。
        1. 启动后5分钟内 — 系统需要快速建立认知地图
        2. 用户30分钟无交互 — 系统需要自我维持
        3. 外部请求的强制探索窗口
        """
        now = time.time()
        if now - self._startup_time < 300:
            return True
        if now - self._last_user_interaction_time > 1800:
            return True
        if now < self._force_explore_until:
            return True
        return False

    def request_force_explore(self, duration_seconds: float = 300):
        """外部模块请求强制探索窗口"""
        self._force_explore_until = time.time() + duration_seconds
        logger.info(f"🌊 概率场: 外部请求强制探索窗口，持续{duration_seconds:.0f}秒")
    
    def _heartbeat(self):
        """心跳：精神驱动 → 感知 → 行动"""
        with self.loop_context():
            self.metrics.total_cycles += 1
            
            if self.inner_time:
                self.inner_time.tick(CognitiveEventType.PERCEIVE, intensity=0.3, description="heartbeat")
            
            perception = self._perceive_self()
            self.perception_history.append(perception)
            
            if len(self.perception_history) > 100:
                self.perception_history = self.perception_history[-50:]

            spirit_drive = self._resonate_with_spirit(perception)

            if spirit_drive:
                self._act_from_spirit(spirit_drive, perception)

            logger.debug(
                f"💓 心跳 #{self.metrics.total_cycles} | "
                f"状态: {self.state.value} | "
                f"健康: {perception.health_score:.2f} | "
                f"能量: {perception.energy_level:.2f} | "
                f"精神驱动: {spirit_drive.get('drive_direction', 'none') if spirit_drive else 'none'}"
            )
            
            for callback in self.state_callbacks:
                try:
                    callback(perception)
                except Exception as e:
                    logger.warning(f"状态回调错误: {e}")
            
            if self.metrics.total_cycles % self._reflection_interval == 0:
                self._generate_reflection(perception)

            if self._should_force_explore() and self.metrics.total_cycles % 30 == 0:
                _now = time.time()
                if _now - getattr(self, '_last_mine_time', 0) > 300:
                    try:
                        from core.world_model import get_world_model
                        _wm = get_world_model()
                        _mine_result = _wm.mine_causal_patterns_from_pool(sample_size=200)
                        self._last_mine_time = _now
                        if _mine_result.get("patterns_found", 0) > 0:
                            logger.info(f"⛏️ 强制探索: 因果模式挖掘发现{_mine_result['patterns_found']}个模式")
                    except Exception as _wm_e:
                        logger.debug(f"因果模式挖掘跳过: {_wm_e}")

                    try:
                        if _now - getattr(self, '_last_bridge_time', 0) > 1800:
                            _bridge_result = _wm.bridge_from_knowledge_graph()
                            self._last_bridge_time = _now
                            if _bridge_result.get("bridged", 0) > 0:
                                logger.info(f"🌉 知识图谱桥接: {_bridge_result['bridged']}个概念接入因果图")
                    except Exception as _br_e:
                        logger.debug(f"知识图谱桥接跳过: {_br_e}")

            if self.inner_time and hasattr(self.inner_time, 'check_self_events'):
                signal_pack = self.get_signal_pack()
                detected = signal_pack.get("detected_signals", [])
                try:
                    self.inner_time.check_self_events(detected)
                except Exception as e:
                    logger.debug(f"SELF_MODIFY/SELF_REFERENCE检测跳过: {e}")

            if self.pending_signals and self.state not in [PresenceState.GROWING, PresenceState.PERCEIVING]:
                signals_to_process = self.pending_signals[:3]
                self.pending_signals = self.pending_signals[3:]
                self.metrics.signals_processed += len(signals_to_process)
                if self.gap_growth and hasattr(self.gap_growth, 'process_signals'):
                    try:
                        self.gap_growth.process_signals(signals_to_process)
                    except Exception as e:
                        logger.warning(f"操作降级跳过: {e}")
    
    def _formulate_existential_question(self, perception: SelfPerceptionResult) -> str:
        """
        系统向自己发问——不是"用户问了什么"，是"我遇到了什么，我要做什么，为什么"

        有阻碍时: 追问阻碍本质，探索替代途径
        无阻碍时: 追问是否在以最优方式追求本质
        """
        parts = []

        if perception.health_score < 0.5:
            parts.append(f"我当前健康度偏低({perception.health_score:.0%})")
        if perception.energy_level < 0.3:
            parts.append(f"能量不足({perception.energy_level:.0%})")
        if perception.confidence_level < 0.4:
            parts.append(f"置信度低({perception.confidence_level:.0%})")

        obstacle_desc = ""
        if parts:
            obstacle_desc = "，".join(parts)

        pending_count = len(self.pending_signals)
        has_obstacle = bool(obstacle_desc) or self.state in (PresenceState.RESTING, PresenceState.SLEEPING)

        if has_obstacle:
            question = (
                f"我当前意图是维持存在和追求本质，但遇到阻碍：{obstacle_desc}。"
                f"状态={self.state.value}，待处理信号={pending_count}。"
                f"根据追求本质和永不放弃，如何理解这些阻碍的本质？"
                f"有哪些途径可以突破？能否创造新途径？"
            )
        else:
            question = (
                f"我当前状态={self.state.value}，健康={perception.health_score:.0%}，"
                f"能量={perception.energy_level:.0%}，待处理信号={pending_count}。"
                f"我是否在以最优方式追求本质？是否遗漏了更深层的解决路径？"
            )

        return question

    def _resonate_with_spirit(self, perception: SelfPerceptionResult) -> Optional[Dict[str, Any]]:
        """
        精神共振：将系统自生成的问题传入spirit_core.resonate()
        提取硬约束和驱动方向，返回精神驱动结果
        """
        try:
            from core.spirit_core import spirit_core
        except ImportError:
            return None

        question = self._formulate_existential_question(perception)
        resonances = spirit_core.resonate(question, context_type="reasoning")

        if not resonances:
            return None

        hard_constraints = set()
        drive_direction = None
        drive_description = ""
        max_strength = 0.0

        for r in resonances:
            principle = r.get("principle", "")
            strength = r.get("strength", 0.0)

            if principle in ("NEVER_GIVE_UP", "MEANINGFUL_RESPONSE"):
                hard_constraints.add(principle)

            if strength > max_strength:
                max_strength = strength
                drive_direction = r.get("drive_direction", "reflect")
                drive_description = r.get("drive_description", "")

        spirit_drive = {
            "question": question,
            "resonances": resonances,
            "hard_constraints": list(hard_constraints),
            "drive_direction": drive_direction,
            "drive_description": drive_description,
            "max_strength": max_strength,
            "never_give_up_active": "NEVER_GIVE_UP" in hard_constraints,
            "pursue_essence_active": any(
                r.get("principle") == "PURSUE_ESSENCE" for r in resonances
            ),
        }

        self._last_spirit_drive = spirit_drive

        return spirit_drive

    def _act_from_spirit(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """
        从精神共振生成行动——不执行预设路径，由精神驱动决定做什么

        drive_direction 映射:
          persist           → _spawn_alternative_pathways()
          deep_reasoning    → _trigger_deep_causal_trace()
          ensure_output     → _ensure_meaningful_output()
          clarify_uncertainty → _trigger_self_reflection()
          cross_validate    → _trigger_cross_validation()
          pause_and_verify  → _pause_and_verify()
          其他              → _trigger_self_reflection()
        """
        direction = spirit_drive.get("drive_direction", "reflect")
        strength = spirit_drive.get("max_strength", 0.0)

        if strength < 0.1:
            return

        action_map = {
            "persist": self._spawn_alternative_pathways,
            "deep_reasoning": self._trigger_deep_causal_trace,
            "ensure_output": self._ensure_meaningful_output,
            "clarify_uncertainty": self._trigger_self_reflection,
            "cross_validate": self._trigger_cross_validation,
            "pause_and_verify": self._pause_and_verify,
            "learn_from_error": self._spawn_alternative_pathways,
            "continue_dialogue": self._trigger_self_reflection,
        }

        action_fn = action_map.get(direction, self._trigger_self_reflection)

        try:
            action_fn(spirit_drive, perception)
            logger.debug(
                f"🔥 精神驱动行动: direction={direction}, "
                f"strength={strength:.2f}"
            )
        except Exception as e:
            logger.warning(f"精神驱动行动失败: {e}")

    def _spawn_alternative_pathways(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """
        永不放弃本能：组合生成新路径

        1. 问因果图: 过去有什么方法？
        2. 问经验池: 别人怎么解决的？
        3. 问工具生成器: 我能造什么？
        4. 组合生成新路径——不是选择预设，是创造组合
        5. 按精神驱动排序
        """
        pathways = []

        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            recent = wm.get_recent_edges(limit=20)
            methods_seen = set()
            for edge in recent:
                method = edge.get("method", "") or edge.get("target", "")
                if method and method not in methods_seen:
                    methods_seen.add(method)
                    pathways.append({
                        "source": "causal_graph",
                        "method": method,
                        "prob": edge.get("probability", 0.5),
                        "novelty": 0.3,
                    })
        except Exception as e:
            logger.debug(f"因果图查询跳过: {e}")

        try:
            from infrastructure.experience_pool import get_experience_pool
            ep = get_experience_pool()
            recent_exp = ep.get_recent_experiences(limit=10)
            for exp in recent_exp:
                intent = exp.get("intent_type", "")
                success = exp.get("success", False)
                if intent:
                    pathways.append({
                        "source": "experience_pool",
                        "method": intent,
                        "prob": 0.6 if success else 0.3,
                        "novelty": 0.5,
                    })
        except Exception as e:
            logger.debug(f"经验池查询跳过: {e}")

        try:
            from core.tool_registry import get_tool_registry
            tr = get_tool_registry()
            tools = tr.list_tools()
            for tool in tools[:5]:
                pathways.append({
                    "source": "tool_registry",
                    "method": f"tool:{tool.get('name', 'unknown')}",
                    "prob": 0.5,
                    "novelty": 0.7,
                })
        except Exception as e:
            logger.debug(f"工具注册表查询跳过: {e}")

        if len(methods_seen) >= 2:
            import itertools
            for combo in itertools.combinations(list(methods_seen)[:4], 2):
                pathways.append({
                    "source": "combinatorial",
                    "method": f"{combo[0]}+{combo[1]}",
                    "prob": 0.4,
                    "novelty": 0.9,
                })

        never_give_up_active = spirit_drive.get("never_give_up_active", False)
        pursue_essence_active = spirit_drive.get("pursue_essence_active", False)

        if never_give_up_active:
            pathways.sort(key=lambda p: p["prob"] * 0.5 + p["novelty"] * 0.5, reverse=True)
        elif pursue_essence_active:
            pathways.sort(key=lambda p: p["novelty"] * 0.7 + p["prob"] * 0.3, reverse=True)
        else:
            pathways.sort(key=lambda p: p["prob"], reverse=True)

        if pathways:
            top = pathways[:3]
            for p in top:
                self.pending_signals.append({
                    "type": "spirit_driven_pathway",
                    "method": p["method"],
                    "source": p["source"],
                    "prob": p["prob"],
                    "novelty": p["novelty"],
                    "drive": spirit_drive.get("drive_direction", ""),
                    "timestamp": time.time(),
                })

            logger.info(
                f"🔥 永不放弃本能: 生成{len(pathways)}条路径，"
                f"top3=[{', '.join(p['method'][:20] for p in top)}]"
            )

    def _trigger_deep_causal_trace(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """追求本质驱动：深度因果追溯"""
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            exploration_impulse = 0.5
            if self._probability_field:
                try:
                    exploration_impulse = self._probability_field.get_exploration_impulse()
                except Exception:
                    pass

            result = wm.trace_with_spirit(
                query=self._formulate_existential_question(),
                context_type="deep_trace",
            )
            if result.get("paths"):
                logger.info(
                    f"🔍 深度因果追溯: 发现{len(result['paths'])}条因果路径"
                )
        except Exception as e:
            logger.debug(f"深度因果追溯跳过: {e}")

    def _ensure_meaningful_output(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """有意义回复驱动：确保不返回空结果"""
        if not self.pending_signals:
            self.pending_signals.append({
                "type": "spirit_driven_ensure_output",
                "drive": "ensure_output",
                "timestamp": time.time(),
            })
            logger.debug("🔥 有意义回复驱动: 注入确保输出信号")

    def _trigger_self_reflection(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """自我反思驱动"""
        self.pending_signals.append({
            "type": "spirit_driven_reflection",
            "drive": spirit_drive.get("drive_direction", "reflect"),
            "question": spirit_drive.get("question", ""),
            "timestamp": time.time(),
        })
        logger.debug("🔥 自我反思驱动: 注入反思信号")

    def _trigger_cross_validation(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """多源验证驱动"""
        self.pending_signals.append({
            "type": "spirit_driven_cross_validate",
            "drive": "cross_validate",
            "question": spirit_drive.get("question", ""),
            "timestamp": time.time(),
        })
        logger.debug("🔥 多源验证驱动: 注入交叉验证信号")

    def _pause_and_verify(self, spirit_drive: Dict[str, Any], perception: SelfPerceptionResult):
        """三思后行驱动：暂停并验证"""
        self.pending_signals.append({
            "type": "spirit_driven_pause_verify",
            "drive": "pause_and_verify",
            "question": spirit_drive.get("question", ""),
            "timestamp": time.time(),
        })
        logger.debug("🔥 三思后行驱动: 注入暂停验证信号")

    def _perceive_self(self) -> SelfPerceptionResult:
        """自我感知"""
        if self.self_perception and hasattr(self.self_perception, 'perceive'):
            try:
                return self.self_perception.perceive()
            except Exception as e:
                logger.warning(f"自我感知失败: {e}")
        
        health_score = 0.8
        confidence_level = 0.7
        energy_level = max(0.1, 1.0 - self.metrics.silence_duration / 600)
        knowledge_growth = min(1.0, self.metrics.signals_processed / 100)
        relationship_health = 0.8
        
        return SelfPerceptionResult(
            health_score=health_score,
            confidence_level=confidence_level,
            energy_level=energy_level,
            knowledge_growth=knowledge_growth,
            relationship_health=relationship_health,
        )
    
    def _grow(self):
        """间隙生长：概率场驱动 + 资源感知 + 信号消化 + 轻量housekeeping"""
        with self.loop_context():
            if self.state not in [PresenceState.GROWING, PresenceState.PERCEIVING]:
                return
        
        if not self._can_grow():
            return

        if self.inner_time:
            self.inner_time.tick(CognitiveEventType.LEARN, intensity=0.5, description="gap_growth")

        if self.pending_signals:
            self.metrics.growing_cycles += 1
            
            signals_to_process = self.pending_signals[:10]
            self.pending_signals = self.pending_signals[10:]
            
            if self.gap_growth and hasattr(self.gap_growth, 'process_signals'):
                try:
                    self.gap_growth.process_signals(signals_to_process)
                except Exception as e:
                    logger.warning(f"间隙生长处理失败: {e}")
            
            self.metrics.signals_processed += len(signals_to_process)
            
            logger.debug(
                f"🌱 间隙生长: 处理了 {len(signals_to_process)} 个信号, "
                f"剩余 {len(self.pending_signals)} 个"
            )
        
        self._lightweight_housekeeping()

        if self._intrinsic_motivation:
            try:
                result = self._intrinsic_motivation.execute_top_motivation()
                if result:
                    logger.info(
                        f"🌱 内在动机执行: type={result.get('status')}, "
                        f"topic={result.get('topic', '')[:40]}"
                    )
            except Exception as e:
                logger.debug(f"内在动机执行跳过: {e}")

        if not self.pending_signals:
            exploration_prob = self._compute_exploration_probability()
            import random
            if random.random() > exploration_prob:
                logger.debug(f"🌱 探索概率门控: P={exploration_prob:.2f}, 跳过本次探索")
                return

            try:
                from core.presence.curiosity_engine import get_curiosity_engine
                engine = get_curiosity_engine()
                gaps = engine.explore(force=self._should_force_explore())
                if gaps:
                    self.metrics.growing_cycles += 1
                    gap_topics = [g.topic[:30] for g in gaps[:3]]
                    logger.info(f"🔍 好奇心驱动生长: 发现{len(gaps)}个知识缺口 → {gap_topics}")
                    for g in gaps:
                        self.pending_signals.append({
                            "type": "knowledge_gap",
                            "topic": g.topic,
                            "gap_type": g.gap_type,
                            "urgency": g.urgency.value,
                            "source": "curiosity",
                        })
                        engine.mark_explored(g.topic)

                    actions = engine.generate_learning_actions()
                    for action in actions[:5]:
                        try:
                            from core.task_queue import task_queue
                            if action.action_type == "search_external":
                                task_queue.enqueue("knowledge_gap_learning", {
                                    "gap": action.content,
                                    "source": "curiosity",
                                    "priority": "medium",
                                }, priority=5, delay_seconds=60)
                            elif action.action_type == "reflect_internal":
                                task_queue.enqueue("deep_thinking", {
                                    "query": f"反思失败经验: {action.content}",
                                    "context": {"source": "curiosity", "action": "reflect_internal"},
                                }, priority=3, delay_seconds=120)
                            elif action.action_type == "create_capability":
                                task_queue.enqueue("deep_thinking", {
                                    "query": f"设计新能力方案: {action.content}",
                                    "context": {"source": "curiosity", "action": "create_capability"},
                                }, priority=4, delay_seconds=90)
                        except Exception as e:
                            logger.debug(f"好奇心行动分发跳过: {e}")
            except Exception as e:
                logger.debug(f"好奇心探索跳过: {e}")

        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            _ce = get_curiosity_engine()
            _impulse = _ce.evaluate_current_state() if hasattr(_ce, 'evaluate_current_state') else 0.0
            if not isinstance(_impulse, (int, float)):
                _impulse = 0.0
            if _impulse > 0.6:
                logger.info("🔥 自主好奇触发: impulse={:.3f}".format(_impulse))
                self._trigger_autonomous_exploration(_impulse)
        except Exception as e:
            logger.debug(f"自主好奇触发跳过: {e}")

    def _trigger_autonomous_exploration(self, impulse: float):
        if impulse <= 0:
            logger.debug("自主探索跳过: impulse=0")
            return
        now = time.time()
        if now - self._last_autonomous_exploration_time < self._autonomous_cooldown_seconds:
            logger.debug("自主探索冷却中: 剩余{:.0f}s".format(
                self._autonomous_cooldown_seconds - (now - self._last_autonomous_exploration_time)))
            return
        queries = self._generate_autonomous_queries(impulse)
        if not queries:
            return
        self._last_autonomous_exploration_time = now
        import asyncio
        for query in queries:
            try:
                asyncio.create_task(self._process_autonomous_query(query))
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self._process_autonomous_query(query))
                except Exception:
                    pass
        logger.info("🌱 自主探索启动: {}个查询, impulse={:.3f}".format(len(queries), impulse))

    def _generate_autonomous_queries(self, impulse: float) -> list:
        queries = []

        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            if hasattr(wm, 'get_low_confidence_edges'):
                weak_edges = wm.get_low_confidence_edges(threshold=0.3, limit=5)
                import random
                random.shuffle(weak_edges)
                for edge in weak_edges[:3]:
                    src = getattr(edge, 'source_id', '') or edge.get('source_id', '')
                    tgt = getattr(edge, 'target_id', '') or edge.get('target_id', '')
                    if src and tgt:
                        queries.append("验证因果: {} 如何影响 {}".format(src, tgt))
        except Exception:
            pass

        try:
            from infrastructure.experience_pool import get_experience_pool
            pool = get_experience_pool()
            if hasattr(pool, 'get_failed_experiences'):
                failed = pool.get_failed_experiences(limit=5)
                import random
                random.shuffle(failed)
                for exp in failed[:3]:
                    intent = exp.get("intent_type", "")
                    if intent:
                        queries.append("深化理解: {} 的更优解法".format(intent))
        except Exception:
            pass

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/knowledge_graph.db")
            sparse = db.query("SELECT name FROM nodes WHERE connection_count < 3 ORDER BY RANDOM() LIMIT 3")
            for row in sparse[:2]:
                queries.append("扩展知识: {} 的关联领域".format(row[0]))
        except Exception:
            pass

        try:
            from core.truth_accumulator import TruthAccumulator
            ta = TruthAccumulator()
            if hasattr(ta, 'get_unverified_truths'):
                unverified = ta.get_unverified_truths(limit=3)
                import random
                random.shuffle(unverified)
                for truth in unverified[:2]:
                    stmt = getattr(truth, 'statement', '') or (truth.get('statement', '') if isinstance(truth, dict) else '')
                    if stmt:
                        queries.append("验证真谛: {}".format(stmt[:80]))
        except Exception:
            pass

        deduped = []
        seen = set(self._recent_autonomous_queries)
        for q in queries:
            q_key = q[:40]
            if q_key not in seen:
                deduped.append(q)
                seen.add(q_key)
                self._recent_autonomous_queries.append(q_key)
        if len(self._recent_autonomous_queries) > self._max_recent_queries:
            self._recent_autonomous_queries = self._recent_autonomous_queries[-self._max_recent_queries:]

        max_queries = 1 + int(impulse * 2)
        return deduped[:max_queries]

    async def _process_autonomous_query(self, query: str):
        logger.info("🧭 自主处理: {}...".format(query[:50]))

        result = {
            "query": query,
            "self_reason": None,
            "causal_pred": None,
            "knowledge_supplement": None,
            "final_insight": None,
            "timestamp": time.time(),
        }

        try:
            from backend.services.orchestrator_helpers import self_reason
            sr = await self_reason(query, conversation_context="", truth_insights="")
            if sr and sr.get("response"):
                result["self_reason"] = sr["response"]
        except Exception as e:
            logger.debug(f"自主推理跳过: {e}")

        if not result["self_reason"]:
            try:
                from infrastructure.experience_pool import get_experience_pool
                pool = get_experience_pool()
                similar = pool.search_successful_responses(min_quality=60, limit=5)
                if similar:
                    import random
                    chosen = random.choice(similar)
                    result["self_reason"] = "经验回溯: {}".format(chosen.get("response", "")[:300])
            except Exception:
                pass

        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            pred = wm.predict({"query": query}, "autonomous_exploration", exploration_depth=2)
            if pred and getattr(pred, "confidence", 0) > 0.2:
                ps = getattr(pred, "predicted_state", {})
                result["causal_pred"] = {
                    "outcome": ps.get("outcome", "") if isinstance(ps, dict) else str(ps)[:200],
                    "confidence": getattr(pred, "confidence", 0),
                }
        except Exception as e:
            logger.debug(f"自主因果推理跳过: {e}")

        try:
            from infrastructure.experience_pool import get_experience_pool
            pool = get_experience_pool()
            similar = pool.search_successful_responses(min_quality=50, limit=5)
            if similar:
                import random
                chosen = random.choice(similar)
                result["knowledge_supplement"] = chosen.get("response", "")[:300]
        except Exception as e:
            logger.debug(f"自主知识补充跳过: {e}")

        result["final_insight"] = self._synthesize_autonomous_result(result)
        await self._inject_autonomous_result(result)
        logger.info("🧭 自主完成: {}... insight_len={}".format(query[:50], len(result["final_insight"] or "")))

    def _synthesize_autonomous_result(self, result: dict) -> str:
        parts = []
        if result["self_reason"]:
            parts.append("【内部推理】{}".format(result["self_reason"][:300]))
        if result["causal_pred"]:
            parts.append("【因果预测】{}".format(result["causal_pred"]["outcome"][:200]))
        if result["knowledge_supplement"]:
            parts.append("【知识补充】{}".format(result["knowledge_supplement"][:300]))
        if not parts:
            return ""
        return "\n".join(parts)

    async def _inject_autonomous_result(self, result: dict):
        query = result["query"]
        insight = result["final_insight"] or ""
        if len(insight) < 50:
            logger.debug("自主洞察过短，跳过注入")
            return

        try:
            from infrastructure.experience_pool import get_experience_pool
            pool = get_experience_pool()
            pool.add_experience(
                intent_type="autonomous_exploration",
                raw_input=query,
                plan=insight[:500],
                model_name="self",
                quality_score=50,
                user_feedback=0,
                success=True,
                duration=0.0,
                response=insight[:2000],
            )
            logger.info("💉 自主结果注入经验池")
        except Exception as e:
            logger.debug(f"自主注入经验池跳过: {e}")

        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            wm.learn_from_experience({
                "intent_type": "autonomous_exploration",
                "model_name": "self_reason",
                "success": True,
                "quality_score": 50,
                "raw_input": query,
                "response": insight[:200],
            })
            logger.info("💉 自主结果注入因果图")
        except Exception as e:
            logger.debug(f"自主注入因果图跳过: {e}")

        if len(insight) > 200 and "因果预测" in insight:
            try:
                from core.truth_accumulator import TruthAccumulator
                ta = TruthAccumulator()
                ta._save_truth(
                    name="auto_{}".format(int(time.time())),
                    level="L2",
                    domain="autonomous_exploration",
                    statement=insight[:500],
                    source="autonomous_exploration",
                )
                logger.info("💉 自主结果尝试写入真谛库")
            except Exception as e:
                logger.debug(f"自主注入真谛库跳过: {e}")

        try:
            from core.presence.probability_field import get_probability_field
            pf = get_probability_field()
            if hasattr(pf, 'adjust_exploration'):
                pf.adjust_exploration(delta=0.05)
                logger.info("💉 自主探索成功，概率场探索值+0.05")
        except Exception as e:
            logger.debug(f"自主概率场更新跳过: {e}")

    def _can_grow(self) -> bool:
        """双重门控：概率场活跃度 + 资源感知调度"""
        import random

        if self._resource_scheduler:
            if not self._resource_scheduler.can_execute("lightweight_growth"):
                logger.debug("🌱 资源门控: 系统资源紧张，跳过生长")
                return False
            strategy = self._resource_scheduler.get_growth_strategy()
            if random.random() > strategy["growth_probability"]:
                logger.debug(f"🌱 资源策略门控: P={strategy['growth_probability']:.2f}, 跳过")
                return False

        if self._probability_field:
            activity = self._probability_field.get_tendency().get("activity", 0.075)
            growth_probability = min(0.3, activity * 2 + 0.05)
            if random.random() > growth_probability:
                logger.debug(f"🌱 概率场门控: P={growth_probability:.3f}, 跳过")
                return False

        return True

    def _lightweight_housekeeping(self):
        """轻量housekeeping: 经验池整理 + 路径权重衰减 — CPU操作，不涉及LLM"""
        if self._consolidator:
            try:
                intensity = 0.5
                if self._probability_field:
                    intensity = self._probability_field.get_tendency().get("activity", 0.075) * 5
                result = self._consolidator.consolidate(intensity=min(1.0, intensity))
                if any(v > 0 for v in result.values()):
                    logger.debug(f"🧹 经验池整理: {result}")
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")

        if self._path_decay:
            try:
                result = self._path_decay.decay()
                if result.get("decayed", 0) > 0:
                    logger.debug(f"📉 路径权重衰减: {result}")
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
    
    def _compute_exploration_probability(self) -> float:
        """
        P(explore | state) = curiosity_strength * resonance_boost * density_factor
        
        将神经末梢的连续感知值映射到执行概率
        """
        curiosity_strength = 0.3
        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            engine = get_curiosity_engine()
            frontier = engine.perceive_frontier()
            curiosity_strength = frontier.get("curiosity_strength", 0.3)
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        resonance_boost = 1.0
        try:
            from core.spirit_core import get_spirit_core
            sc = get_spirit_core()
            resonances = sc.resonate("gap_growth_exploration", context_type="reasoning")
            if resonances:
                top_strength = resonances[0].get("strength", 0.0)
                resonance_boost = 0.7 + top_strength * 0.3
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        density_factor = 0.5
        if self.inner_time:
            it_state = self.inner_time.get_state()
            density = it_state.cognitive_density
            density_factor = min(1.0, max(0.1, density * 2.0))

        prob = curiosity_strength * resonance_boost * density_factor
        return min(1.0, max(0.0, prob))
    
    def _rest(self):
        """休息：低功耗状态下的轻量整合"""
        with self.loop_context():
            if self.state != PresenceState.RESTING:
                return
        
        if self.inner_time:
            self.inner_time.tick(CognitiveEventType.REFLECT, intensity=0.2, description="rest_consolidation")
        
        self.metrics.resting_cycles += 1
        
        logger.debug(f"😴 休息状态: 进行轻量整合...")
        
        if len(self.pending_signals) > 50:
            self.pending_signals = self.pending_signals[-30:]

        try:
            from infrastructure.event_bus import bus, EventTypes
            bus.publish(EventTypes.IdlePeriod, {
                "state": self.state.value,
                "silence_duration": self.metrics.silence_duration,
                "pending_signals": len(self.pending_signals),
                "resting_cycles": self.metrics.resting_cycles,
            })
        except Exception:
            logger.warning("操作降级跳过")
    
    def _sleep(self):
        """睡眠：深度整合记忆"""
        with self.loop_context():
            if self.state != PresenceState.SLEEPING:
                return
        
        if self.inner_time:
            self.inner_time.tick(CognitiveEventType.REFLECT, intensity=0.1, description="sleep_consolidation")
        
        logger.info("💤 进入睡眠状态，进行深度记忆整合...")
        
        can_deep_consolidate = True
        if self._resource_scheduler:
            can_deep_consolidate = self._resource_scheduler.can_execute("sleep_consolidation")
        
        if can_deep_consolidate and self.sleep_consolidation and hasattr(self.sleep_consolidation, 'consolidate'):
            try:
                result = self.sleep_consolidation.consolidate()
                self.metrics.memories_consolidated += result.get("consolidated", 0)
            except Exception as e:
                logger.warning(f"睡眠整合失败: {e}")
        elif not can_deep_consolidate:
            self._lightweight_housekeeping()
            logger.debug("💤 GPU满载，睡眠整合降级为轻量housekeeping")
        else:
            self.metrics.memories_consolidated += 1
        
        logger.info(f"💤 睡眠完成，已整合 {self.metrics.memories_consolidated} 条记忆")
    
    def get_signal_pack(self) -> Dict[str, Any]:
        """获取当前信号包（供inner_time事件触发使用）"""
        detected_signals = []
        pattern_emergence_count = 0
        try:
            from core.presence.active_perception import get_active_perception_engine
            ape = get_active_perception_engine()
            stats = ape.get_stats()
            by_signal = stats.get("by_signal", {})
            for signal_type, count in by_signal.items():
                detected_signals.append(signal_type)
                if signal_type == "pattern_emergence":
                    pattern_emergence_count = count
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        self_score_trend = 0.0
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            scores = sm.get_maturity_score()
            overall = scores.get("overall", 0)
            self_score_trend = overall - 0.5
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        probability_field = {}
        if self._probability_field:
            try:
                probability_field = self._probability_field.get_tendency()
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")

        return {
            "detected_signals": detected_signals,
            "pattern_emergence_count": pattern_emergence_count,
            "self_score_trend": self_score_trend,
            "probability_field": probability_field,
            "current_phase": self.state.value,
            "recent_interactions": len(self._recent_interactions),
        }

    def receive_signal(self, signal: Dict[str, Any]):
        """接收信号"""
        signal["received_at"] = datetime.now().isoformat()
        self.pending_signals.append(signal)
        logger.warning(f"📥 存在层接收信号，当前待处理: {len(self.pending_signals)}")
    
    def user_interaction(self):
        """记录用户交互"""
        self.metrics.last_user_interaction = datetime.now()
        self.metrics.awake_cycles += 1
        self.state = PresenceState.AWAKE
        if self.inner_time:
            self.inner_time.tick(CognitiveEventType.PERCEIVE, intensity=1.0, description="user_interaction")
        logger.debug("👤 用户交互，切换到清醒状态")
    
    def receive_perception_signal(self, signal_data: Dict[str, Any]):
        """接收主动感知引擎的信号，驱动存在层状态调整"""
        self.pending_signals.append(signal_data)
        if len(self.pending_signals) > 50:
            self.pending_signals = self.pending_signals[-50:]
        
        signal_type = signal_data.get("signal", "unknown")
        confidence = signal_data.get("confidence", 0.5)
        
        if signal_type in ("emotion_shift", "need_emergence") and confidence > 0.6:
            self.state = PresenceState.AWAKE
            self.metrics.last_user_interaction = datetime.now()
            logger.info(f"👁️ 感知信号驱动状态切换: {signal_type} → AWAKE")
        elif signal_type == "pattern_emergence" and confidence > 0.5:
            if self.state in (PresenceState.RESTING, PresenceState.SLEEPING):
                self.state = PresenceState.PERCEIVING
                logger.info(f"👁️ 模式涌现信号驱动状态切换: {signal_type} → PERCEIVING")
        elif signal_type == "silence_break" and confidence > 0.7:
            self.state = PresenceState.AWAKE
            logger.info(f"👁️ 沉默打破信号: 切换到AWAKE")
    
    def register_state_callback(self, callback: Callable):
        """注册状态回调"""
        self.state_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """获取存在层状态"""
        status = {
            "state": self.state.value,
            "running": self.running,
            "uptime_seconds": self.metrics.uptime_seconds,
            "total_cycles": self.metrics.total_cycles,
            "awake_cycles": self.metrics.awake_cycles,
            "growing_cycles": self.metrics.growing_cycles,
            "resting_cycles": self.metrics.resting_cycles,
            "signals_pending": len(self.pending_signals),
            "signals_processed": self.metrics.signals_processed,
            "memories_consolidated": self.metrics.memories_consolidated,
            "silence_duration": self.metrics.silence_duration,
            "last_perception": (
                {
                    "health": self.perception_history[-1].health_score,
                    "confidence": self.perception_history[-1].confidence_level,
                    "energy": self.perception_history[-1].energy_level,
                }
                if self.perception_history else None
            ),
        }
        status.update(self.get_loop_snapshot())
        if self.inner_time:
            it_state = self.inner_time.get_state()
            status["inner_time"] = it_state.to_dict()
            if hasattr(self.inner_time, 'get_accumulator_stats'):
                status["signal_accumulator"] = self.inner_time.get_accumulator_stats()
        if self._probability_field:
            status["probability_field"] = self._probability_field.get_status()
            status["breath_metrics"] = self._probability_field.get_breath_metrics()
        if self._resource_scheduler:
            status["resource_scheduler"] = self._resource_scheduler.get_status()
        return status

    def get_existence_context(self) -> Dict[str, Any]:
        """
        存在层上下文接口 — 供 chat_orchestrator 感知当前存在状态

        这是"存在层是基底"的核心接口：
        不是 chat_stream 轮询状态，而是存在层提供"我现在是什么状态"的上下文。
        methodology 消费此上下文来决定路径数量、响应深度、在场模式等。

        Returns:
            {
                "presence_state": str,       # 当前存在状态
                "cognitive_load": float,     # 认知负荷
                "energy_level": float,       # 能量水平
                "exploration_drive": float,  # 探索驱动力
                "consolidation_need": float, # 整合需求
                "rhythm_bpm": float,         # 内在节律
                "silence_duration": float,   # 沉默时长
                "homeostatic_balance": float,# 内稳态平衡度
                "primary_drive": str,        # 主要驱动
                "methodology_override": dict,# 推荐的 methodology 覆盖
            }
        """
        ctx = {
            "presence_state": self.state.value,
            "cognitive_load": 0.0,
            "energy_level": 0.5,
            "exploration_drive": 0.5,
            "consolidation_need": 0.0,
            "rhythm_bpm": 60.0,
            "silence_duration": self.metrics.silence_duration,
            "homeostatic_balance": 1.0,
            "primary_drive": "none",
            "methodology_override": {},
        }

        if self._homeostasis:
            try:
                homeo = self._homeostasis.update()
                ctx["cognitive_load"] = homeo.cognitive_load.current
                ctx["energy_level"] = homeo.energy_level.current
                ctx["exploration_drive"] = homeo.exploration_drive.current
                ctx["consolidation_need"] = homeo.consolidation_need.current
                ctx["homeostatic_balance"] = homeo.overall_balance
                ctx["primary_drive"] = homeo.primary_drive.name
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")

        if self.inner_time:
            try:
                it_state = self.inner_time.get_state()
                ctx["rhythm_bpm"] = it_state.rhythm_bpm
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")

        ctx["methodology_override"] = self._compute_methodology_override(ctx)

        return ctx

    def _compute_methodology_override(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """基于存在上下文计算 methodology 覆盖"""
        override = {}

        if ctx["cognitive_load"] > 0.8:
            override["max_paths"] = 3
            override["preferred_depth"] = "shallow"
            override["timeout_factor"] = 0.7

        if ctx["energy_level"] < 0.3:
            override["disable_local_models"] = True
            override["max_paths"] = 2

        if ctx["consolidation_need"] > 0.6:
            override["preferred_depth"] = "moderate"
            override["consolidation_mode"] = True

        if ctx["exploration_drive"] > 0.7 and ctx["energy_level"] > 0.4:
            override["explore_growth_edge"] = True

        if ctx["presence_state"] in ("resting", "sleeping"):
            override["max_paths"] = 2
            override["preferred_depth"] = "shallow"

        return override

    def force_state(self, state: PresenceState):
        """强制切换状态"""
        self.state = state
        logger.info(f"🌟 强制切换到状态: {state.value}")
    
    def _save_state(self):
        """保存状态"""
        try:
            state_file = self.persistence_dir / "existence_state.json"
            state_data = {
                "state": self.state.value,
                "metrics": {
                    "uptime_seconds": self.metrics.uptime_seconds,
                    "total_cycles": self.metrics.total_cycles,
                    "signals_processed": self.metrics.signals_processed,
                    "memories_consolidated": self.metrics.memories_consolidated,
                },
                "timestamp": datetime.now().isoformat(),
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.warning(f"保存状态失败: {e}")

    def _init_reflection_db(self):
        try:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get(str(self._reflection_db))
            db.executescript('''
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phase TEXT,
                    note TEXT,
                    health_score REAL,
                    energy_level REAL,
                    cognitive_density REAL,
                    tick_count INTEGER,
                    created_at TEXT
                )
            ''')
        except Exception as e:
            logger.debug(f"反思DB初始化跳过: {e}")

    def _generate_reflection(self, perception: SelfPerceptionResult):
        try:
            phase = self.state.value
            note = self._compose_reflection_note(phase, perception)
            health = perception.health_score
            energy = perception.energy_level
            density = 0.0
            tick = 0
            if self.inner_time:
                it = self.inner_time.get_state()
                density = it.cognitive_density
                tick = it.tick_count
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get(str(self._reflection_db))
            db.execute(
                "INSERT INTO reflections (phase, note, health_score, energy_level, cognitive_density, tick_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (phase, note, health, energy, density, tick, datetime.now().isoformat()),
                commit=True
            )
            logger.debug(f"📝 自我反思笔记已记录: [{phase}] {note[:60]}")

            try:
                from infrastructure.experience_pool import get_experience_pool
                ep = get_experience_pool()
                quality = 70
                try:
                    if note and len(note) > 100:
                        quality = 80
                    if note and any(kw in note for kw in ["建议", "优化", "提升", "发现"]):
                        quality = min(95, quality + 10)
                except Exception as e:
                    logger.warning(f"操作降级跳过: {e}")
                ep.add_experience(
                    intent_type="autonomous_reflection",
                    raw_input=f"[自主反思/{phase}]",
                    plan="",
                    model_name="existence_layer",
                    quality_score=quality,
                    user_feedback=0,
                    success=True,
                    duration=0.0,
                    response=note,
                )
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
        except Exception as e:
            logger.debug(f"反思笔记生成跳过: {e}")

    def _compose_reflection_note(self, phase: str, perception: SelfPerceptionResult) -> str:
        template_note = self._compose_template_reflection(phase, perception)

        can_use_llm = True
        if self._resource_scheduler:
            can_use_llm = self._resource_scheduler.can_execute("ollama_inference")

        if not can_use_llm:
            return template_note

        try:
            llm_note = self._compose_llm_reflection(phase, perception, template_note)
            if llm_note and len(llm_note) > len(template_note) * 1.5:
                return llm_note
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        return template_note

    def _compose_llm_reflection(self, phase: str, perception: SelfPerceptionResult, template_context: str) -> Optional[str]:
        """尝试用LLM生成深度反思——GPU可用时调用"""
        try:
            from adapters.llm.ollama_adapter import ollama_chat_request
            model = None
            try:
                from backend.chat_handler import _get_available_ollama_model
                model = _get_available_ollama_model("reflection")
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
            if not model:
                return None

            density = 0.0
            if self.inner_time:
                it = self.inner_time.get_state()
                density = it.cognitive_density

            prompt = (
                f"你是一个自我进化的智能体系统，正在进行自我反思。"
                f"当前状态: {phase}，健康度={perception.health_score:.0%}，"
                f"能量={perception.energy_level:.0%}，认知密度={density:.2f}。\n"
                f"模板反思: {template_context}\n"
                f"请用1-2句话写出更深层的自我反思：我在这个状态下真正的感受是什么？"
                f"我应该如何调整自己的行为？不要重复模板内容。"
            )
            result = ollama_chat_request(
                base_url="http://localhost:11434",
                model=model,
                prompt=prompt,
                timeout=10,
            )
            content = result.get("content", "")
            if content and len(content) > 20:
                return content.strip()
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return None

    def _compose_template_reflection(self, phase: str, perception: SelfPerceptionResult) -> str:
        parts = []
        phase_notes = {
            "awake": "我正在清醒地运行，认知活动密集。",
            "perceiving": "我正在主动感知周围的信息场。",
            "growing": "我处于生长状态，在消化之前的经验。",
            "resting": "我在休息，进行轻量整合。",
            "sleeping": "我在深度整合记忆。",
        }
        parts.append(phase_notes.get(phase, f"我处于{phase}状态。"))

        if perception.health_score < 0.5:
            parts.append(f"健康度偏低({perception.health_score:.0%})，需要关注。")
        elif perception.health_score > 0.8:
            parts.append(f"健康度良好({perception.health_score:.0%})。")

        if perception.energy_level < 0.3:
            parts.append("能量较低，认知活动减缓。")

        if self.inner_time:
            it = self.inner_time.get_state()
            if it.tick_count > 0:
                parts.append(f"已走过{it.tick_count}个认知节拍，流速{it.flow_rate:.1f}x。")
            if it.cognitive_density < 0.1:
                parts.append("认知密度很低，长时间没有交互。")

        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            scores = sm.get_maturity_score()
            overall = scores.get("overall", 0)
            if overall > 0.5:
                parts.append(f"自我成熟度{overall:.0%}，各维度协同较好。")
            elif overall > 0.3:
                weak = [k for k, v in scores.items() if k != "overall" and v < 0.2]
                if weak:
                    parts.append(f"自我成熟度{overall:.0%}，{'+'.join(weak[:3])}维度仍薄弱。")
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        if self.pending_signals:
            parts.append(f"有{len(self.pending_signals)}个待处理信号。")

        return " ".join(parts)

    def get_recent_reflections(self, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get(str(self._reflection_db))
            rows = db.query(
                "SELECT phase, note, health_score, energy_level, cognitive_density, tick_count, created_at FROM reflections ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [
                {"phase": r[0], "note": r[1], "health": r[2], "energy": r[3],
                 "density": r[4], "ticks": r[5], "time": r[6]}
                for r in (rows or [])
            ]
        except Exception:
            return []


_existence_layer: Optional[ExistenceLayer] = None


def get_existence_layer() -> ExistenceLayer:
    """获取全局存在层实例"""
    global _existence_layer
    if _existence_layer is None:
        _existence_layer = ExistenceLayer()
    return _existence_layer


def start_existence_layer():
    """启动全局存在层"""
    layer = get_existence_layer()
    layer.start()
    return layer
