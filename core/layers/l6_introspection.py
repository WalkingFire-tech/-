"""
L6: 内省层 - 系统自我感知、诊断与修复的最高层

职责：
1. 持续收集所有层的状态（通过状态收集器和心跳机制）
2. 评估系统整体健康度（不仅仅是各层健康，而是整体协调性）
3. 预测潜在异常（基于历史趋势和模式）
4. 触发自我修复（当检测到问题时，自动启动修复流程）
5. 生成内省报告（为设计者提供透明的系统状态视图）

与L5的关系：
L5是"进化"——从经验中学习，改变系统行为。
L6是"内省"——感知系统状态，判断进化方向是否正确。

核心理念：
L6是系统的"前额叶皮质"——它不会直接控制每一层，
但它会持续感知、评估、并在必要时发出警告或触发修复。
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.introspection.layer_reporter import LayerReporter
from core.reporting.state_collector import get_state_collector, SystemSnapshot
from core.introspection.heartbeat import get_heartbeat_manager, HeartbeatStatus
from core.state_report import LayerHealth, LayerStatus, LayerStateReport


class SystemHealthLevel(Enum):
    """系统整体健康级别"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class AnomalySeverity(Enum):
    """异常严重程度"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


@dataclass
class HealthScore:
    """健康度评分"""
    overall: float
    layers: Dict[str, float]
    coordination: float
    trend: str
    issues: List[str]
    timestamp: str
    
    def get_level(self) -> SystemHealthLevel:
        if self.overall >= 0.9:
            return SystemHealthLevel.EXCELLENT
        elif self.overall >= 0.7:
            return SystemHealthLevel.GOOD
        elif self.overall >= 0.5:
            return SystemHealthLevel.FAIR
        elif self.overall >= 0.3:
            return SystemHealthLevel.POOR
        else:
            return SystemHealthLevel.CRITICAL


@dataclass
class Anomaly:
    """异常记录"""
    id: str
    title: str
    description: str
    severity: AnomalySeverity
    detected_at: str
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None
    related_layers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
            "related_layers": self.related_layers
        }


@dataclass
class IntrospectionReport:
    """内省报告"""
    timestamp: str
    health: HealthScore
    active_anomalies: List[Anomaly]
    recent_changes: List[Dict]
    recommendations: List[str]
    summary: str


class L6IntrospectionLayer:
    """L6: 内省层"""
    
    def __init__(self):
        self.reporter = LayerReporter("L6")
        self.collector = get_state_collector()
        self.heartbeat = get_heartbeat_manager()
        
        self.reporter.report_idle()
        
        self.health_history: List[HealthScore] = []
        self.anomalies: List[Anomaly] = []
        self.resolved_anomalies: List[Anomaly] = []
        
        self.stats = {
            'total_introspections': 0,
            'health_checks': 0,
            'anomalies_detected': 0,
            'anomalies_resolved': 0,
            'auto_repairs_triggered': 0,
            'avg_health_score': 0.0,
            'last_report_time': None,
        }
        
        self.config = {
            'introspection_interval_seconds': 60,
            'health_thresholds': {
                'critical': 0.3,
                'poor': 0.5,
                'fair': 0.7,
                'good': 0.9,
            },
            'anomaly_detection': {
                'confidence_drop_threshold': 0.15,
                'error_rate_threshold': 0.2,
                'layer_dead_threshold_seconds': 30,
            }
        }
        
        self._running = False
        self._thread = None
        
        logger.info("🔍 L6内省层已初始化（含状态报告 + 自动修复）")
        self.reporter.report_completed(
            metrics={
                "introspection_interval": self.config['introspection_interval_seconds'],
                "health_thresholds_set": len(self.config['health_thresholds'])
            },
            confidence=1.0
        )
    
    def start_background_introspection(self):
        """启动后台内省线程"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._introspection_loop, daemon=True)
        self._thread.start()
        
        logger.info("🔍 L6内省服务已启动")
        self.reporter.report_completed(
            metrics={"service_started": 1},
            confidence=1.0
        )
    
    def stop_background_introspection(self):
        """停止后台内省线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🔍 L6内省服务已停止")
    
    def _introspection_loop(self):
        """内省循环"""
        while self._running:
            try:
                self._perform_introspection()
                time.sleep(self.config['introspection_interval_seconds'])
            except Exception as e:
                logger.error(f"L6内省循环错误: {e}")
                time.sleep(10)
    
    def _perform_introspection(self):
        """执行一次完整的内省"""
        self.stats['total_introspections'] += 1
        
        snapshot = self.collector.get_snapshot()
        
        health = self._assess_health(snapshot)
        self.health_history.append(health)
        
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        self.stats['avg_health_score'] = (
            (self.stats['avg_health_score'] * (self.stats['health_checks'] - 1) + health.overall)
            / max(self.stats['health_checks'], 1)
        )
        self.stats['health_checks'] += 1
        
        new_anomalies = self._detect_anomalies(snapshot, health)
        
        for anomaly in new_anomalies:
            self.anomalies.append(anomaly)
            self.stats['anomalies_detected'] += 1
            logger.warning(
                f"⚠️ [L6] 异常检测: {anomaly.title} "
                f"(严重程度: {anomaly.severity.value})"
            )
        
        if new_anomalies:
            self._trigger_repairs(new_anomalies, snapshot)
        
        self._check_resolved_anomalies(snapshot)
        
        if len(self.health_history) % 10 == 0 or health.get_level() in [SystemHealthLevel.POOR, SystemHealthLevel.CRITICAL]:
            self._log_introspection_summary(health, new_anomalies)
    
    def _assess_health(self, snapshot: SystemSnapshot) -> HealthScore:
        """评估系统健康度"""
        issues = []
        layer_scores = {}
        
        for layer_name, report in snapshot.layer_reports.items():
            health_map = {
                LayerHealth.HEALTHY: 1.0,
                LayerHealth.WARNING: 0.6,
                LayerHealth.CRITICAL: 0.2,
                LayerHealth.UNKNOWN: 0.3,
            }
            base_score = health_map.get(report.health, 0.5)
            
            confidence = report.confidence_score
            layer_score = base_score * (0.7 + 0.3 * confidence)
            
            if report.issues:
                layer_score *= max(0.5, 1 - len(report.issues) * 0.1)
            
            layer_scores[layer_name] = min(1.0, layer_score)
            
            if report.issues:
                issues.extend([f"{layer_name}: {issue}" for issue in report.issues[:2]])
        
        coordination = self._assess_coordination(snapshot)
        
        if layer_scores:
            avg_layer_score = sum(layer_scores.values()) / len(layer_scores)
            overall = avg_layer_score * 0.6 + coordination * 0.4
        else:
            overall = 0.5
        
        trend = self._analyze_trend()
        
        return HealthScore(
            overall=overall,
            layers=layer_scores,
            coordination=coordination,
            trend=trend,
            issues=issues[:5],
            timestamp=datetime.now().isoformat()
        )
    
    def _assess_coordination(self, snapshot: SystemSnapshot) -> float:
        """评估层间协调性"""
        active_layers = list(snapshot.layer_reports.keys())
        expected_layers = ["L0", "L1", "L2", "L3", "L4", "L5"]
        
        active_count = sum(1 for l in expected_layers if l in active_layers)
        completeness = active_count / len(expected_layers)
        
        healthy_count = snapshot.healthy_layers
        total_layers = snapshot.layers_count or 1
        health_ratio = healthy_count / total_layers
        
        confidences = [r.confidence_score for r in snapshot.layer_reports.values()]
        if len(confidences) > 1:
            consistency = 1.0 - (max(confidences) - min(confidences))
            consistency = max(0, consistency)
        else:
            consistency = 0.8
        
        heartbeat_status = []
        for layer in expected_layers:
            status = self.heartbeat.get_layer_status(layer)
            if status in [HeartbeatStatus.ALIVE, HeartbeatStatus.DEGRADED]:
                heartbeat_status.append(1.0)
            else:
                heartbeat_status.append(0.0)
        
        heartbeat_ratio = sum(heartbeat_status) / len(expected_layers) if heartbeat_status else 0.5
        
        coordination = (
            completeness * 0.25 +
            health_ratio * 0.25 +
            consistency * 0.25 +
            heartbeat_ratio * 0.25
        )
        
        return min(1.0, coordination)
    
    def _analyze_trend(self) -> str:
        """分析健康度趋势"""
        if len(self.health_history) < 3:
            return 'stable'
        
        recent = [h.overall for h in self.health_history[-5:]]
        older = [h.overall for h in self.health_history[-10:-5]] if len(self.health_history) >= 10 else recent
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        diff = recent_avg - older_avg
        
        if diff > 0.05:
            return 'improving'
        elif diff < -0.05:
            return 'declining'
        else:
            return 'stable'
    
    def _detect_anomalies(self, snapshot: SystemSnapshot, health: HealthScore) -> List[Anomaly]:
        """检测异常"""
        anomalies = []
        now = datetime.now().isoformat()
        
        if health.overall < self.config['health_thresholds']['poor']:
            if len(self.health_history) > 1:
                prev = self.health_history[-2].overall
                if health.overall < prev - 0.1:
                    anomalies.append(Anomaly(
                        id=f"anom_{datetime.now().strftime('%Y%m%d%H%M%S')}_001",
                        title="系统健康度急剧下降",
                        description=f"整体健康度从 {prev:.2f} 下降至 {health.overall:.2f}",
                        severity=AnomalySeverity.CRITICAL,
                        detected_at=now,
                        related_layers=list(health.layers.keys())
                    ))
        
        for layer_name, score in health.layers.items():
            if score < 0.3:
                if self._is_persistent_issue(layer_name, score):
                    anomalies.append(Anomaly(
                        id=f"anom_{datetime.now().strftime('%Y%m%d%H%M%S')}_{layer_name}",
                        title=f"{layer_name} 进入危急状态",
                        description=f"{layer_name} 健康度降至 {score:.2f}",
                        severity=AnomalySeverity.CRITICAL,
                        detected_at=now,
                        related_layers=[layer_name]
                    ))
            elif score < 0.5:
                anomalies.append(Anomaly(
                    id=f"anom_{datetime.now().strftime('%Y%m%d%H%M%S')}_{layer_name}_warn",
                    title=f"{layer_name} 健康度偏低",
                    description=f"{layer_name} 健康度为 {score:.2f}，需要关注",
                    severity=AnomalySeverity.MAJOR,
                    detected_at=now,
                    related_layers=[layer_name]
                ))
        
        if health.coordination < 0.5:
            anomalies.append(Anomaly(
                id=f"anom_{datetime.now().strftime('%Y%m%d%H%M%S')}_coord",
                title="层间协调性不足",
                description=f"协调性评分: {health.coordination:.2f}",
                severity=AnomalySeverity.MINOR,
                detected_at=now,
                related_layers=[]
            ))
        
        expected_layers = ["L0", "L1", "L2", "L3", "L4", "L5"]
        for layer in expected_layers:
            status = self.heartbeat.get_layer_status(layer)
            if status == HeartbeatStatus.DEAD:
                anomalies.append(Anomaly(
                    id=f"anom_{datetime.now().strftime('%Y%m%d%H%M%S')}_dead_{layer}",
                    title=f"{layer} 失去心跳",
                    description=f"{layer} 已超过 {self.config['anomaly_detection']['layer_dead_threshold_seconds']} 秒无响应",
                    severity=AnomalySeverity.CRITICAL,
                    detected_at=now,
                    related_layers=[layer]
                ))
        
        return anomalies
    
    def _is_persistent_issue(self, layer_name: str, current_score: float) -> bool:
        """检查是否是持续性问题"""
        if len(self.health_history) < 3:
            return True
        
        recent_scores = []
        for h in self.health_history[-5:]:
            if layer_name in h.layers:
                recent_scores.append(h.layers[layer_name])
        
        if len(recent_scores) >= 3:
            low_count = sum(1 for s in recent_scores if s < 0.4)
            return low_count >= 2
        
        return True
    
    def _trigger_repairs(self, anomalies: List[Anomaly], snapshot: SystemSnapshot):
        """触发修复"""
        for anomaly in anomalies:
            if anomaly.severity == AnomalySeverity.CRITICAL:
                self._trigger_critical_repair(anomaly, snapshot)
            elif anomaly.severity == AnomalySeverity.MAJOR:
                self._trigger_major_repair(anomaly, snapshot)
            else:
                self._trigger_minor_repair(anomaly, snapshot)
    
    def _trigger_critical_repair(self, anomaly: Anomaly, snapshot: SystemSnapshot):
        """触发严重修复"""
        self.stats['auto_repairs_triggered'] += 1
        
        if "健康度急剧下降" in anomaly.title:
            for layer_name, report in snapshot.layer_reports.items():
                if report.health == LayerHealth.CRITICAL:
                    self._restart_layer(layer_name)
                    
        elif "失去心跳" in anomaly.title:
            for layer_name in anomaly.related_layers:
                self._restart_layer(layer_name)
        
        anomaly.resolution = f"已触发自动修复 (修复ID: {self.stats['auto_repairs_triggered']})"
        logger.info(f"🔧 [L6] 已触发严重修复: {anomaly.title}")
    
    def _trigger_major_repair(self, anomaly: Anomaly, snapshot: SystemSnapshot):
        """触发重要修复"""
        self.stats['auto_repairs_triggered'] += 1
        
        for layer_name in anomaly.related_layers:
            if layer_name in snapshot.layer_reports:
                self._reduce_layer_load(layer_name)
        
        anomaly.resolution = f"已触发负载调整 (修复ID: {self.stats['auto_repairs_triggered']})"
        logger.info(f"🔧 [L6] 已触发重要修复: {anomaly.title}")
    
    def _trigger_minor_repair(self, anomaly: Anomaly, snapshot: SystemSnapshot):
        """触发轻微修复"""
        anomaly.resolution = "已记录观察，将在下次内省中重新评估"
        logger.info(f"📋 [L6] 已记录观察: {anomaly.title}")
    
    def _restart_layer(self, layer_name: str):
        """重启某层"""
        logger.info(f"🔄 [L6] 正在重启层: {layer_name}")
        self.collector.collect(LayerStateReport(
            layer_name="L6",
            timestamp=datetime.now().isoformat(),
            status=LayerStatus.BUSY,
            health=LayerHealth.HEALTHY,
            metrics={"restarted_layer": layer_name},
            issues=[],
            warnings=[],
            last_operation=f"重启 {layer_name}",
            confidence=0.9
        ))
    
    def _reduce_layer_load(self, layer_name: str):
        """降低某层负载"""
        logger.info(f"📊 [L6] 正在降低层负载: {layer_name}")
        self.collector.collect(LayerStateReport(
            layer_name="L6",
            timestamp=datetime.now().isoformat(),
            status=LayerStatus.RUNNING,
            health=LayerHealth.HEALTHY,
            metrics={"load_reduced": layer_name},
            issues=[],
            warnings=[],
            last_operation=f"降低 {layer_name} 负载",
            confidence=0.8
        ))
    
    def _check_resolved_anomalies(self, snapshot: SystemSnapshot):
        """检查已存在的异常是否已解决"""
        now = datetime.now().isoformat()
        
        for anomaly in self.anomalies:
            if anomaly.resolved_at is not None:
                continue
            
            resolved = False
            
            if "健康度" in anomaly.title:
                current_health = self._assess_health(snapshot)
                if current_health.overall > 0.6:
                    resolved = True
            
            elif "失去心跳" in anomaly.title:
                for layer_name in anomaly.related_layers:
                    status = self.heartbeat.get_layer_status(layer_name)
                    if status in [HeartbeatStatus.ALIVE, HeartbeatStatus.DEGRADED]:
                        resolved = True
                    else:
                        resolved = False
                        break
            
            if resolved:
                anomaly.resolved_at = now
                anomaly.resolution = anomaly.resolution or "已自动恢复"
                self.resolved_anomalies.append(anomaly)
                self.stats['anomalies_resolved'] += 1
                logger.info(f"✅ [L6] 异常已解决: {anomaly.title}")
    
    def _log_introspection_summary(self, health: HealthScore, new_anomalies: List[Anomaly]):
        """记录内省摘要"""
        level = health.get_level()
        summary = (
            f"[L6] 内省报告 | "
            f"健康度: {health.overall:.2f} ({level.value}) | "
            f"趋势: {health.trend} | "
            f"新异常: {len(new_anomalies)} | "
            f"活跃异常: {len([a for a in self.anomalies if a.resolved_at is None])}"
        )
        
        if health.issues:
            summary += f" | 问题: {len(health.issues)}"
        
        logger.info(summary)
        self.stats['last_report_time'] = datetime.now().isoformat()
    
    def generate_report(self) -> IntrospectionReport:
        """生成完整的内省报告"""
        snapshot = self.collector.get_snapshot()
        health = self._assess_health(snapshot)
        
        active_anomalies = [a for a in self.anomalies if a.resolved_at is None]
        
        recommendations = []
        
        if health.overall < 0.5:
            recommendations.append("系统健康度偏低，建议检查各层状态")
        
        for layer_name, score in health.layers.items():
            if score < 0.4:
                recommendations.append(f"{layer_name} 健康度较低 ({score:.2f})，建议重点关注")
        
        if health.coordination < 0.6:
            recommendations.append("层间协调性不足，建议检查心跳和通信机制")
        
        if health.trend == 'declining':
            recommendations.append("系统健康度呈下降趋势，建议排查根本原因")
        
        level = health.get_level()
        summary = f"系统健康度: {level.value} ({health.overall:.2f})"
        if active_anomalies:
            summary += f", 活跃异常: {len(active_anomalies)}个"
        if health.trend == 'improving':
            summary += ", 趋势: 改善中"
        elif health.trend == 'declining':
            summary += ", 趋势: 下降中"
        
        return IntrospectionReport(
            timestamp=datetime.now().isoformat(),
            health=health,
            active_anomalies=active_anomalies,
            recent_changes=self._get_recent_changes(),
            recommendations=recommendations[:5],
            summary=summary
        )
    
    def _get_recent_changes(self) -> List[Dict]:
        """获取最近的变更"""
        changes = []
        
        if len(self.health_history) > 1:
            current = self.health_history[-1]
            previous = self.health_history[-2]
            
            for layer, score in current.layers.items():
                if layer in previous.layers:
                    diff = score - previous.layers[layer]
                    if abs(diff) > 0.05:
                        changes.append({
                            "layer": layer,
                            "change": diff,
                            "direction": "improved" if diff > 0 else "declined",
                            "old_score": previous.layers[layer],
                            "new_score": score
                        })
        
        return changes[:5]
    
    def get_introspection_status(self) -> Dict:
        """获取内省状态"""
        neighbor_status = self.heartbeat.get_neighbor_status("L6")
        
        latest = self.collector.get_latest("L6")
        
        return {
            "layer": "L6",
            "status": latest.status.value if latest else "unknown",
            "stats": self.stats,
            "neighbor_status": {
                k: v.value for k, v in neighbor_status.items()
            },
            "health": {
                "avg": self.stats['avg_health_score'],
                "history_count": len(self.health_history),
                "trend": self._analyze_trend()
            },
            "anomalies": {
                "active": len([a for a in self.anomalies if a.resolved_at is None]),
                "total_detected": self.stats['anomalies_detected'],
                "total_resolved": self.stats['anomalies_resolved']
            },
            "running": self._running
        }


_l6_instance = None

def get_l6_introspection() -> L6IntrospectionLayer:
    global _l6_instance
    if _l6_instance is None:
        _l6_instance = L6IntrospectionLayer()
    return _l6_instance