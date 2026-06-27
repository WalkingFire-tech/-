"""
层状态报告接口 - 为每一层提供便捷的报告方法
"""

from datetime import datetime
from typing import Dict, List, Optional
from core.state_report import LayerStateReport, LayerStatus, LayerHealth
from core.reporting.state_collector import get_state_collector


class LayerReporter:
    """
    层报告器 - 每一层使用此工具报告状态
    
    使用方法:
        reporter = LayerReporter("L1")
        reporter.report_idle()
        reporter.report_busy("处理用户输入")
        reporter.report_completed(metrics={"intent_confidence": 0.92})
        reporter.report_error(["意图理解失败"])
    """
    
    def __init__(self, layer_name: str):
        self.layer_name = layer_name
        self.collector = get_state_collector()
        
        self.collector.register_layer(layer_name)
    
    def report_idle(self, issues: List[str] = None, warnings: List[str] = None):
        """报告空闲状态"""
        self._report(
            status=LayerStatus.IDLE,
            health=LayerHealth.HEALTHY,
            metrics={},
            issues=issues or [],
            warnings=warnings or [],
            last_operation="空闲"
        )
    
    def report_busy(self, operation: str, active_tasks: List[str] = None):
        """报告忙碌状态"""
        self._report(
            status=LayerStatus.BUSY,
            health=LayerHealth.HEALTHY,
            metrics={},
            issues=[],
            warnings=[],
            last_operation=operation,
            active_tasks=active_tasks or [operation]
        )
    
    def report_completed(self, metrics: Dict[str, float], 
                         confidence: float = 1.0,
                         issues: List[str] = None,
                         warnings: List[str] = None):
        """报告操作完成"""
        self._report(
            status=LayerStatus.RUNNING,
            health=LayerHealth.HEALTHY,
            metrics=metrics,
            issues=issues or [],
            warnings=warnings or [],
            last_operation="操作完成",
            confidence=confidence
        )
    
    def report_warning(self, warnings: List[str], 
                       metrics: Dict[str, float] = None):
        """报告警告状态"""
        self._report(
            status=LayerStatus.DEGRADED,
            health=LayerHealth.WARNING,
            metrics=metrics or {},
            issues=[],
            warnings=warnings,
            last_operation="警告状态",
            confidence=0.7
        )
    
    def report_error(self, issues: List[str], 
                     metrics: Dict[str, float] = None):
        """报告错误状态"""
        self._report(
            status=LayerStatus.ERROR,
            health=LayerHealth.CRITICAL,
            metrics=metrics or {},
            issues=issues,
            warnings=[],
            last_operation="错误状态",
            confidence=0.3
        )
    
    def report_health(self, health: LayerHealth, 
                      confidence: float = 1.0,
                      issues: List[str] = None,
                      warnings: List[str] = None):
        """直接报告健康度"""
        self._report(
            status=LayerStatus.RUNNING,
            health=health,
            metrics={},
            issues=issues or [],
            warnings=warnings or [],
            confidence=confidence
        )
    
    def _report(self, status: LayerStatus, health: LayerHealth,
                metrics: Dict[str, float], issues: List[str],
                warnings: List[str], last_operation: str = "",
                active_tasks: List[str] = None,
                confidence: float = 1.0):
        
        report = LayerStateReport(
            layer_name=self.layer_name,
            timestamp=datetime.now().isoformat(),
            status=status,
            health=health,
            metrics=metrics,
            issues=issues,
            warnings=warnings,
            last_operation=last_operation,
            active_tasks=active_tasks or [],
            confidence_score=confidence
        )
        
        self.collector.collect(report)
    
    def receive_feedback(self, feedback: Dict):
        """接收反馈（双向通信）"""
        pass