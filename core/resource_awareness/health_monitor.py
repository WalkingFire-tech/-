"""
系统健康监测器 - 持续感知资源状态

核心理念：感知优先于行动
- 系统在采取任何可能消耗大量资源的行动前，先评估当前资源状态
- 类似生物体的内稳态机制，持续监测并在资源紧张时主动调节
- 跨设备自适应：8GB笔记本和32GB台式机用不同的阈值

设计原则：
- 轻量级：检查本身不能成为资源负担
- 渐进式：从正常→保守→紧急，分级响应
- 可恢复：资源恢复后自动回到正常模式
- 跨设备：根据实际硬件动态调整阈值
"""

import threading
import time
import subprocess
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class OperatingMode(Enum):
    NORMAL = "normal"
    CONSERVATIVE = "conservative"
    EMERGENCY = "emergency"


@dataclass
class HardwareProfile:
    total_ram_gb: float = 0.0
    gpu_vendor: str = "none"
    gpu_vram_gb: float = 0.0
    cpu_cores: int = 4
    gpu_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ram_gb": round(self.total_ram_gb, 1),
            "gpu_vendor": self.gpu_vendor,
            "gpu_vram_gb": round(self.gpu_vram_gb, 1),
            "cpu_cores": self.cpu_cores,
            "gpu_name": self.gpu_name,
        }


@dataclass
class ResourceSnapshot:
    memory_usage: float = 0.0
    memory_available_gb: float = 0.0
    thread_count: int = 0
    cpu_percent: float = 0.0
    gpu_memory: float = 0.0
    gpu_vram_used_gb: float = 0.0
    gpu_vram_total_gb: float = 0.0
    ollama_active_requests: int = 0
    ollama_estimated_vram_gb: float = 0.0
    active_queries: int = 0
    mode: OperatingMode = OperatingMode.NORMAL
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_usage": round(self.memory_usage, 3),
            "memory_available_gb": round(self.memory_available_gb, 2),
            "thread_count": self.thread_count,
            "cpu_percent": round(self.cpu_percent, 1),
            "gpu_memory": round(self.gpu_memory, 3),
            "gpu_vram_used_gb": round(self.gpu_vram_used_gb, 2),
            "gpu_vram_total_gb": round(self.gpu_vram_total_gb, 2),
            "ollama_active_requests": self.ollama_active_requests,
            "ollama_estimated_vram_gb": round(self.ollama_estimated_vram_gb, 2),
            "active_queries": self.active_queries,
            "mode": self.mode.value,
            "timestamp": self.timestamp,
        }


def _detect_hardware() -> HardwareProfile:
    """检测硬件配置"""
    profile = HardwareProfile()

    try:
        import psutil
        profile.total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        profile.cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4
    except Exception:
        profile.total_ram_gb = 8.0
        profile.cpu_cores = 4

    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            if len(parts) >= 2:
                profile.gpu_vendor = "nvidia"
                profile.gpu_name = parts[0].strip()
                profile.gpu_vram_gb = float(parts[1].strip()) / 1024.0
                return profile
    except Exception:
        logger.warning("操作降级跳过")

    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | Format-List'],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0 and result.stdout.strip():
            name = ""
            vram = 0.0
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith("Name"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("AdapterRAM"):
                    try:
                        vram = int(line.split(":", 1)[1].strip()) / (1024 ** 3)
                    except ValueError:
                        pass
            if name:
                profile.gpu_name = name
                vram = _correct_vram(name, vram)
                profile.gpu_vram_gb = vram
                name_lower = name.lower()
                if "radeon" in name_lower or "amd" in name_lower:
                    profile.gpu_vendor = "amd"
                elif "nvidia" in name_lower or "geforce" in name_lower or "rtx" in name_lower or "gtx" in name_lower:
                    profile.gpu_vendor = "nvidia"
                else:
                    profile.gpu_vendor = "unknown"
    except Exception:
        logger.warning("操作降级跳过")

    return profile


OLLAMA_MODEL_VRAM = {
    "gemma": 4.0,
    "qwen": 5.0,
    "llama": 5.0,
    "mistral": 4.5,
    "deepseek": 5.0,
    "deepcoder": 5.0,
    "codellama": 4.5,
    "phi": 2.5,
    "default": 4.0,
}

KNOWN_GPU_VRAM = {
    "rx 580": 8.0,
    "rx 570": 8.0,
    "rx 5600 xt": 6.0,
    "rx 5700 xt": 8.0,
    "rx 6600": 8.0,
    "rx 6600 xt": 8.0,
    "rx 6700 xt": 12.0,
    "rx 6800": 16.0,
    "rx 6800 xt": 16.0,
    "rx 6900 xt": 16.0,
    "rx 7600": 8.0,
    "rx 7700 xt": 12.0,
    "rx 7800 xt": 16.0,
    "rx 7900 xtx": 24.0,
    "gtx 1060": 6.0,
    "gtx 1070": 8.0,
    "gtx 1080": 8.0,
    "gtx 1080 ti": 11.0,
    "gtx 1650": 4.0,
    "gtx 1660": 6.0,
    "rtx 2060": 6.0,
    "rtx 2070": 8.0,
    "rtx 2080": 8.0,
    "rtx 3060": 12.0,
    "rtx 3070": 8.0,
    "rtx 3080": 10.0,
    "rtx 3090": 24.0,
    "rtx 4060": 8.0,
    "rtx 4070": 12.0,
    "rtx 4080": 16.0,
    "rtx 4090": 24.0,
}


def _correct_vram(gpu_name: str, reported_vram: float) -> float:
    """修正WMI报告的VRAM（WMI常低估AMD显卡显存）"""
    name_lower = gpu_name.lower()
    for known_name, known_vram in KNOWN_GPU_VRAM.items():
        if known_name in name_lower:
            if reported_vram < known_vram * 0.8:
                logger.debug(f"VRAM修正: {gpu_name} WMI报告{reported_vram:.1f}GB→实际{known_vram:.1f}GB")
                return known_vram
            return max(reported_vram, known_vram)
    return reported_vram if reported_vram > 0 else 4.0


class SystemHealthMonitor:
    """
    系统健康监测器

    持续感知资源状态，为自适应调节提供决策依据。
    跨设备自适应：根据实际硬件动态调整阈值。
    """

    def __init__(self):
        self._snapshot = ResourceSnapshot()
        self._last_check_time: Optional[datetime] = None
        self._check_interval = 2.0
        self._oom_count = 0
        self._last_oom_time: Optional[datetime] = None
        self._mode_history: list = []
        self._max_history = 100
        self._lock = threading.Lock()

        self._ollama_active = 0
        self._ollama_lock = threading.Lock()
        self._ollama_loaded_models: Dict[str, float] = {}

        self._active_queries = 0
        self._query_lock = threading.Lock()

        self.hardware = _detect_hardware()
        logger.info(f"🖥️ 硬件检测: RAM={self.hardware.total_ram_gb:.1f}GB, "
                     f"GPU={self.hardware.gpu_name or '无'} "
                     f"({self.hardware.gpu_vram_gb:.1f}GB VRAM), "
                     f"CPU={self.hardware.cpu_cores}核")

        self.thresholds = self._compute_thresholds()

        self._trend_window = 10
        self._memory_trend: list = []

        logger.info(f"🫀 系统健康监测器已创建 (阈值: MEM warn={self.thresholds['memory_warn']:.0%} "
                     f"critical={self.thresholds['memory_critical']:.0%})")

    def _compute_thresholds(self) -> Dict[str, float]:
        """根据硬件配置动态计算阈值"""
        ram = self.hardware.total_ram_gb
        vram = self.hardware.gpu_vram_gb

        if ram >= 32:
            mem_warn = 0.80
            mem_critical = 0.90
            avail_min = 3.0
        elif ram >= 16:
            mem_warn = 0.75
            mem_critical = 0.88
            avail_min = 2.0
        elif ram >= 8:
            mem_warn = 0.70
            mem_critical = 0.85
            avail_min = 1.5
        else:
            mem_warn = 0.65
            mem_critical = 0.80
            avail_min = 1.0

        if vram > 0 and vram <= 4:
            gpu_warn = 0.70
            gpu_critical = 0.85
        elif vram > 4 and vram <= 8:
            gpu_warn = 0.75
            gpu_critical = 0.88
        else:
            gpu_warn = 0.80
            gpu_critical = 0.90

        return {
            "memory_warn": mem_warn,
            "memory_critical": mem_critical,
            "available_memory_min_gb": avail_min,
            "gpu_memory_warn": gpu_warn,
            "gpu_memory_critical": gpu_critical,
            "thread_warn": 60,
            "thread_critical": 80,
            "cpu_warn": 0.85,
            "cpu_critical": 0.95,
            "ollama_concurrent_warn": 2,
            "ollama_concurrent_critical": 4,
        }

    def check(self) -> ResourceSnapshot:
        """检查当前资源状态（带缓存，避免频繁调用psutil）"""
        with self._lock:
            now = datetime.now()
            if self._last_check_time:
                elapsed = (now - self._last_check_time).total_seconds()
                if elapsed < self._check_interval:
                    return self._snapshot

            self._last_check_time = now
            self._do_check()
            return self._snapshot

    def _do_check(self):
        """执行实际检查"""
        try:
            import psutil

            mem = psutil.virtual_memory()
            self._snapshot.memory_usage = mem.percent / 100.0
            self._snapshot.memory_available_gb = mem.available / (1024 ** 3)
            self._snapshot.cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
            self._snapshot.thread_count = threading.active_count()
        except ImportError:
            self._snapshot.memory_usage = 0.5
            self._snapshot.memory_available_gb = 4.0
            self._snapshot.cpu_percent = 0.5
            self._snapshot.thread_count = threading.active_count()

        gpu_usage, vram_used, vram_total = self._get_gpu_memory_usage()
        self._snapshot.gpu_memory = gpu_usage
        self._snapshot.gpu_vram_used_gb = vram_used
        self._snapshot.gpu_vram_total_gb = vram_total

        with self._ollama_lock:
            self._snapshot.ollama_active_requests = self._ollama_active
            self._snapshot.ollama_estimated_vram_gb = sum(self._ollama_loaded_models.values())

        with self._query_lock:
            self._snapshot.active_queries = self._active_queries

        self._snapshot.mode = self._compute_mode()
        self._snapshot.timestamp = datetime.now().isoformat()

        self._memory_trend.append(self._snapshot.memory_usage)
        if len(self._memory_trend) > self._trend_window:
            self._memory_trend = self._memory_trend[-self._trend_window:]

        self._mode_history.append({
            "mode": self._snapshot.mode.value,
            "memory": self._snapshot.memory_usage,
            "ts": self._snapshot.timestamp,
        })
        if len(self._mode_history) > self._max_history:
            self._mode_history = self._mode_history[-self._max_history:]

    def _compute_mode(self) -> OperatingMode:
        """根据资源状态计算运行模式"""
        mem = self._snapshot.memory_usage
        avail = self._snapshot.memory_available_gb
        threads = self._snapshot.thread_count
        cpu = self._snapshot.cpu_percent
        gpu = self._snapshot.gpu_memory

        gpu_temp = 0
        try:
            from infrastructure.hardware_monitor import get_gpu_stats
            gs = get_gpu_stats()
            if gs.get("available"):
                gpu_temp = gs.get("temperature", 0)
        except Exception:
            pass

        if (mem > self.thresholds["memory_critical"]
                or avail < self.thresholds["available_memory_min_gb"]
                or threads > self.thresholds["thread_critical"]
                or cpu > self.thresholds["cpu_critical"]
                or gpu > self.thresholds["gpu_memory_critical"]
                or gpu_temp >= 90):
            return OperatingMode.EMERGENCY

        if (mem > self.thresholds["memory_warn"]
                or threads > self.thresholds["thread_warn"]
                or cpu > self.thresholds["cpu_warn"]
                or gpu > self.thresholds["gpu_memory_warn"]
                or gpu_temp >= 80):
            return OperatingMode.CONSERVATIVE

        if self._is_memory_rising_fast():
            return OperatingMode.CONSERVATIVE

        if self._is_vram_tight():
            return OperatingMode.CONSERVATIVE

        return OperatingMode.NORMAL

    def _is_memory_rising_fast(self) -> bool:
        """检测内存是否快速上升"""
        if len(self._memory_trend) < 5:
            return False
        recent = self._memory_trend[-5:]
        delta = recent[-1] - recent[0]
        return delta > 0.1

    def _is_vram_tight(self) -> bool:
        """检测VRAM是否紧张（Ollama模型占用+当前使用接近上限）"""
        vram_total = self.hardware.gpu_vram_gb
        if vram_total <= 0:
            return False
        if self._ollama_active == 0 and self._snapshot.gpu_memory < 0.01:
            return False
        estimated_ollama = self._snapshot.ollama_estimated_vram_gb
        current_usage = self._snapshot.gpu_memory
        if current_usage > 0:
            estimated_used = vram_total * current_usage + estimated_ollama * 0.3
        else:
            estimated_used = estimated_ollama
        return estimated_used > vram_total * 0.7

    def _get_gpu_memory_usage(self) -> Tuple[float, float, float]:
        """
        获取GPU显存使用率

        Returns: (usage_ratio, used_gb, total_gb)
        支持NVIDIA(nvidia-smi)和AMD(WMI)两种检测方式
        """
        if self.hardware.gpu_vendor == "nvidia":
            return self._get_nvidia_gpu()
        elif self.hardware.gpu_vendor == "amd":
            return self._get_amd_gpu()
        return 0.0, 0.0, 0.0

    def _get_nvidia_gpu(self) -> Tuple[float, float, float]:
        """NVIDIA GPU显存检测"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].split(',')
                    if len(parts) == 2:
                        used_mb = float(parts[0].strip())
                        total_mb = float(parts[1].strip())
                        used_gb = used_mb / 1024.0
                        total_gb = total_mb / 1024.0
                        ratio = used_mb / total_mb if total_mb > 0 else 0.0
                        return ratio, used_gb, total_gb
        except Exception:
            logger.warning("操作降级跳过")
        return 0.0, 0.0, 0.0

    def _get_amd_gpu(self) -> Tuple[float, float, float]:
        """AMD GPU显存检测（通过WMI + Ollama估算）"""
        vram_total = self.hardware.gpu_vram_gb
        if vram_total <= 0:
            return 0.0, 0.0, 0.0

        estimated_ollama = 0.0
        with self._ollama_lock:
            estimated_ollama = sum(self._ollama_loaded_models.values())

        if self._ollama_active > 0 and estimated_ollama > 0:
            used_gb = min(vram_total, estimated_ollama)
            ratio = used_gb / vram_total
            return ratio, used_gb, vram_total

        return 0.0, 0.0, vram_total

    def register_ollama_model(self, model_name: str):
        """注册Ollama模型加载（估算VRAM消耗）"""
        vram_estimate = OLLAMA_MODEL_VRAM.get("default", 4.0)
        for key, val in OLLAMA_MODEL_VRAM.items():
            if key in model_name.lower():
                vram_estimate = val
                break
        with self._ollama_lock:
            self._ollama_loaded_models[model_name] = vram_estimate
        logger.debug(f"Ollama模型注册: {model_name} ~{vram_estimate:.1f}GB VRAM")

    def unregister_ollama_model(self, model_name: str):
        """注销Ollama模型"""
        with self._ollama_lock:
            self._ollama_loaded_models.pop(model_name, None)

    def get_operating_mode(self) -> OperatingMode:
        """获取当前运行模式"""
        snap = self.check()
        return snap.mode

    def get_mode_value(self) -> str:
        return self.get_operating_mode().value

    def is_normal(self) -> bool:
        return self.get_operating_mode() == OperatingMode.NORMAL

    def is_conservative(self) -> bool:
        return self.get_operating_mode() == OperatingMode.CONSERVATIVE

    def is_emergency(self) -> bool:
        return self.get_operating_mode() == OperatingMode.EMERGENCY

    def register_ollama_request(self):
        with self._ollama_lock:
            self._ollama_active += 1

    def unregister_ollama_request(self):
        with self._ollama_lock:
            self._ollama_active = max(0, self._ollama_active - 1)

    def register_query(self):
        with self._query_lock:
            self._active_queries += 1

    def unregister_query(self):
        with self._query_lock:
            self._active_queries = max(0, self._active_queries - 1)

    def record_oom(self):
        self._oom_count += 1
        self._last_oom_time = datetime.now()
        logger.warning(f"🔴 OOM事件记录 (累计{self._oom_count}次)")

    def get_max_parallel_paths(self) -> int:
        """根据当前模式返回最大并行路径数——动态降频，永不停工"""
        mode = self.get_operating_mode()
        if mode == OperatingMode.EMERGENCY:
            return 3
        if mode == OperatingMode.CONSERVATIVE:
            gpu_temp = 0
            try:
                from infrastructure.hardware_monitor import get_gpu_stats
                gs = get_gpu_stats()
                if gs.get("available"):
                    gpu_temp = gs.get("temperature", 0)
            except Exception:
                pass
            if gpu_temp >= 85:
                return 3
            return 5
        return 9

    def get_max_ollama_concurrent(self) -> int:
        mode = self.get_operating_mode()
        if mode == OperatingMode.EMERGENCY:
            return 0
        if mode == OperatingMode.CONSERVATIVE:
            return 1
        return 1

    def should_use_dense_retrieval(self) -> bool:
        """是否应该使用稠密检索（sentence_transformers）"""
        snap = self.check()
        if snap.memory_usage > self.thresholds["memory_warn"]:
            return False
        if self._is_vram_tight():
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """获取完整状态"""
        snap = self.check()
        return {
            "snapshot": snap.to_dict(),
            "hardware": self.hardware.to_dict(),
            "oom_count": self._oom_count,
            "last_oom": self._last_oom_time.isoformat() if self._last_oom_time else None,
            "memory_trend": self._memory_trend[-10:],
            "max_parallel_paths": self.get_max_parallel_paths(),
            "max_ollama_concurrent": self.get_max_ollama_concurrent(),
            "should_use_dense_retrieval": self.should_use_dense_retrieval(),
            "thresholds": self.thresholds,
            "ollama_loaded_models": dict(self._ollama_loaded_models),
        }


_health_monitor: Optional[SystemHealthMonitor] = None
_monitor_lock = threading.Lock()


def get_health_monitor() -> SystemHealthMonitor:
    """获取健康监测器单例"""
    global _health_monitor
    with _monitor_lock:
        if _health_monitor is None:
            _health_monitor = SystemHealthMonitor()
        return _health_monitor
