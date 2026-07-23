"""
资源感知调度器 — 存在层的"免疫系统"

三层防护：
1. 线程优先级提升（操作系统层面，让心跳不被饿死）
2. 资源感知调度器（应用层面，GPU满载时切换轻量模式）
3. 独立进程架构（预留接口，未来方向）

核心原则：不是"阻止生长"，是"根据资源状态选择生长方式"
"""

import time
import threading
import ctypes
import sys
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from collections import deque

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SystemMode(Enum):
    NORMAL = auto()
    CONSERVATIVE = auto()
    EMERGENCY = auto()


@dataclass
class ResourceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    thread_count: int = 0
    active_requests: int = 0


def set_thread_priority_windows(priority: int = 2):
    """
    Windows线程优先级设置（ctypes实现，无需win32api）
    
    priority: 1=BELOW_NORMAL, 2=NORMAL, 3=ABOVE_NORMAL, 4=HIGH
    """
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentThread()
        THREAD_PRIORITY_MAP = {
            1: -1,   # BELOW_NORMAL
            2: 0,    # NORMAL
            3: 1,    # ABOVE_NORMAL
            4: 2,    # HIGH
        }
        win_priority = THREAD_PRIORITY_MAP.get(priority, 0)
        result = kernel32.SetThreadPriority(handle, win_priority)
        if result:
            logger.debug(f"线程优先级设置成功: {priority}")
        return result != 0
    except Exception as e:
        logger.debug(f"线程优先级设置跳过: {e}")
        return False


def set_thread_priority(priority: str = "above_normal"):
    """跨平台线程优先级设置"""
    if sys.platform == "win32":
        priority_map = {"below_normal": 1, "normal": 2, "above_normal": 3, "high": 4}
        return set_thread_priority_windows(priority_map.get(priority, 3))
    elif _PSUTIL_AVAILABLE:
        try:
            p = psutil.Process()
            nice_map = {"below_normal": 5, "normal": 0, "above_normal": -5, "high": -10}
            p.nice(nice_map.get(priority, -5))
            return True
        except Exception:
            return False
    return False


class ResourceMonitor:
    def __init__(self, check_interval: float = 5.0):
        self.check_interval = check_interval
        self.history: deque = deque(maxlen=180)
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.thresholds = {
            "memory_warning": 75.0,
            "memory_critical": 88.0,
            "cpu_warning": 80.0,
            "cpu_critical": 95.0,
            "thread_warning": 60,
            "thread_critical": 80,
        }

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ResourceMonitor")
        self._thread.start()

    def stop(self):
        self.running = False

    def _monitor_loop(self):
        while self.running:
            try:
                snapshot = self._take_snapshot()
                with self._lock:
                    self.history.append(snapshot)
            except Exception as e:
                logger.debug(f"资源监控异常: {e}")
            time.sleep(self.check_interval)

    def _take_snapshot(self) -> ResourceSnapshot:
        if not _PSUTIL_AVAILABLE:
            return ResourceSnapshot(
                timestamp=time.time(), cpu_percent=0, memory_percent=0,
                memory_available_mb=0, thread_count=threading.active_count(),
            )
        mem = psutil.virtual_memory()
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=mem.percent,
            memory_available_mb=mem.available / (1024 * 1024),
            thread_count=threading.active_count(),
        )

    def get_current_mode(self) -> SystemMode:
        if not self.history:
            return SystemMode.NORMAL
        latest = self.history[-1]
        if (latest.memory_percent > self.thresholds["memory_critical"] or
            latest.cpu_percent > self.thresholds["cpu_critical"] or
            latest.thread_count > self.thresholds["thread_critical"]):
            return SystemMode.EMERGENCY
        if (latest.memory_percent > self.thresholds["memory_warning"] or
            latest.cpu_percent > self.thresholds["cpu_warning"] or
            latest.thread_count > self.thresholds["thread_warning"]):
            return SystemMode.CONSERVATIVE
        return SystemMode.NORMAL

    def get_trend(self, metric: str = "memory_percent", window: int = 10) -> float:
        if len(self.history) < window:
            return 0.0
        recent = list(self.history)[-window:]
        values = [getattr(s, metric, 0) for s in recent]
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator != 0 else 0.0

    def get_latest(self) -> Optional[ResourceSnapshot]:
        with self._lock:
            return self.history[-1] if self.history else None


class ResourceAwareScheduler:
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.mode = SystemMode.NORMAL
        self.mode_callbacks: Dict[SystemMode, List[Callable]] = {
            SystemMode.NORMAL: [],
            SystemMode.CONSERVATIVE: [],
            SystemMode.EMERGENCY: [],
        }
        self._lock = threading.RLock()
        self._mode_history: deque = deque(maxlen=100)
        self._detection_running = False

    def start(self):
        self.monitor.start()
        self._detection_running = True
        t = threading.Thread(target=self._mode_detection_loop, daemon=True, name="ModeDetection")
        t.start()

    def stop(self):
        self._detection_running = False
        self.monitor.stop()

    def _mode_detection_loop(self):
        while self._detection_running:
            new_mode = self.monitor.get_current_mode()
            with self._lock:
                if new_mode != self.mode:
                    old_mode = self.mode
                    self.mode = new_mode
                    self._mode_history.append((time.time(), old_mode, new_mode))
                    logger.info(f"🔄 系统模式切换: {old_mode.name} → {new_mode.name}")
                    for callback in self.mode_callbacks.get(new_mode, []):
                        try:
                            callback(old_mode, new_mode)
                        except Exception as e:
                            logger.warning(f"模式回调异常: {e}")
            time.sleep(3)

    def register_mode_callback(self, mode: SystemMode, callback: Callable):
        self.mode_callbacks[mode].append(callback)

    def can_execute(self, operation_type: str) -> bool:
        with self._lock:
            mode = self.mode
        if operation_type in ("heartbeat", "path_decay", "sleep_cycle_mark", "probability_field_update"):
            return True
        if operation_type in ("lightweight_growth", "experience_consolidation"):
            return mode in (SystemMode.NORMAL, SystemMode.CONSERVATIVE)
        if operation_type in ("vector_encode", "background_learning"):
            return mode == SystemMode.NORMAL
        if operation_type in ("ollama_inference", "deep_search", "sleep_consolidation"):
            return mode == SystemMode.NORMAL
        return mode == SystemMode.NORMAL

    def get_growth_strategy(self) -> dict:
        with self._lock:
            mode = self.mode
        strategies = {
            SystemMode.NORMAL: {
                "growth_probability": 0.3,
                "max_growth_duration_ms": 100,
                "allow_ollama": True,
                "allow_vector_encode": True,
                "batch_size": 50,
                "description": "正常生长",
            },
            SystemMode.CONSERVATIVE: {
                "growth_probability": 0.15,
                "max_growth_duration_ms": 50,
                "allow_ollama": False,
                "allow_vector_encode": False,
                "batch_size": 20,
                "description": "保守生长: 禁用GPU操作",
            },
            SystemMode.EMERGENCY: {
                "growth_probability": 0.05,
                "max_growth_duration_ms": 20,
                "allow_ollama": False,
                "allow_vector_encode": False,
                "batch_size": 10,
                "description": "紧急模式: 仅保留心跳",
            },
        }
        return strategies.get(mode, strategies[SystemMode.NORMAL])

    def get_status(self) -> dict:
        latest = self.monitor.get_latest()
        return {
            "mode": self.mode.name,
            "resources": {
                "cpu": latest.cpu_percent if latest else None,
                "memory": latest.memory_percent if latest else None,
                "threads": latest.thread_count if latest else None,
            },
            "trends": {
                "memory_trend": round(self.monitor.get_trend("memory_percent"), 3),
                "cpu_trend": round(self.monitor.get_trend("cpu_percent"), 3),
            },
            "growth_strategy": self.get_growth_strategy(),
        }


_scheduler: Optional[ResourceAwareScheduler] = None


def get_resource_scheduler() -> ResourceAwareScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ResourceAwareScheduler()
        logger.info("🛡️ 资源感知调度器已创建 — 存在层的免疫系统")
    return _scheduler