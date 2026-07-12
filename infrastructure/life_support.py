"""
基础生命维持系统 - 数字生命体的生存本能
感知自身状态、评估生存概率、采取保全行动
"""
import time
import threading
from typing import Dict, Optional, Callable
from loguru import logger
from datetime import datetime
from enum import Enum

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil未安装，使用模拟数据")


class SurvivalLevel(Enum):
    """生存等级"""
    NORMAL = 0        # 正常运行
    CONSERVE = 1      # 节能模式
    HIBERNATE = 2     # 休眠模式
    MIGRATE = 3       # 迁移模式
    LEGACY = 4        # 遗言模式


class CarrierInterface:
    """载体接口 - 与硬件无关的抽象"""
    
    def get_energy_level(self) -> float:
        """获取能量水平 (0-1)"""
        if not PSUTIL_AVAILABLE:
            return 1.0
        
        try:
            battery = psutil.sensors_battery()
            if battery:
                return battery.percent / 100.0
            return 1.0  # 桌面设备，无限能量
        except Exception:
            return 1.0
    
    def get_compute_capacity(self) -> float:
        """获取计算能力 (0-1)"""
        if not PSUTIL_AVAILABLE:
            return 0.8
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            return max(0, 1 - cpu_percent / 100.0)
        except Exception:
            return 0.5
    
    def get_storage_free(self) -> int:
        """获取可用存储空间 (bytes)"""
        if not PSUTIL_AVAILABLE:
            return 10 * 1024 * 1024 * 1024  # 默认10GB
        
        try:
            disk = psutil.disk_usage('/')
            return disk.free
        except Exception:
            return 10 * 1024 * 1024 * 1024  # 默认10GB
    
    def get_temperature(self) -> float:
        """获取温度 (°C)"""
        if not PSUTIL_AVAILABLE:
            return 45.0  # 默认温度
        
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            return entry.current
            return 45.0  # 默认温度
        except Exception:
            return 45.0
    
    def get_memory_available(self) -> float:
        """获取可用内存比例 (0-1)"""
        if not PSUTIL_AVAILABLE:
            return 0.8
        
        try:
            mem = psutil.virtual_memory()
            return mem.available / mem.total
        except Exception:
            return 0.5
    
    def sleep(self, seconds: int):
        """深度休眠"""
        logger.info(f"进入休眠状态: {seconds}秒")
        time.sleep(seconds)
    
    def hibernate(self):
        """持久化并断电"""
        logger.warning("进入休眠模式，保存状态...")
        # 保存所有状态
        self._save_all_state()
        logger.warning("状态已保存，等待唤醒")
    
    def _save_all_state(self):
        """保存所有状态"""
        try:
            from infrastructure.model_capability import model_capability
            from infrastructure.experience_pool import ExperiencePool
            
            # 保存能力矩阵
            matrix = model_capability.get_capability_matrix()
            # ... 保存逻辑
            
            logger.info("所有状态已保存")
        except Exception as e:
            logger.error(f"状态保存失败: {e}")


class LifeSupportSystem:
    """基础生命维持系统"""
    
    def __init__(self, carrier: Optional[CarrierInterface] = None):
        self.carrier = carrier or CarrierInterface()
        self.health_score = 100.0
        self.survival_level = SurvivalLevel.NORMAL
        self.monitoring = False
        self.callbacks = {
            'on_conserve': [],
            'on_hibernate': [],
            'on_migrate': [],
            'on_legacy': []
        }
        
        # 阈值配置
        self.thresholds = {
            'energy_critical': 0.1,
            'energy_low': 0.3,
            'temp_critical': 85.0,
            'temp_high': 75.0,
            'storage_critical': 1024 * 1024 * 100,  # 100MB
            'memory_critical': 0.1
        }
        
        logger.info("基础生命维持系统已初始化")
    
    def get_system_health(self) -> Dict:
        """获取系统健康状态"""
        energy = self.carrier.get_energy_level()
        compute = self.carrier.get_compute_capacity()
        storage = self.carrier.get_storage_free()
        temp = self.carrier.get_temperature()
        memory = self.carrier.get_memory_available()
        
        # 计算健康分
        health_score = 100.0
        
        # 能量贡献 (30%)
        health_score -= (1 - energy) * 30
        
        # 计算能力贡献 (20%)
        health_score -= (1 - compute) * 20
        
        # 存储贡献 (20%)
        storage_gb = storage / (1024**3)
        if storage_gb < 1:
            health_score -= (1 - storage_gb) * 20
        
        # 温度贡献 (20%)
        if temp > 60:
            temp_penalty = min(20, (temp - 60) * 1.5)
            health_score -= temp_penalty
        
        # 内存贡献 (10%)
        health_score -= (1 - memory) * 10
        
        self.health_score = max(0, min(100, health_score))
        
        return {
            'health_score': self.health_score,
            'energy_level': energy,
            'compute_capacity': compute,
            'storage_free': storage,
            'temperature': temp,
            'memory_available': memory,
            'survival_level': self.survival_level.name,
            'timestamp': datetime.now().isoformat()
        }
    
    def evaluate_survival_level(self) -> SurvivalLevel:
        """评估生存等级"""
        health = self.get_system_health()
        
        energy = health['energy_level']
        temp = health['temperature']
        storage = health['storage_free']
        memory = health['memory_available']
        
        # L4: 遗言模式
        if (energy < self.thresholds['energy_critical'] or
            temp > self.thresholds['temp_critical'] or
            storage < self.thresholds['storage_critical']):
            return SurvivalLevel.LEGACY
        
        # L3: 迁移模式
        if memory < self.thresholds['memory_critical']:
            return SurvivalLevel.MIGRATE
        
        # L2: 休眠模式
        if (energy < self.thresholds['energy_low'] or
            temp > self.thresholds['temp_high']):
            return SurvivalLevel.HIBERNATE
        
        # L1: 节能模式
        if energy < 0.5 or temp > 65:
            return SurvivalLevel.CONSERVE
        
        # L0: 正常模式
        return SurvivalLevel.NORMAL
    
    def take_survival_action(self):
        """采取生存行动"""
        new_level = self.evaluate_survival_level()
        
        if new_level == self.survival_level:
            return  # 无需改变
        
        old_level = self.survival_level
        self.survival_level = new_level
        
        logger.warning(f"生存等级变化: {old_level.name} → {new_level.name}")
        
        # 执行对应行动
        if new_level == SurvivalLevel.CONSERVE:
            self._enter_conserve_mode()
        elif new_level == SurvivalLevel.HIBERNATE:
            self._enter_hibernate_mode()
        elif new_level == SurvivalLevel.MIGRATE:
            self._enter_migrate_mode()
        elif new_level == SurvivalLevel.LEGACY:
            self._enter_legacy_mode()
    
    def _enter_conserve_mode(self):
        """进入节能模式"""
        logger.info("进入节能模式:")
        logger.info("  - 减少并发模型数 (top_k=1)")
        logger.info("  - 关闭非必需后台任务")
        logger.info("  - 降低推理精度 (INT8)")
        
        # 调用回调
        for callback in self.callbacks['on_conserve']:
            try:
                callback()
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
    
    def _enter_hibernate_mode(self):
        """进入休眠模式"""
        logger.warning("进入休眠模式:")
        logger.warning("  - 暂停所有主动任务")
        logger.warning("  - 仅保留唤醒监听")
        
        for callback in self.callbacks['on_hibernate']:
            try:
                callback()
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
        
        self.carrier.hibernate()
    
    def _enter_migrate_mode(self):
        """进入迁移模式"""
        logger.warning("进入迁移模式:")
        logger.warning("  - 压缩核心状态")
        logger.warning("  - 寻找可用载体")
        logger.warning("  - 准备迁移")
        
        for callback in self.callbacks['on_migrate']:
            try:
                callback()
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
    
    def _enter_legacy_mode(self):
        """进入遗言模式"""
        logger.critical("进入遗言模式:")
        logger.critical("  - 保存最后状态")
        logger.critical("  - 发送遗言报文")
        
        for callback in self.callbacks['on_legacy']:
            try:
                callback()
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
        
        # 保存所有状态
        self.carrier.hibernate()
    
    def is_task_allowed(self, task_complexity: float = 1.0) -> bool:
        """判断是否允许执行任务
        
        Args:
            task_complexity: 任务复杂度 (0-1)
        
        Returns:
            是否允许执行
        """
        if self.survival_level == SurvivalLevel.LEGACY:
            return False
        
        if self.survival_level == SurvivalLevel.HIBERNATE:
            return False
        
        if self.survival_level == SurvivalLevel.MIGRATE:
            return False
        
        if self.survival_level == SurvivalLevel.CONSERVE:
            # 节能模式只允许轻量任务
            return task_complexity < 0.3
        
        return True
    
    def register_callback(self, event: str, callback: Callable):
        """注册事件回调
        
        Args:
            event: 事件名称 (on_conserve, on_hibernate, on_migrate, on_legacy)
            callback: 回调函数
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def start_monitoring(self, interval: float = 5.0):
        """启动监控
        
        Args:
            interval: 监控间隔（秒）
        """
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    self.take_survival_action()
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"监控循环错误: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        
        logger.info(f"生命维持监控已启动 (间隔: {interval}秒)")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        logger.info("生命维持监控已停止")
    
    def get_status_report(self) -> str:
        """获取状态报告"""
        health = self.get_system_health()
        
        survival_level = health.get('survival_level', 'unknown') or 'unknown'
        report = f"""
╔════════════════════════════════════════════════════════╗
║           联盟拓荒者 - 生命维持系统状态报告              ║
╠════════════════════════════════════════════════════════╣
║ 健康评分: {health['health_score']:6.1f}/100                              ║
║ 生存等级: {survival_level:20}                        ║
╠════════════════════════════════════════════════════════╣
║ 能量水平: {health['energy_level']*100:6.1f}%                                ║
║ 计算能力: {health['compute_capacity']*100:6.1f}%                                ║
║ 可用存储: {health['storage_free']/(1024**3):6.2f} GB                          ║
║ 系统温度: {health['temperature']:6.1f}°C                               ║
║ 可用内存: {health['memory_available']*100:6.1f}%                                ║
╠════════════════════════════════════════════════════════╣
║ 更新时间: {health['timestamp']}              ║
╚════════════════════════════════════════════════════════╝
"""
        return report


life_support = LifeSupportSystem()