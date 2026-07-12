"""
低功耗模式管理器 (Low Power Mode Manager)

实现系统的节能策略，让系统在几十瓦功耗下持续运行
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
import threading
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PowerLevel(Enum):
    FULL = "full"              # 全功率：所有功能活跃
    NORMAL = "normal"          # 正常：核心功能活跃
    REDUCED = "reduced"        # 降低：仅必要功能
    MINIMAL = "minimal"        # 最小：仅存在层运行
    DEEP_SLEEP = "deep_sleep"  # 深度睡眠：仅心跳


@dataclass
class PowerMetrics:
    """功耗指标"""
    current_level: PowerLevel = PowerLevel.NORMAL
    target_watts: float = 50.0
    current_watts: float = 0.0
    idle_time_seconds: float = 0.0
    last_activity: datetime = None
    power_savings_percent: float = 0.0
    mode_changes: int = 0


@dataclass
class PowerProfile:
    """功耗配置"""
    name: str
    max_watts: float
    active_layers: list
    active_mechanisms: list
    cycle_interval: float
    description: str


POWER_PROFILES = {
    PowerLevel.FULL: PowerProfile(
        name="全功率",
        max_watts=100.0,
        active_layers=["l2", "l3", "l4", "l5", "l6", "existence"],
        active_mechanisms=["all"],
        cycle_interval=0.1,
        description="所有功能全速运行"
    ),
    PowerLevel.NORMAL: PowerProfile(
        name="正常",
        max_watts=50.0,
        active_layers=["l2", "l3", "l4", "existence"],
        active_mechanisms=["incremental_perception", "feedback_loop", "knowledge_weaver"],
        cycle_interval=0.5,
        description="核心功能正常运行"
    ),
    PowerLevel.REDUCED: PowerProfile(
        name="降低",
        max_watts=30.0,
        active_layers=["l2", "existence"],
        active_mechanisms=["incremental_perception"],
        cycle_interval=2.0,
        description="仅必要功能运行"
    ),
    PowerLevel.MINIMAL: PowerProfile(
        name="最小",
        max_watts=15.0,
        active_layers=["existence"],
        active_mechanisms=[],
        cycle_interval=5.0,
        description="仅存在层运行"
    ),
    PowerLevel.DEEP_SLEEP: PowerProfile(
        name="深度睡眠",
        max_watts=5.0,
        active_layers=[],
        active_mechanisms=[],
        cycle_interval=30.0,
        description="仅心跳维持"
    ),
}


class LowPowerManager:
    """
    低功耗模式管理器
    
    职责：
    1. 根据活动水平自动调整功耗
    2. 管理各功耗等级的资源配置
    3. 平滑切换功耗模式
    4. 监控实际功耗
    """
    
    def __init__(
        self,
        target_watts: float = 50.0,
        idle_threshold_seconds: float = 300.0,
        deep_idle_threshold: float = 1800.0,
    ):
        self.target_watts = target_watts
        self.idle_threshold = idle_threshold_seconds
        self.deep_idle_threshold = deep_idle_threshold
        
        self.metrics = PowerMetrics()
        self.metrics.last_activity = datetime.now()
        
        self.current_profile = POWER_PROFILES[PowerLevel.NORMAL]
        self.orchestrator = None
        
        self.running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        self.activity_callbacks = []
        
        logger.info(f"🔋 低功耗管理器已初始化 (目标: {target_watts}W)")
    
    def set_orchestrator(self, orchestrator):
        """设置编排器引用"""
        self.orchestrator = orchestrator
    
    def start(self):
        """启动功耗监控"""
        if self.running:
            return
        
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    self._monitor_tick()
                    time.sleep(5.0)
                except Exception as e:
                    logger.error(f"功耗监控错误: {e}")
        
        self._monitor_thread = threading.Thread(
            target=monitor_loop,
            daemon=True,
            name="PowerMonitor"
        )
        self._monitor_thread.start()
        
        logger.info("✓ 功耗监控已启动")
    
    def stop(self):
        """停止功耗监控"""
        self.running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("✓ 功耗监控已停止")
    
    def _monitor_tick(self):
        """监控循环的单次执行"""
        now = datetime.now()
        idle_time = (now - self.metrics.last_activity).total_seconds()
        self.metrics.idle_time_seconds = idle_time
        
        if idle_time > self.deep_idle_threshold:
            self._set_power_level(PowerLevel.DEEP_SLEEP)
        elif idle_time > self.idle_threshold * 3:
            self._set_power_level(PowerLevel.MINIMAL)
        elif idle_time > self.idle_threshold * 2:
            self._set_power_level(PowerLevel.REDUCED)
        elif idle_time > self.idle_threshold:
            self._set_power_level(PowerLevel.NORMAL)
        
        self._estimate_power_usage()
    
    def _set_power_level(self, level: PowerLevel):
        """设置功耗等级"""
        if self.metrics.current_level == level:
            return
        
        old_level = self.metrics.current_level
        self.metrics.current_level = level
        self.current_profile = POWER_PROFILES[level]
        self.metrics.mode_changes += 1
        
        logger.info(f"🔋 功耗模式切换: {old_level.value} → {level.value} ({self.current_profile.description})")
        
        if self.orchestrator:
            self._apply_power_profile()
    
    def _apply_power_profile(self):
        """应用功耗配置"""
        if not self.orchestrator:
            return
        
        profile = self.current_profile
        
        for layer_name, status in self.orchestrator.layer_status.items():
            should_be_active = layer_name in profile.active_layers
            
            if should_be_active and not status.active:
                try:
                    layer = self.orchestrator.layers.get(layer_name)
                    if layer and hasattr(layer, 'activate'):
                        layer.activate()
                    status.active = True
                except Exception as e:
                    logger.warning(f"激活层 {layer_name} 失败: {e}")
            
            elif not should_be_active and status.active:
                try:
                    layer = self.orchestrator.layers.get(layer_name)
                    if layer and hasattr(layer, 'deactivate'):
                        layer.deactivate()
                    status.active = False
                except Exception as e:
                    logger.warning(f"停用层 {layer_name} 失败: {e}")
        
        for mech_name, mechanism in self.orchestrator.mechanisms.items():
            should_be_active = (
                "all" in profile.active_mechanisms or
                mech_name in profile.active_mechanisms
            )
            
            if hasattr(mechanism, 'set_active'):
                try:
                    mechanism.set_active(should_be_active)
                except Exception:
                    pass
    
    def _estimate_power_usage(self):
        """估算当前功耗"""
        base_watts = 5.0
        
        active_layers = len([s for s in self.orchestrator.layer_status.values() if s.active]) if self.orchestrator else 0
        layer_watts = active_layers * 8.0
        
        active_mechanisms = 0
        if self.orchestrator:
            for mech_name, mech in self.orchestrator.mechanisms.items():
                if hasattr(mech, 'is_active') and mech.is_active:
                    active_mechanisms += 1
        mech_watts = active_mechanisms * 3.0
        
        self.metrics.current_watts = base_watts + layer_watts + mech_watts
        
        if self.metrics.current_watts > 0:
            self.metrics.power_savings_percent = (
                1.0 - self.metrics.current_watts / POWER_PROFILES[PowerLevel.FULL].max_watts
            ) * 100
    
    def record_activity(self, activity_type: str = "general"):
        """记录活动（重置空闲计时器）"""
        self.metrics.last_activity = datetime.now()
        self.metrics.idle_time_seconds = 0.0
        
        if self.metrics.current_level != PowerLevel.FULL:
            self._set_power_level(PowerLevel.NORMAL)
        
        for callback in self.activity_callbacks:
            try:
                callback(activity_type)
            except Exception:
                pass
    
    def force_power_level(self, level: PowerLevel):
        """强制设置功耗等级"""
        self._set_power_level(level)
        self.metrics.last_activity = datetime.now()
    
    def get_power_status(self) -> Dict[str, Any]:
        """获取功耗状态"""
        return {
            "current_level": self.metrics.current_level.value,
            "current_watts": self.metrics.current_watts,
            "target_watts": self.target_watts,
            "power_savings_percent": self.metrics.power_savings_percent,
            "idle_time_seconds": self.metrics.idle_time_seconds,
            "mode_changes": self.metrics.mode_changes,
            "profile": {
                "name": self.current_profile.name,
                "max_watts": self.current_profile.max_watts,
                "active_layers": self.current_profile.active_layers,
                "cycle_interval": self.current_profile.cycle_interval,
            },
        }
    
    def suggest_optimization(self) -> Dict[str, Any]:
        """建议功耗优化"""
        suggestions = []
        
        if self.metrics.current_watts > self.target_watts * 1.2:
            suggestions.append({
                "type": "reduce_power",
                "reason": f"当前功耗 {self.metrics.current_watts:.1f}W 超过目标 {self.target_watts:.1f}W",
                "action": "考虑进入降低功耗模式",
            })
        
        if self.metrics.idle_time_seconds > self.idle_threshold and self.metrics.current_level == PowerLevel.NORMAL:
            suggestions.append({
                "type": "enter_idle",
                "reason": f"已空闲 {self.metrics.idle_time_seconds:.0f} 秒",
                "action": "可进入低功耗模式以节省能源",
            })
        
        if self.orchestrator:
            active_count = len([s for s in self.orchestrator.layer_status.values() if s.active])
            if active_count > 4 and self.metrics.current_level != PowerLevel.FULL:
                suggestions.append({
                    "type": "too_many_layers",
                    "reason": f"{active_count} 个层同时活跃",
                    "action": "考虑停用非必要层",
                })
        
        return {
            "suggestions": suggestions,
            "current_efficiency": self.metrics.power_savings_percent,
        }


low_power_manager = LowPowerManager()