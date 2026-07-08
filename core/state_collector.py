"""
状态收集器 - L6内省层的基础设施
收集所有层的状态报告，汇总系统整体健康度
"""

import threading
import time
import os
import json
from infrastructure.database_manager import DatabaseManager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from collections import defaultdict
from enum import Enum
from dataclasses import dataclass

from core.state_report import (
    LayerStateReport,
    LayerStatus,
    LayerName
)

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class HealthLevel(Enum):
    """健康度等级"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


@dataclass
class SystemHealthSummary:
    """系统健康度摘要"""
    level: HealthLevel
    timestamp: str
    layer_summaries: Dict[str, Dict]
    overall_score: float
    critical_issues: List[str]
    recommendations: List[str]


class StateCollector:
    """
    状态收集器
    
    职责：
    1. 收集所有层的状态报告
    2. 汇总系统整体健康度
    3. 通知监听者（L6、调度器等）
    4. 持久化状态历史
    """
    
    def __init__(self, db_path: str = "data/state_collector.db"):
        self.db_path = db_path
        self._reports: List[LayerStateReport] = []
        self._listeners: List[Callable] = []
        self._lock = threading.Lock()
        
        self._layer_latest: Dict[str, LayerStateReport] = {}
        
        self._health_thresholds = {
            'healthy': 0.8,
            'warning': 0.6,
            'danger': 0.4,
            'critical': 0.2
        }
        
        self._init_database()
        
        logger.info("📊 状态收集器已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = DatabaseManager.get(self.db_path)._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS state_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer_name TEXT,
                status TEXT,
                timestamp TEXT,
                metrics TEXT,
                issues TEXT,
                confidence REAL,
                report_json TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                timestamp TEXT,
                overall_score REAL,
                summary_json TEXT
            )
        ''')
        
        conn.commit()
    
    def collect(self, report: LayerStateReport) -> None:
        """
        收集状态报告
        
        这是核心接口，所有层都通过这个接口报告状态
        """
        with self._lock:
            self._reports.append(report)
            self._layer_latest[report.layer_name] = report
            
            self._save_report(report)
            
            self._notify_listeners(report)
            
            if len(self._reports) % 10 == 0:
                self._cleanup_old_reports()
    
    def get_latest(self, layer_name: str) -> Optional[LayerStateReport]:
        """获取指定层的最新状态"""
        with self._lock:
            return self._layer_latest.get(layer_name)
    
    def get_all_latest(self) -> Dict[str, LayerStateReport]:
        """获取所有层的最新状态"""
        with self._lock:
            return self._layer_latest.copy()
    
    def get_health_summary(self) -> SystemHealthSummary:
        """
        汇总系统整体健康度
        
        这是L6内省层的核心输入
        """
        with self._lock:
            layer_summaries = {}
            overall_score = 0.0
            critical_issues = []
            recommendations = []
            
            for layer_name, report in self._layer_latest.items():
                layer_score = self._calculate_layer_score(report)
                layer_summaries[layer_name] = {
                    'status': report.status.value,
                    'score': layer_score,
                    'confidence': report.confidence_score,
                    'issues_count': len(report.issues),
                    'is_healthy': report.is_healthy()
                }
                
                overall_score += layer_score
                
                if report.needs_attention():
                    critical_issues.extend([
                        f"[{layer_name}] {issue}" 
                        for issue in report.issues[:3]
                    ])
                
                if report.status == LayerStatus.ERROR:
                    recommendations.append(f"检查 {layer_name} 层的运行状态")
                elif report.status == LayerStatus.DEGRADED:
                    recommendations.append(f"优化 {layer_name} 层的性能")
            
            if self._layer_latest:
                overall_score /= len(self._layer_latest)
            
            level = self._determine_health_level(overall_score)
            
            summary = SystemHealthSummary(
                level=level,
                timestamp=datetime.now().isoformat(),
                layer_summaries=layer_summaries,
                overall_score=overall_score,
                critical_issues=critical_issues[:10],
                recommendations=recommendations[:5]
            )
            
            self._save_summary(summary)
            
            return summary
    
    def _calculate_layer_score(self, report: LayerStateReport) -> float:
        """计算层分数"""
        base_score = report.confidence_score
        
        status_penalty = {
            LayerStatus.RUNNING: 0.0,
            LayerStatus.IDLE: 0.0,
            LayerStatus.BUSY: 0.1,
            LayerStatus.DEGRADED: 0.3,
            LayerStatus.ERROR: 0.5
        }
        
        score = base_score - status_penalty.get(report.status, 0.0)
        score -= len(report.issues) * 0.05
        
        return max(0.0, min(1.0, score))
    
    def _determine_health_level(self, score: float) -> HealthLevel:
        """判定健康度等级"""
        if score >= self._health_thresholds['healthy']:
            return HealthLevel.HEALTHY
        elif score >= self._health_thresholds['warning']:
            return HealthLevel.WARNING
        elif score >= self._health_thresholds['danger']:
            return HealthLevel.DANGER
        else:
            return HealthLevel.CRITICAL
    
    def register_listener(self, listener: Callable):
        """
        注册监听者
        
        当状态变化时，监听者会被通知
        """
        self._listeners.append(listener)
    
    def _notify_listeners(self, report: LayerStateReport):
        """通知监听者"""
        for listener in self._listeners:
            try:
                listener(report)
            except Exception as e:
                logger.warning(f"监听者通知失败: {e}")
    
    def _save_report(self, report: LayerStateReport):
        """保存报告"""
        try:
            conn = DatabaseManager.get(self.db_path)._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO state_reports
                (layer_name, status, timestamp, metrics, issues, confidence, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.layer_name,
                report.status.value,
                report.timestamp,
                json.dumps(report.metrics),
                json.dumps(report.issues),
                report.confidence_score,
                json.dumps(report.to_dict())
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"保存状态报告失败: {e}")
    
    def _save_summary(self, summary: SystemHealthSummary):
        """保存摘要"""
        try:
            conn = DatabaseManager.get(self.db_path)._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO health_summaries
                (level, timestamp, overall_score, summary_json)
                VALUES (?, ?, ?, ?)
            ''', (
                summary.level.value,
                summary.timestamp,
                summary.overall_score,
                json.dumps({
                    'level': summary.level.value,
                    'layer_summaries': summary.layer_summaries,
                    'overall_score': summary.overall_score,
                    'critical_issues': summary.critical_issues,
                    'recommendations': summary.recommendations
                })
            ))
            conn.commit()
        except Exception as e:
            logger.warning(f"保存健康度摘要失败: {e}")
    
    def _cleanup_old_reports(self):
        """清理旧报告"""
        with self._lock:
            if len(self._reports) > 1000:
                self._reports = self._reports[-500:]
    
    def get_layer_history(self, layer_name: str, limit: int = 100) -> List[Dict]:
        """获取层的历史状态"""
        try:
            conn = DatabaseManager.get(self.db_path)._get_conn()
            cursor = conn.execute('''
                SELECT * FROM state_reports
                WHERE layer_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (layer_name, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"获取层历史失败: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return {
                'total_reports': len(self._reports),
                'layers_monitored': len(self._layer_latest),
                'listeners_count': len(self._listeners),
                'latest_timestamp': max(
                    [r.timestamp for r in self._layer_latest.values()],
                    default=None
                )
            }


state_collector = StateCollector()