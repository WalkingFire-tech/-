"""
L2 监控感知层 - 健康指标采集 (Health Metrics Collector)

类比：神经系统——感知全身状态
- 采集系统各维度健康指标
- 趋势预测（基于滑动窗口）
- 预警机制（阈值触发）
"""
import time
from infrastructure.database_manager import DatabaseManager
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class HealthMetricsCollector:
    WINDOW_SIZE = 100
    ALERT_THRESHOLDS = {
        "error_rate": 0.5,
        "latency_p95": 10.0,
        "memory_usage": 0.9,
        "cpu_usage": 0.9,
    }

    def __init__(self, db_path: str = "data/defense_metrics.db"):
        self.db_path = db_path
        self._metrics: Dict[str, List[tuple]] = {}
        self._alerts: List[dict] = []
        self._init_db()

    def _init_db(self):
        try:
            db = DatabaseManager.get(self.db_path)
            db.executescript('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    value REAL,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    value REAL,
                    threshold REAL,
                    message TEXT,
                    timestamp TEXT
                )
            ''')
        except Exception as e:
            logger.debug(f"指标数据库初始化失败: {e}")

    def record(self, metric_name: str, value: float):
        ts = time.time()
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append((ts, value))
        if len(self._metrics[metric_name]) > self.WINDOW_SIZE:
            self._metrics[metric_name] = self._metrics[metric_name][-self.WINDOW_SIZE:]
        self._check_threshold(metric_name, value)
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("INSERT INTO metrics (metric_name, value, timestamp) VALUES (?, ?, ?)",
                         (metric_name, value, datetime.now().isoformat()), commit=True)
        except Exception:
            pass

    def _check_threshold(self, metric_name: str, value: float):
        threshold = self.ALERT_THRESHOLDS.get(metric_name)
        if threshold is not None and value > threshold:
            alert = {
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "message": f"⚠️ {metric_name}={value:.2f} 超过阈值{threshold:.2f}",
                "timestamp": datetime.now().isoformat(),
            }
            self._alerts.append(alert)
            if len(self._alerts) > 200:
                self._alerts = self._alerts[-200:]
            logger.warning(alert["message"])
            try:
                db = DatabaseManager.get(self.db_path)
                db.execute("INSERT INTO alerts (metric_name, value, threshold, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                             (metric_name, value, threshold, alert["message"], alert["timestamp"]), commit=True)
            except Exception:
                pass

    def get_current(self, metric_name: str) -> Optional[float]:
        if metric_name in self._metrics and self._metrics[metric_name]:
            return self._metrics[metric_name][-1][1]
        return None

    def get_trend(self, metric_name: str, window: int = 20) -> str:
        if metric_name not in self._metrics or len(self._metrics[metric_name]) < 2:
            return "insufficient_data"
        recent = self._metrics[metric_name][-window:]
        values = [v[1] for v in recent]
        if len(values) < 2:
            return "stable"
        first_half = sum(values[:len(values)//2]) / max(len(values)//2, 1)
        second_half = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
        diff = second_half - first_half
        if abs(diff) < 0.01:
            return "stable"
        return "rising" if diff > 0 else "declining"

    def get_alerts(self, limit: int = 20) -> List[dict]:
        return self._alerts[-limit:]

    def get_snapshot(self) -> dict:
        snapshot = {}
        for name, readings in self._metrics.items():
            if readings:
                values = [v[1] for v in readings]
                snapshot[name] = {
                    "current": values[-1],
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "trend": self.get_trend(name),
                }
        return snapshot


health_metrics = HealthMetricsCollector()