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
    
    def start(self):
        """启动存在层"""
        if self.running:
            logger.warning("存在层已在运行")
            return
        
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
        """更新存在状态 — 优先使用内在节律，回退到wall-clock"""
        if self.inner_time:
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
    
    def _heartbeat(self):
        """心跳：持续感知自身状态"""
        with self.loop_context():
            self.metrics.total_cycles += 1
            
            if self.inner_time:
                self.inner_time.tick(CognitiveEventType.PERCEIVE, intensity=0.3, description="heartbeat")
            
            perception = self._perceive_self()
            self.perception_history.append(perception)
            
            if len(self.perception_history) > 100:
                self.perception_history = self.perception_history[-50:]
            
            logger.debug(
                f"💓 心跳 #{self.metrics.total_cycles} | "
                f"状态: {self.state.value} | "
                f"健康: {perception.health_score:.2f} | "
                f"能量: {perception.energy_level:.2f}"
            )
            
            for callback in self.state_callbacks:
                try:
                    callback(perception)
                except Exception as e:
                    logger.warning(f"状态回调错误: {e}")
            
            if self.metrics.total_cycles % self._reflection_interval == 0:
                self._generate_reflection(perception)

            if self.pending_signals and self.state not in [PresenceState.GROWING, PresenceState.PERCEIVING]:
                signals_to_process = self.pending_signals[:3]
                self.pending_signals = self.pending_signals[3:]
                self.metrics.signals_processed += len(signals_to_process)
                if self.gap_growth and hasattr(self.gap_growth, 'process_signals'):
                    try:
                        self.gap_growth.process_signals(signals_to_process)
                    except Exception:
                        pass
    
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
        """间隙生长：消化未处理的信号 + 好奇心驱动的主动探索"""
        with self.loop_context():
            if self.state not in [PresenceState.GROWING, PresenceState.PERCEIVING]:
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
        
        if not self.pending_signals:
            try:
                from core.presence.curiosity_engine import get_curiosity_engine
                engine = get_curiosity_engine()
                gaps = engine.explore()
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
    
    def _rest(self):
        """休息：低功耗状态下的轻量整合"""
        with self.loop_context():
            if self.state != PresenceState.RESTING:
                return
        
        if self.inner_time:
            self.inner_time.tick(CognitiveEventType.REFLECT, intensity=0.2, description="rest_consolidation")
        
        self.metrics.resting_cycles += 1
        
        logger.warning(f"😴 休息状态: 进行轻量整合...")
        
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
        
        if self.sleep_consolidation and hasattr(self.sleep_consolidation, 'consolidate'):
            try:
                result = self.sleep_consolidation.consolidate()
                self.metrics.memories_consolidated += result.get("consolidated", 0)
            except Exception as e:
                logger.warning(f"睡眠整合失败: {e}")
        else:
            self.metrics.memories_consolidated += 1
        
        logger.info(f"💤 睡眠完成，已整合 {self.metrics.memories_consolidated} 条记忆")
    
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
        return status
    
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
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(str(self._reflection_db), timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")
            conn.executescript('''
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
            conn.close()
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
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(str(self._reflection_db), timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")
            conn.execute(
                "INSERT INTO reflections (phase, note, health_score, energy_level, cognitive_density, tick_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (phase, note, health, energy, density, tick, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
            logger.debug(f"📝 自我反思笔记已记录: [{phase}] {note[:60]}")
        except Exception as e:
            logger.debug(f"反思笔记生成跳过: {e}")

    def _compose_reflection_note(self, phase: str, perception: SelfPerceptionResult) -> str:
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
        except Exception:
            pass

        if self.pending_signals:
            parts.append(f"有{len(self.pending_signals)}个待处理信号。")

        return " ".join(parts)

    def get_recent_reflections(self, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(str(self._reflection_db), timeout=15.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.execute(
                "SELECT phase, note, health_score, energy_level, cognitive_density, tick_count, created_at FROM reflections ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
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
