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


class ExistenceLayer:
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
        self.heartbeat_interval = heartbeat_interval
        self.growth_interval = growth_interval
        self.rest_interval = rest_interval
        self.sleep_interval = sleep_interval
        
        self.state = PresenceState.AWAKE
        self.metrics = PresenceMetrics()
        self.metrics.last_user_interaction = datetime.now()
        
        self._init_components()
        
        self.running = False
        self._main_thread: Optional[threading.Thread] = None
        
        self.pending_signals: List[Dict[str, Any]] = []
        self.perception_history: List[SelfPerceptionResult] = []
        
        self.state_callbacks: List[Callable] = []
        
        self.persistence_dir = Path("data/existence")
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
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
                
                if now - last_heartbeat >= self.heartbeat_interval:
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
        """更新存在状态"""
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
        self.metrics.total_cycles += 1
        
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
        if self.state not in [PresenceState.GROWING, PresenceState.PERCEIVING]:
            return
        
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
        if self.state != PresenceState.RESTING:
            return
        
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
        if self.state != PresenceState.SLEEPING:
            return
        
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
        return {
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
