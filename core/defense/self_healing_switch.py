"""
L4 自修复层 - 自愈开关 (Self-Healing Switch)

类比：细胞凋亡 + 干细胞再生
- 检测到模块持续异常时，自动下线（凋亡）
- 冷却后自动重启并验证（干细胞再生）
- 重启失败则升级处理
"""
import time
from typing import Dict, List, Optional, Callable
from loguru import logger
from infrastructure.config_manager import config
from datetime import datetime


class SelfHealingSwitch:

    def __init__(self):
        self._apoptosis_threshold = config.get("defense.apoptosis_threshold", 10)
        self._regeneration_cooldown = config.get("defense.regeneration_cooldown_seconds", 120)
        self._max_regeneration_attempts = config.get("defense.max_regeneration_attempts", 3)
        self._modules: Dict[str, dict] = {}
        self._regeneration_registry: Dict[str, Callable] = {}
        self._healing_log: List[dict] = []

    def register(self, module_name: str, regenerator: Callable):
        self._regeneration_registry[module_name] = regenerator

    def check_health(self, module_name: str, failure_count: int, success_count: int) -> Optional[str]:
        total = failure_count + success_count
        if total == 0:
            return "healthy"
        error_rate = failure_count / total
        if failure_count >= self._apoptosis_threshold and error_rate > 0.7:
            return "apoptosis"
        if error_rate > 0.5 and total >= 5:
            return "degraded"
        return "healthy"

    def trigger_apoptosis(self, module_name: str, reason: str = ""):
        if module_name not in self._modules:
            self._modules[module_name] = {"status": "active", "regeneration_attempts": 0}
        self._modules[module_name]["status"] = "apoptosis"
        self._modules[module_name]["apoptosis_at"] = time.time()
        self._modules[module_name]["apoptosis_reason"] = reason
        entry = {
            "action": "apoptosis",
            "module": module_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self._healing_log.append(entry)
        logger.warning(f"💀 细胞凋亡: {module_name} ({reason})")

    def attempt_regeneration(self, module_name: str) -> bool:
        if module_name not in self._modules:
            return False
        info = self._modules[module_name]
        if info.get("status") != "apoptosis":
            return False
        if info.get("regeneration_attempts", 0) >= self._max_regeneration_attempts:
            logger.error(f"❌ {module_name}再生失败次数已达上限，需人工介入")
            info["status"] = "dead"
            return False
        elapsed = time.time() - info.get("apoptosis_at", 0)
        if elapsed < self._regeneration_cooldown:
            return False
        info["regeneration_attempts"] = info.get("regeneration_attempts", 0) + 1
        regenerator = self._regeneration_registry.get(module_name)
        if regenerator:
            try:
                regenerator()
                info["status"] = "regenerated"
                info["regeneration_attempts"] = 0
                entry = {
                    "action": "regeneration_success",
                    "module": module_name,
                    "timestamp": datetime.now().isoformat(),
                }
                self._healing_log.append(entry)
                logger.info(f"🌱 干细胞再生成功: {module_name}")
                return True
            except Exception as e:
                logger.error(f"❌ {module_name}再生失败: {e}")
                entry = {
                    "action": "regeneration_failed",
                    "module": module_name,
                    "error": str(e)[:200],
                    "timestamp": datetime.now().isoformat(),
                }
                self._healing_log.append(entry)
                return False
        else:
            logger.debug(f"⚠️ {module_name}无注册再生器，跳过自动再生")
            return False

    def get_module_status(self, module_name: str) -> str:
        if module_name in self._modules:
            return self._modules[module_name].get("status", "unknown")
        return "unregistered"

    def get_all_statuses(self) -> dict:
        return {name: info.get("status", "unknown") for name, info in self._modules.items()}

    def get_healing_log(self, limit: int = 20) -> List[dict]:
        return self._healing_log[-limit:]


self_healing_switch = SelfHealingSwitch()