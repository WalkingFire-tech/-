"""
触发率监控 — 确保能力存在 = 能力运行

核心洞察（P5审计）：
  系统有大量已编码能力，但无法确认它们是否真正在运行。
  触发率监控是验证基础设施——没有它，所有改进都无法验证。

设计原则：
  - 轻量：每个监控点仅计数，不存储完整事件
  - 非侵入：record()调用不影响主路径性能
  - 可观测：get_report()生成人类可读的状态报告
  - 可告警：低于阈值自动触发告警
"""
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class TriggerRateMonitor:
    """触发率监控器"""

    _instance = None
    _lock = threading.Lock()

    ALERT_LEVELS = {
        "critical": 0.05,
        "warning": 0.10,
        "info": 0.20,
    }

    def __init__(self):
        self._monitors: Dict[str, Dict] = {}
        self._alert_callback: Optional[Callable] = None
        self._history_max = 1000

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_alert_callback(self, callback: Callable):
        self._alert_callback = callback

    def register(self, name: str, expected_rate: float, description: str = ""):
        """注册一个监控点"""
        self._monitors[name] = {
            "expected": expected_rate,
            "actual": 0.0,
            "count": 0,
            "total": 0,
            "description": description,
            "history": [],
            "last_alert": None,
        }

    def record(self, name: str, triggered: bool):
        """记录一次调用"""
        if name not in self._monitors:
            return
        m = self._monitors[name]
        m["total"] += 1
        if triggered:
            m["count"] += 1
        m["actual"] = m["count"] / m["total"] if m["total"] > 0 else 0.0
        m["history"].append({
            "time": datetime.now().isoformat(),
            "triggered": triggered,
            "rate": m["actual"],
        })
        if len(m["history"]) > self._history_max:
            m["history"] = m["history"][-self._history_max:]
        self._check_alert(name)

    def _check_alert(self, name: str):
        m = self._monitors[name]
        rate = m["actual"]
        if m["total"] < 5:
            return
        expected = m["expected"]
        if expected > 0 and rate < expected * 0.5:
            level = "critical"
        elif expected > 0 and rate < expected * 0.8:
            level = "warning"
        elif rate < 0.05:
            level = "critical"
        else:
            return
        msg = f"{name} 触发率 {rate:.1%}，预期 {expected:.1%}，{level}级"
        m["last_alert"] = {"level": level, "message": msg, "time": datetime.now().isoformat()}
        logger.warning(f"触发率告警: {msg}")
        if self._alert_callback:
            try:
                self._alert_callback(name, level, msg)
            except Exception:
                pass

    def alert(self, name: str, level: str, message: str):
        if self._alert_callback:
            try:
                self._alert_callback(name, level, message)
            except Exception:
                pass

    def get_report(self) -> Dict:
        """生成监控报告"""
        report = {}
        for name, m in self._monitors.items():
            status = "healthy"
            if m["total"] >= 5:
                if m["actual"] < m["expected"] * 0.5:
                    status = "degraded"
                elif m["actual"] < m["expected"] * 0.8:
                    status = "warning"
            trend = self._compute_trend(m["history"])
            report[name] = {
                "description": m["description"],
                "expected": m["expected"],
                "actual": m["actual"],
                "count": m["count"],
                "total": m["total"],
                "status": status,
                "trend": trend,
                "last_alert": m.get("last_alert"),
            }
        return report

    def _compute_trend(self, history: List[Dict]) -> str:
        if len(history) < 10:
            return "insufficient_data"
        recent = [h["rate"] for h in history[-5:]]
        older = [h["rate"] for h in history[-10:-5]]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        diff = avg_recent - avg_older
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        return "stable"

    def reset(self):
        self._monitors.clear()


trigger_rate_monitor = TriggerRateMonitor.get_instance()