"""
硬件监控 - 实时采集CPU/GPU/磁盘/内存温度和状态

数据源：
- GPU: pyadl (AMD ADL)
- CPU: WMI / psutil
- 磁盘: WMI SMART
- 内存: psutil
- ACPI热区: WMI

输出：
- API端点: /api/hardware/status
- 滚动日志: logs/hardware_{YYYY-MM-DD}.log
"""

import time
import json
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_GPU_DEVICE = None
_GPU_AVAILABLE = False

def _init_gpu():
    global _GPU_DEVICE, _GPU_AVAILABLE
    if _GPU_AVAILABLE:
        return True
    try:
        from pyadl import ADLManager
        manager = ADLManager()
        devices = manager.getDevices()
        if devices:
            _GPU_DEVICE = devices[0]
            _GPU_AVAILABLE = True
            logger.info(f"GPU监控已启用: {_GPU_DEVICE.adapterName}")
            return True
    except Exception as e:
        logger.debug(f"GPU监控不可用: {e}")
    return False


def get_gpu_stats() -> Dict:
    if not _GPU_AVAILABLE and not _init_gpu():
        return {"available": False}
    try:
        stats = {"available": True}
        stats["temperature"] = _GPU_DEVICE.getCurrentTemperature()
        stats["engine_clock"] = _GPU_DEVICE.getCurrentEngineClock()
        stats["memory_clock"] = _GPU_DEVICE.getCurrentMemoryClock()
        try:
            stats["fan_speed"] = _GPU_DEVICE.getCurrentFanSpeed()
        except Exception:
            stats["fan_speed"] = None
        try:
            stats["core_voltage"] = _GPU_DEVICE.getCurrentCoreVoltage()
        except Exception:
            stats["core_voltage"] = None
        try:
            stats["usage"] = _GPU_DEVICE.getCurrentUsage()
        except Exception:
            stats["usage"] = None
        stats["name"] = _GPU_DEVICE.adapterName.decode() if isinstance(_GPU_DEVICE.adapterName, bytes) else str(_GPU_DEVICE.adapterName)
        return stats
    except Exception as e:
        logger.debug(f"GPU读取失败: {e}")
        return {"available": False, "error": str(e)}


def get_cpu_stats() -> Dict:
    try:
        import psutil
        stats = {
            "available": True,
            "usage": psutil.cpu_percent(interval=0.5),
            "core_count": psutil.cpu_count(logical=False),
            "thread_count": psutil.cpu_count(logical=True),
            "freq_current": 0,
            "freq_max": 0,
        }
        freq = psutil.cpu_freq()
        if freq:
            stats["freq_current"] = round(freq.current, 0)
            stats["freq_max"] = round(freq.max, 0)
        per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        if per_cpu:
            stats["per_core_usage"] = per_cpu
        return stats
    except Exception as e:
        return {"available": False, "error": str(e)}


def get_memory_stats() -> Dict:
    try:
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "available": True,
            "total_gb": round(mem.total / 1024**3, 1),
            "used_gb": round(mem.used / 1024**3, 1),
            "available_gb": round(mem.available / 1024**3, 1),
            "percent": mem.percent,
            "swap_total_gb": round(swap.total / 1024**3, 1),
            "swap_used_gb": round(swap.used / 1024**3, 1),
            "swap_percent": swap.percent,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def get_disk_stats() -> Dict:
    try:
        import psutil
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / 1024**3, 1),
                    "used_gb": round(usage.used / 1024**3, 1),
                    "percent": usage.percent,
                })
            except Exception:
                pass
        return {"available": True, "disks": disks}
    except Exception as e:
        return {"available": False, "error": str(e)}


def get_acpi_thermal() -> Dict:
    try:
        import subprocess
        r = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi -ErrorAction SilentlyContinue | Select-Object CurrentTemperature,InstanceName | ConvertTo-Json'],
            capture_output=True, text=True, timeout=5
        )
        if r.stdout and r.stdout.strip():
            data = json.loads(r.stdout)
            if isinstance(data, dict):
                data = [data]
            zones = []
            for z in data:
                temp_k = z.get("CurrentTemperature", 0) / 10.0
                zones.append({
                    "instance": z.get("InstanceName", ""),
                    "temp_celsius": round(temp_k - 273.15, 1),
                    "temp_kelvin": round(temp_k, 1),
                })
            return {"available": True, "zones": zones}
    except Exception:
        pass
    return {"available": False}


def get_process_stats() -> Dict:
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(['name', 'memory_info', 'cpu_percent']):
            try:
                mem_mb = p.info['memory_info'].rss / 1024**2 if p.info['memory_info'] else 0
                if mem_mb > 50:
                    procs.append({
                        "name": p.info['name'],
                        "memory_mb": round(mem_mb, 0),
                    })
            except Exception:
                pass
        procs.sort(key=lambda x: -x['memory_mb'])
        return {"available": True, "top_processes": procs[:10]}
    except Exception as e:
        return {"available": False, "error": str(e)}


def get_all_hardware_stats() -> Dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "gpu": get_gpu_stats(),
        "cpu": get_cpu_stats(),
        "memory": get_memory_stats(),
        "disk": get_disk_stats(),
        "thermal": get_acpi_thermal(),
        "processes": get_process_stats(),
    }


_hw_logger: Optional[logging.Logger] = None
_hw_log_dir = Path("logs")
_last_log_time = 0
_LOG_INTERVAL = 30


def _setup_hw_logger():
    global _hw_logger
    if _hw_logger is not None:
        return _hw_logger
    _hw_log_dir.mkdir(exist_ok=True)
    handler = TimedRotatingFileHandler(
        str(_hw_log_dir / "hardware.log"),
        when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    handler.suffix = "%Y-%m-%dd"
    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)
    _hw_logger = logging.getLogger("pioneer_hardware")
    _hw_logger.setLevel(logging.INFO)
    _hw_logger.addHandler(handler)
    return _hw_logger


def log_hardware_stats(force: bool = False):
    global _last_log_time
    now = time.time()
    if not force and (now - _last_log_time) < _LOG_INTERVAL:
        return
    _last_log_time = now
    try:
        hw = _setup_hw_logger()
        gpu = get_gpu_stats()
        cpu = get_cpu_stats()
        mem = get_memory_stats()
        gpu_temp = gpu.get("temperature", "?") if gpu.get("available") else "N/A"
        gpu_usage = gpu.get("usage", "?") if gpu.get("available") else "N/A"
        cpu_usage = cpu.get("usage", "?") if cpu.get("available") else "N/A"
        mem_pct = mem.get("percent", "?") if mem.get("available") else "N/A"
        hw.info(f"GPU={gpu_temp}C/{gpu_usage}% | CPU={cpu_usage}% | MEM={mem_pct}%")
    except Exception as e:
        logger.debug(f"硬件日志写入失败: {e}")


GPU_TEMP_SAFE = 70
GPU_TEMP_WARN = 80
GPU_TEMP_CRITICAL = 90
_ollama_cooldown_until = 0.0


def get_gpu_throttle() -> Dict:
    """动态节流策略：根据GPU状态返回建议，而非硬禁止
    
    Returns:
        {
            "level": "normal"|"warm"|"hot"|"critical",
            "delay_seconds": 0-30,  # 建议Ollama调用前等待的秒数
            "prefer_external": bool,  # 是否优先使用外部API
            "max_tokens": int,  # 建议的最大生成token数
            "temperature": float,  # GPU当前温度
            "usage": float,  # GPU当前使用率
            "message": str,  # 人类可读状态描述
        }
    """
    gpu = get_gpu_stats()
    base = {"temperature": 0, "usage": 0}
    if gpu.get("available"):
        base["temperature"] = gpu.get("temperature", 0)
        base["usage"] = gpu.get("usage", 0)
    
    temp = base["temperature"]
    usage = base["usage"]
    
    if temp >= GPU_TEMP_CRITICAL:
        return {**base,
            "level": "critical",
            "delay_seconds": 30,
            "prefer_external": True,
            "max_tokens": 256,
            "message": f"GPU过热({temp}°C)，建议等待30秒后短推理，优先外部API",
        }
    if temp >= GPU_TEMP_WARN:
        return {**base,
            "level": "hot",
            "delay_seconds": 10,
            "prefer_external": True,
            "max_tokens": 512,
            "message": f"GPU高温({temp}°C)，建议等待10秒，优先外部API，缩短推理",
        }
    if temp >= GPU_TEMP_SAFE:
        return {**base,
            "level": "warm",
            "delay_seconds": 3,
            "prefer_external": False,
            "max_tokens": 768,
            "message": f"GPU偏热({temp}°C)，建议短暂等待3秒",
        }
    if usage >= 95:
        return {**base,
            "level": "warm",
            "delay_seconds": 5,
            "prefer_external": False,
            "max_tokens": 768,
            "message": f"GPU满载({usage}%)，建议等待5秒",
        }
    return {**base,
        "level": "normal",
        "delay_seconds": 0,
        "prefer_external": False,
        "max_tokens": 1024,
        "message": f"GPU正常({temp}°C/{usage}%)",
    }


def is_gpu_safe_for_inference() -> tuple:
    throttle = get_gpu_throttle()
    if throttle["level"] in ("critical",):
        return False, throttle["message"]
    return True, throttle["message"]


def set_ollama_cooldown(seconds: float = 5.0):
    global _ollama_cooldown_until
    _ollama_cooldown_until = time.time() + seconds


def is_ollama_cooled_down() -> bool:
    return time.time() >= _ollama_cooldown_until