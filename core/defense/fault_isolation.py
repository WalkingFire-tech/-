"""
L3 异常处理层 - 故障隔离 (Fault Isolator)

类比：炎症反应——将感染区域隔离，防止扩散
- 模块级隔离：标记故障模块为不可用
- 隔离墙：阻止级联故障传播
- 自动解除：冷却后试探性恢复
"""
import time
from typing import Dict, List, Optional
from loguru import logger
from infrastructure.config_manager import config
from datetime import datetime


class FaultIsolator:

    def __init__(self):
        self._isolation_cooldown = config.get("defense.isolation_cooldown_seconds", 300)
        self._max_isolated = config.get("defense.max_isolated_modules", 20)
        self._isolated: Dict[str, dict] = {}
        self._isolation_log: List[dict] = []

    def isolate(self, module_name: str, reason: str = "") -> bool:
        if module_name in self._isolated:
            self._isolated[module_name]["reason"] = reason
            self._isolated[module_name]["isolated_at"] = time.time()
            self._isolated[module_name]["isolation_count"] += 1
            return True
        if len(self._isolated) >= self._max_isolated:
            oldest = min(self._isolated.items(), key=lambda x: x[1]["isolated_at"])
            self.release(oldest[0])
        self._isolated[module_name] = {
            "reason": reason,
            "isolated_at": time.time(),
            "isolation_count": 1,
            "dependencies": [],
        }
        entry = {
            "action": "isolate",
            "module": module_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self._isolation_log.append(entry)
        logger.warning(f"🔒 故障隔离: {module_name} ({reason})")
        return True

    def release(self, module_name: str) -> bool:
        if module_name not in self._isolated:
            return False
        info = self._isolated.pop(module_name)
        entry = {
            "action": "release",
            "module": module_name,
            "was_isolated_for": f"{time.time() - info['isolated_at']:.0f}s",
            "timestamp": datetime.now().isoformat(),
        }
        self._isolation_log.append(entry)
        logger.info(f"🔓 故障解除: {module_name}")
        return True

    def is_isolated(self, module_name: str) -> bool:
        if module_name not in self._isolated:
            return False
        info = self._isolated[module_name]
        elapsed = time.time() - info["isolated_at"]
        if elapsed > self._isolation_cooldown:
            if info["isolation_count"] <= 3:
                self.release(module_name)
                return False
            else:
                logger.warning(f"🔒 {module_name}反复隔离{info['isolation_count']}次，保持隔离")
                return True
        return True

    def set_dependencies(self, module_name: str, deps: List[str]):
        if module_name in self._isolated:
            self._isolated[module_name]["dependencies"] = deps

    def cascade_check(self, module_name: str) -> List[str]:
        affected = []
        for name, info in self._isolated.items():
            if module_name in info.get("dependencies", []):
                affected.append(name)
        return affected

    def get_isolated_modules(self) -> dict:
        return {name: {
            "reason": info["reason"],
            "isolated_at": datetime.fromtimestamp(info["isolated_at"]).isoformat(),
            "duration": f"{time.time() - info['isolated_at']:.0f}s",
            "isolation_count": info["isolation_count"],
        } for name, info in self._isolated.items()}

    def get_log(self, limit: int = 20) -> List[dict]:
        return self._isolation_log[-limit:]


fault_isolator = FaultIsolator()