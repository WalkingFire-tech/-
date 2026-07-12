"""
状态报告系统 - 让系统能够"看见自己"

这是整个自我审查能力的底层基础设施。
每一层都通过这个系统报告自己的状态，
所有状态数据被集中收集、分析、用于决策。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import json
import threading

from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LayerStatus(Enum):
    """层状态"""
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    DEGRADED = "degraded"
    ERROR = "error"
    RECOVERING = "recovering"


class LayerHealth(Enum):
    """层健康度"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class LayerStateReport:
    """
    层状态报告
    
    每一层在处理完任何操作后，都应生成一份报告。
    报告被发送到StateCollector进行汇总。
    """
    
    layer_name: str
    timestamp: str
    status: LayerStatus
    health: LayerHealth
    metrics: Dict[str, float]
    issues: List[str]
    warnings: List[str]
    last_operation: Optional[str] = None
    active_tasks: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    layer_version: str = "v1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于存储和传输）"""
        return {
            "layer": self.layer_name,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "health": self.health.value,
            "metrics": self.metrics,
            "issues": self.issues,
            "warnings": self.warnings,
            "last_operation": self.last_operation,
            "active_tasks": self.active_tasks,
            "confidence": self.confidence_score,
            "layer_version": self.layer_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayerStateReport":
        """从字典恢复"""
        return cls(
            layer_name=data["layer"],
            timestamp=data["timestamp"],
            status=LayerStatus(data["status"]),
            health=LayerHealth(data["health"]),
            metrics=data.get("metrics", {}),
            issues=data.get("issues", []),
            warnings=data.get("warnings", []),
            last_operation=data.get("last_operation"),
            active_tasks=data.get("active_tasks", []),
            confidence_score=data.get("confidence", 1.0),
            layer_version=data.get("layer_version", "v1.0")
        )
    
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.health in (LayerHealth.HEALTHY, LayerHealth.WARNING)
    
    def needs_attention(self) -> bool:
        """是否需要关注"""
        return self.health == LayerHealth.CRITICAL or len(self.issues) > 0


@dataclass
class SystemSnapshot:
    """系统快照 - 所有层的状态汇总"""
    
    timestamp: str
    layer_reports: Dict[str, LayerStateReport]
    overall_health: LayerHealth
    overall_confidence: float
    layers_count: int
    healthy_layers: int
    warning_layers: int
    critical_layers: int
    aggregated_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_health": self.overall_health.value,
            "overall_confidence": self.overall_confidence,
            "layers": {
                name: report.to_dict() 
                for name, report in self.layer_reports.items()
            },
            "summary": {
                "total": self.layers_count,
                "healthy": self.healthy_layers,
                "warning": self.warning_layers,
                "critical": self.critical_layers
            },
            "aggregated_metrics": self.aggregated_metrics
        }
