"""
趋势分析器 — 跨维度趋势检测与异常识别

分析维度：
1. 资源趋势：内存/CPU/GPU是否持续上升
2. 调度趋势：fast/slow/learning比例是否偏移
3. L5趋势：自修改成功率是否下降
4. 闭环趋势：各模块连续失败次数是否增加
5. 关联分析：资源紧张是否导致调度效率下降

设计原则：
- 基于滑动窗口（最近N个快照）
- 异常检测使用简单规则（非ML），避免引入复杂依赖
- 检测结果通过explain()生成解释
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.metacognition.snapshot import SystemMetacognitiveSnapshot


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TrendResult:
    dimension: str
    direction: str
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "direction": self.direction,
            "severity": self.severity.value,
            "message": self.message,
            "data": self.data,
        }


class TrendAnalyzer:
    """趋势分析器 — 基于滑动窗口的跨维度趋势检测"""

    def __init__(self, window_size: int = 20):
        self._window: List[SystemMetacognitiveSnapshot] = []
        self.window_size = window_size

    def add_snapshot(self, snap: SystemMetacognitiveSnapshot) -> None:
        self._window.append(snap)
        if len(self._window) > self.window_size:
            self._window.pop(0)

    def analyze(self) -> List[TrendResult]:
        if len(self._window) < 3:
            return [TrendResult(dimension="insufficient_data", direction="unknown",
                                severity=AlertSeverity.INFO,
                                message=f"数据不足（{len(self._window)}/3），无法进行趋势分析")]

        results = []
        results.extend(self._analyze_resource_trend())
        results.extend(self._analyze_health_trend())
        results.extend(self._analyze_l5_trend())
        results.extend(self._analyze_cross_dimension())
        return results

    def _analyze_resource_trend(self) -> List[TrendResult]:
        results = []
        healths = [s.overall_health for s in self._window]
        modes = [s.operating_mode for s in self._window]

        if len(healths) >= 5:
            recent = healths[-5:]
            earlier = healths[-10:-5] if len(healths) >= 10 else healths[:len(healths)//2]
            if earlier:
                avg_recent = sum(recent) / len(recent)
                avg_earlier = sum(earlier) / len(earlier)
                delta = avg_recent - avg_earlier

                if delta < -0.15:
                    results.append(TrendResult(
                        dimension="overall_health", direction="declining",
                        severity=AlertSeverity.WARNING,
                        message=f"系统整体健康度持续下降: {avg_earlier:.2f}→{avg_recent:.2f} (Δ={delta:.2f})",
                        data={"earlier_avg": round(avg_earlier, 3), "recent_avg": round(avg_recent, 3)},
                    ))
                elif delta > 0.1:
                    results.append(TrendResult(
                        dimension="overall_health", direction="improving",
                        severity=AlertSeverity.INFO,
                        message=f"系统整体健康度改善: {avg_earlier:.2f}→{avg_recent:.2f}",
                    ))

        emergency_count = sum(1 for m in modes if m == "emergency")
        if emergency_count > len(modes) * 0.4:
            results.append(TrendResult(
                dimension="operating_mode", direction="degrading",
                severity=AlertSeverity.CRITICAL,
                message=f"频繁进入紧急模式({emergency_count}/{len(modes)})，资源持续紧张",
            ))

        return results

    def _analyze_health_trend(self) -> List[TrendResult]:
        results = []
        sm_healths = [s.self_model_health for s in self._window]
        sm_confidences = [s.self_model_confidence for s in self._window]

        if len(sm_healths) >= 5:
            recent_avg = sum(sm_healths[-5:]) / 5
            if recent_avg < 0.3:
                results.append(TrendResult(
                    dimension="self_model_health", direction="low",
                    severity=AlertSeverity.WARNING,
                    message=f"自我模型健康度持续偏低: {recent_avg:.2f}",
                ))

        if len(sm_confidences) >= 5:
            recent_avg = sum(sm_confidences[-5:]) / 5
            if recent_avg < 0.3:
                results.append(TrendResult(
                    dimension="self_model_confidence", direction="low",
                    severity=AlertSeverity.WARNING,
                    message=f"自我模型置信度持续偏低: {recent_avg:.2f}",
                ))

        return results

    def _analyze_l5_trend(self) -> List[TrendResult]:
        results = []
        l5_rates = [s.l5.success_rate for s in self._window if s.l5.total_runs > 0]

        if len(l5_rates) >= 3:
            recent = l5_rates[-3:]
            avg_recent = sum(recent) / len(recent)
            if avg_recent < 0.3:
                results.append(TrendResult(
                    dimension="l5_success_rate", direction="declining",
                    severity=AlertSeverity.WARNING,
                    message=f"L5自修改成功率持续偏低: {avg_recent:.0%}",
                ))

        return results

    def _analyze_cross_dimension(self) -> List[TrendResult]:
        results = []
        if len(self._window) < 5:
            return results

        recent = self._window[-5:]
        resource_stressed = sum(1 for s in recent if s.operating_mode != "normal") >= 3
        health_declining = sum(1 for s in recent if s.self_model_health < 0.4) >= 3

        if resource_stressed and health_declining:
            results.append(TrendResult(
                dimension="resource_health_correlation", direction="correlated_decline",
                severity=AlertSeverity.CRITICAL,
                message="资源紧张与健康度下降同时出现，可能存在因果关联",
                data={"resource_stressed": resource_stressed, "health_declining": health_declining},
            ))

        return results

    def get_window_size(self) -> int:
        return len(self._window)

    def clear(self) -> None:
        self._window.clear()