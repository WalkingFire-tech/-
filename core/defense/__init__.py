"""
SDRS 四层防御体系 - Self-Defense & Resilience System

类比人体防御机制：
  L1 预防层（皮肤屏障）  → InputSanitizer + CircuitBreaker
  L2 监控感知层（神经系统）→ HealthMetricsCollector + AnomalyDetector
  L3 异常处理层（炎症/免疫）→ FaultIsolator + ExceptionPhagocyte
  L4 自修复层（干细胞/可塑性）→ AutoRollback + SelfHealingSwitch + CognitiveSelfRepair

整合入口：SystemGuardian
"""

from core.defense.input_sanitizer import InputSanitizer
from core.defense.circuit_breaker import CircuitBreaker
from core.defense.health_metrics import HealthMetricsCollector
from core.defense.anomaly_detector import AnomalyDetector
from core.defense.fault_isolation import FaultIsolator
from core.defense.exception_phagocyte import ExceptionPhagocyte
from core.defense.auto_rollback import AutoRollback
from core.defense.self_healing_switch import SelfHealingSwitch
from core.defense.cognitive_self_repair import CognitiveSelfRepair
from core.defense.guardian import SystemGuardian

__all__ = [
    "InputSanitizer",
    "CircuitBreaker",
    "HealthMetricsCollector",
    "AnomalyDetector",
    "FaultIsolator",
    "ExceptionPhagocyte",
    "AutoRollback",
    "SelfHealingSwitch",
    "CognitiveSelfRepair",
    "SystemGuardian",
]