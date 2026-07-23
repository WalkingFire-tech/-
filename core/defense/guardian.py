"""
SDRS 四层防御体系 - 系统守护者 (System Guardian)

整合所有防御层，提供统一入口：
  L1 预防层  → InputSanitizer + CircuitBreaker
  L2 监控层  → HealthMetricsCollector + AnomalyDetector
  L3 处理层  → FaultIsolator + ExceptionPhagocyte
  L4 修复层  → AutoRollback + SelfHealingSwitch + CognitiveSelfRepair

守护者职责：
  1. 启动时初始化所有防御组件
  2. 定期巡检（健康指标→异常检测→故障隔离→自修复）
  3. 提供统一的防御API
"""
import time
import asyncio
from typing import Dict, Optional, Any
from loguru import logger
from datetime import datetime

from core.defense.input_sanitizer import input_sanitizer
from core.defense.circuit_breaker import circuit_breaker
from core.defense.health_metrics import health_metrics
from core.defense.anomaly_detector import anomaly_detector
from core.defense.fault_isolation import fault_isolator
from core.defense.exception_phagocyte import exception_phagocyte
from core.defense.auto_rollback import auto_rollback
from core.defense.self_healing_switch import self_healing_switch
from core.defense.cognitive_self_repair import cognitive_self_repair


class SystemGuardian:
    PATROL_INTERVAL = 60

    def __init__(self):
        self._running = False
        self._patrol_count = 0
        self._last_patrol = None

    async def start_patrol(self, interval: int = None):
        if self._running:
            return
        self._running = True
        interval = interval or self.PATROL_INTERVAL
        logger.info(f"🛡️ 系统守护者启动巡逻 (间隔{interval}秒)")
        while self._running:
            try:
                await self.patrol()
            except Exception as e:
                logger.error(f"守护者巡逻异常: {e}")
            await asyncio.sleep(interval)

    def stop_patrol(self):
        self._running = False
        logger.info("🛡️ 系统守护者停止巡逻")

    async def patrol(self):
        self._patrol_count += 1
        self._last_patrol = datetime.now().isoformat()
        self._collect_health_metrics()
        self._check_circuit_breakers()
        self._attempt_regenerations()
        if self._patrol_count % 10 == 0:
            self._run_cognitive_repair()
        if self._patrol_count % 15 == 0:
            self._run_low_load_reorganization()
        if self._patrol_count % 20 == 0:
            self._run_knowledge_forgetting()

    def _collect_health_metrics(self):
        try:
            from core.ports.adapters import get_storage_port
            row = get_storage_port("data/experience_pool.db").query_one("SELECT COUNT(*) FROM experiences WHERE success=0")
            failures = row[0] if row else 0
            row = get_storage_port("data/experience_pool.db").query_one("SELECT COUNT(*) FROM experiences")
            total = row[0] if row else 0

            if total > 0:
                error_rate = failures / total
                health_metrics.record("error_rate", error_rate)
                anomaly_detector.check("error_rate", error_rate)
        except Exception:
            logger.warning("操作降级跳过")

    def _check_circuit_breakers(self):
        for name, state in circuit_breaker.get_all_states().items():
            if state == "open":
                health_metrics.record(f"circuit_breaker_{name}", 1.0)

    def _attempt_regenerations(self):
        for name, info in fault_isolator.get_isolated_modules().items():
            self_healing_switch.attempt_regeneration(name)

    def _run_cognitive_repair(self):
        try:
            cognitive_self_repair.run_full_repair()
        except Exception as e:
            logger.error(f"认知自修复失败: {e}")

    def _run_knowledge_forgetting(self):
        try:
            from core.knowledge_forgetting import knowledge_forgetting
            report = knowledge_forgetting.execute_fading(dry_run=False)
            if report["rules"]["pruned"] > 0 or report["experiences"]["pruned"] > 0:
                logger.info(f"🧹 知识遗忘: 规则淡化{report['rules']['faded']}+清除{report['rules']['pruned']}, 经验淡化{report['experiences']['faded']}+清除{report['experiences']['pruned']}")
        except Exception as e:
            logger.error(f"知识遗忘失败: {e}")

    def _run_low_load_reorganization(self):
        try:
            from core.low_load_reorganization import low_load_reorganization
            result = low_load_reorganization.run()
            s = result.get("summary", {})
            if any(v > 0 for v in s.values()):
                logger.info(f"🔄 低负载重组: 激活{s.get('rules_activated',0)} 合并{s.get('rules_merged',0)} 提取{s.get('rules_extracted',0)} 连接{s.get('connections_found',0)}")
        except Exception as e:
            logger.error(f"低负载重组失败: {e}")

    def sanitize_input(self, raw: str) -> tuple:
        return input_sanitizer.sanitize(raw)

    def check_circuit(self, name: str) -> bool:
        return circuit_breaker.is_available(name)

    def record_circuit_success(self, name: str):
        circuit_breaker.record_success(name)

    def record_circuit_failure(self, name: str):
        circuit_breaker.record_failure(name)

    def swallow_exception(self, exception: Exception, context: str = "", module: str = "") -> dict:
        return exception_phagocyte.swallow(exception, context, module)

    def create_snapshot(self, target: str, data: Any) -> str:
        return auto_rollback.create_snapshot(target, data)

    def rollback(self, target: str, reason: str = "", entropy: float = 0.0) -> Optional[Any]:
        return auto_rollback.rollback(target, reason, entropy)

    def get_status(self) -> dict:
        return {
            "patrol_count": self._patrol_count,
            "last_patrol": self._last_patrol,
            "running": self._running,
            "circuit_breakers": circuit_breaker.get_all_states(),
            "isolated_modules": fault_isolator.get_isolated_modules(),
            "health_snapshot": health_metrics.get_snapshot(),
            "recent_anomalies": anomaly_detector.get_anomalies(5),
            "exception_stats": exception_phagocyte.get_stats(),
            "healing_statuses": self_healing_switch.get_all_statuses(),
            "rollback_history": auto_rollback.get_rollback_history(5),
        }


system_guardian = SystemGuardian()