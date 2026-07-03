"""
L1 预防层 - 熔断保护 (Circuit Breaker)

类比：皮肤的痛觉反射——遇到持续伤害时自动收缩保护
- 连续失败时熔断，阻止请求继续冲击
- 冷却后自动半开试探
- 成功则恢复，失败则继续熔断
"""
import time
from typing import Dict
from loguru import logger


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, half_open_max: int = 1):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._circuits: Dict[str, dict] = {}

    def _get_circuit(self, name: str) -> dict:
        if name not in self._circuits:
            self._circuits[name] = {
                "state": self.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0,
                "half_open_calls": 0,
            }
        return self._circuits[name]

    def is_available(self, name: str) -> bool:
        circuit = self._get_circuit(name)
        if circuit["state"] == self.CLOSED:
            return True
        if circuit["state"] == self.OPEN:
            if time.time() - circuit["last_failure_time"] > self.recovery_timeout:
                circuit["state"] = self.HALF_OPEN
                circuit["half_open_calls"] = 0
                logger.info(f"⚡ 熔断器[{name}]进入半开状态，试探性放行")
                return True
            return False
        if circuit["state"] == self.HALF_OPEN:
            return circuit["half_open_calls"] < self.half_open_max
        return True

    def record_success(self, name: str):
        circuit = self._get_circuit(name)
        circuit["success_count"] += 1
        circuit["failure_count"] = 0
        if circuit["state"] == self.HALF_OPEN:
            circuit["state"] = self.CLOSED
            logger.info(f"✅ 熔断器[{name}]恢复正常（半开试探成功）")

    def record_failure(self, name: str):
        circuit = self._get_circuit(name)
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = time.time()
        if circuit["state"] == self.HALF_OPEN:
            circuit["state"] = self.OPEN
            logger.warning(f"🔴 熔断器[{name}]半开试探失败，重新熔断")
        elif circuit["failure_count"] >= self.failure_threshold:
            circuit["state"] = self.OPEN
            logger.warning(f"🔴 熔断器[{name}]已熔断（连续{circuit['failure_count']}次失败）")

    def get_state(self, name: str) -> str:
        return self._get_circuit(name)["state"]

    def get_all_states(self) -> dict:
        return {name: c["state"] for name, c in self._circuits.items()}

    def reset(self, name: str):
        if name in self._circuits:
            self._circuits[name] = {
                "state": self.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0,
                "half_open_calls": 0,
            }
            logger.info(f"🔄 熔断器[{name}]已重置")


circuit_breaker = CircuitBreaker()