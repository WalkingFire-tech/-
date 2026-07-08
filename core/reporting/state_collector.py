"""
状态收集器 - 接收所有层的状态报告，并提供汇总分析
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import threading
from infrastructure.database_manager import DatabaseManager
import json
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.state_report import (
    LayerStateReport, LayerStatus, LayerHealth, SystemSnapshot
)


class StateCollector:
    """
    状态收集器
    
    这是一个单例，所有层都通过它报告状态。
    它收集所有报告，提供历史查询和健康度分析。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        self._latest_reports: Dict[str, LayerStateReport] = {}
        self._history: List[LayerStateReport] = []
        self._max_history = 1000
        
        self._heartbeat_initialized = False
        self._cached_snapshot: Optional[SystemSnapshot] = None
        self._snapshot_cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 5
        
        self._listeners: List[Callable[[LayerStateReport], None]] = []
        self._last_snapshot: Optional[SystemSnapshot] = None
        
        self._db_path = Path("data/state_collector.db")
        
        self._init_database()
        self._init_heartbeat()
        
        self._listeners: List[Callable] = []
        
        self._db_path = Path("data/state_reports.db")
        self._init_database()
        
        self._last_snapshot: Optional[SystemSnapshot] = None
        
        self._init_heartbeat()
        
        logger.info("📊 状态收集器已初始化")
    
    def _init_heartbeat(self):
        """初始化并启动心跳服务"""
        if self._heartbeat_initialized:
            return
        try:
            from core.introspection.heartbeat import get_heartbeat_manager
            hbm = get_heartbeat_manager()
            
            for layer in ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]:
                hbm.register_layer(layer)
            
            hbm.start_background()
            
            self._heartbeat_initialized = True
            logger.info("❤️ 心跳服务已自动启动")
        except Exception as e:
            logger.warning(f"心跳服务启动失败: {e}，将在下次 collect 时重试")
    
    def _init_database(self):
        """初始化数据库"""
        self._db_path.parent.mkdir(exist_ok=True)
        
        conn = DatabaseManager.get(str(self._db_path))._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS state_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT,
                timestamp TEXT,
                status TEXT,
                health TEXT,
                metrics TEXT,
                issues TEXT,
                warnings TEXT,
                last_operation TEXT,
                active_tasks TEXT,
                confidence REAL,
                layer_version TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                layer TEXT,
                health TEXT,
                confidence REAL,
                snapshot TEXT
            )
        ''')
        
        conn.commit()
    
    def collect(self, report: LayerStateReport) -> None:
        """
        收集状态报告
        
        所有层都应该在操作完成后调用此方法。
        """
        if not self._heartbeat_initialized:
            self._init_heartbeat()
        
        self._latest_reports[report.layer_name] = report
        
        self._history.append(report)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        self._save_report(report)
        
        self._notify_listeners(report)
        
        if report.needs_attention():
            logger.warning(
                f"⚠️ {report.layer_name} 需要关注: "
                f"健康={report.health.value}, "
                f"问题={len(report.issues)}, "
                f"警告={len(report.warnings)}"
            )
    
    def _save_report(self, report: LayerStateReport):
        """保存报告到数据库"""
        try:
            conn = DatabaseManager.get(str(self._db_path))._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO state_reports 
                (layer, timestamp, status, health, metrics, issues, warnings,
                 last_operation, active_tasks, confidence, layer_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.layer_name,
                report.timestamp,
                report.status.value,
                report.health.value,
                json.dumps(report.metrics),
                json.dumps(report.issues),
                json.dumps(report.warnings),
                report.last_operation,
                json.dumps(report.active_tasks),
                report.confidence_score,
                report.layer_version
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"保存状态报告失败: {e}")
    
    def get_latest(self, layer_name: str) -> Optional[LayerStateReport]:
        """获取某层的最新报告"""
        return self._latest_reports.get(layer_name)
    
    def get_all_latest(self) -> Dict[str, LayerStateReport]:
        """获取所有层的最新报告"""
        return self._latest_reports.copy()
    
    def get_history(self, layer_name: Optional[str] = None, 
                    limit: int = 100) -> List[LayerStateReport]:
        """获取历史报告"""
        if layer_name:
            return [r for r in self._history[-limit:] if r.layer_name == layer_name]
        return self._history[-limit:]
    
    def get_snapshot(self) -> SystemSnapshot:
        """获取当前系统快照"""
        if self._cached_snapshot and self._snapshot_cache_time:
            if (datetime.now() - self._snapshot_cache_time).total_seconds() < self._cache_ttl_seconds:
                return self._cached_snapshot
        
        reports = self._latest_reports
        
        if not reports:
            snapshot = SystemSnapshot(
                timestamp=datetime.now().isoformat(),
                layer_reports={},
                overall_health=LayerHealth.UNKNOWN,
                overall_confidence=0.0,
                layers_count=0,
                healthy_layers=0,
                warning_layers=0,
                critical_layers=0
            )
            self._cached_snapshot = snapshot
            self._snapshot_cache_time = datetime.now()
            return snapshot
        
        layers = list(reports.keys())
        healthy = sum(1 for r in reports.values() if r.health == LayerHealth.HEALTHY)
        warning = sum(1 for r in reports.values() if r.health == LayerHealth.WARNING)
        critical = sum(1 for r in reports.values() if r.health == LayerHealth.CRITICAL)
        
        if critical > 0:
            overall_health = LayerHealth.CRITICAL
        elif warning > 0:
            overall_health = LayerHealth.WARNING
        else:
            overall_health = LayerHealth.HEALTHY
        
        confidences = [r.confidence_score for r in reports.values()]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        aggregated = {}
        metric_keys = set()
        for r in reports.values():
            metric_keys.update(r.metrics.keys())
        
        for key in metric_keys:
            values = [r.metrics.get(key, 0) for r in reports.values() if key in r.metrics]
            if values:
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    aggregated[key] = sum(numeric_values) / len(numeric_values)
        
        snapshot = SystemSnapshot(
            timestamp=datetime.now().isoformat(),
            layer_reports=reports,
            overall_health=overall_health,
            overall_confidence=overall_confidence,
            layers_count=len(layers),
            healthy_layers=healthy,
            warning_layers=warning,
            critical_layers=critical,
            aggregated_metrics=aggregated
        )
        
        self._last_snapshot = snapshot
        self._cached_snapshot = snapshot
        self._snapshot_cache_time = datetime.now()
        return snapshot
    
    def add_listener(self, callback: Callable[[LayerStateReport], None]) -> None:
        """添加状态报告监听器"""
        self._listeners.append(callback)
    
    def _notify_listeners(self, report: LayerStateReport):
        """通知所有监听器"""
        for callback in self._listeners:
            try:
                callback(report)
            except Exception as e:
                logger.error(f"状态监听器回调失败: {e}")
    
    def register_layer(self, layer_name: str) -> None:
        """注册一个层（创建初始状态记录）"""
        if layer_name not in self._latest_reports:
            report = LayerStateReport(
                layer_name=layer_name,
                timestamp=datetime.now().isoformat(),
                status=LayerStatus.IDLE,
                health=LayerHealth.UNKNOWN,
                metrics={},
                issues=[],
                warnings=[],
                confidence_score=0.5
            )
            self._latest_reports[layer_name] = report
            logger.info(f"📊 已注册层: {layer_name}")
    
    def get_health_trend(self, layer_name: str, hours: int = 24) -> List[Dict]:
        """获取某层的健康度趋势"""
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            conn = DatabaseManager.get(str(self._db_path))._get_conn()
            cursor = conn.execute('''
                SELECT timestamp, health, confidence
                FROM state_reports
                WHERE layer = ? AND timestamp > ?
                ORDER BY timestamp ASC
            ''', (layer_name, cutoff))
            
            return [
                {
                    "timestamp": row["timestamp"],
                    "health": row["health"],
                    "confidence": row["confidence"]
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"获取健康趋势失败: {e}")
            return []
    
    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康度摘要"""
        snapshot = self.get_snapshot()
        
        return {
            "total_layers": snapshot.layers_count,
            "healthy_layers": snapshot.healthy_layers,
            "warning_layers": snapshot.warning_layers,
            "critical_layers": snapshot.critical_layers,
            "overall_health": snapshot.overall_health.value,
            "overall_confidence": snapshot.overall_confidence
        }
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要（人类可读）"""
        snapshot = self.get_snapshot()
        
        return {
            "timestamp": snapshot.timestamp,
            "overall_health": snapshot.overall_health.value,
            "overall_confidence": f"{snapshot.overall_confidence:.1%}",
            "layers": {
                name: {
                    "status": report.status.value,
                    "health": report.health.value,
                    "confidence": f"{report.confidence_score:.1%}",
                    "issues": len(report.issues),
                    "warnings": len(report.warnings)
                }
                for name, report in snapshot.layer_reports.items()
            },
            "summary": {
                "total": snapshot.layers_count,
                "healthy": snapshot.healthy_layers,
                "warning": snapshot.warning_layers,
                "critical": snapshot.critical_layers
            }
        }


_state_collector = None

_state_collector: Optional[StateCollector] = None
_state_collector_lock = threading.Lock()


def get_state_collector() -> StateCollector:
    """获取全局状态收集器单例"""
    global _state_collector
    if _state_collector is None:
        with _state_collector_lock:
            if _state_collector is None:
                _state_collector = StateCollector()
    return _state_collector