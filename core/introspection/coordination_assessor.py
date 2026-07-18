"""
协调性评估器 + 健康趋势分析

从L6内省层提取的核心能力：
1. 评估系统各模块之间的协调性（完整性、健康比、一致性、心跳比）
2. 分析健康度趋势（improving/stable/declining）
与introspector互补——introspector负责异常检测和自动修复，coordination_assessor负责整体协调性和趋势。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class HealthSnapshot:
    overall: float
    layers: Dict[str, float]
    coordination: float
    trend: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CoordinationAssessor:
    """协调性评估器 + 健康趋势分析"""

    EXPECTED_MODULES = [
        'inner_time', 'existence_layer', 'self_model',
        'knowledge_graph', 'experience_pool', 'rule_engine',
        'chat_orchestrator', 'context_builder', 'response_aggregator',
    ]

    def __init__(self, max_history: int = 100):
        self._history: List[HealthSnapshot] = []
        self._max_history = max_history

    def assess(self, module_reports: Dict[str, Dict]) -> HealthSnapshot:
        """评估系统协调性

        Args:
            module_reports: {module_name: {"health": float, "confidence": float, "issues": List[str]}}

        Returns:
            健康快照
        """
        layer_scores = {}
        for name, report in module_reports.items():
            base = report.get('health', 0.5)
            confidence = report.get('confidence', 0.5)
            issues = report.get('issues', [])
            score = base * (0.7 + 0.3 * confidence)
            if issues:
                score *= max(0.5, 1 - len(issues) * 0.1)
            layer_scores[name] = min(1.0, score)

        coordination = self._compute_coordination(module_reports)

        if layer_scores:
            avg = sum(layer_scores.values()) / len(layer_scores)
            overall = avg * 0.6 + coordination * 0.4
        else:
            overall = 0.5

        trend = self._compute_trend()

        snapshot = HealthSnapshot(
            overall=overall,
            layers=layer_scores,
            coordination=coordination,
            trend=trend,
        )

        self._history.append(snapshot)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return snapshot

    def _compute_coordination(self, module_reports: Dict[str, Dict]) -> float:
        """计算协调性评分

        四维度等权：
        - 完整性：期望模块中有多少在报告
        - 健康比：报告模块中健康的比例
        - 一致性：置信度分布的一致程度
        - 覆盖比：有实际输出的模块比例
        """
        active = set(module_reports.keys())
        expected = set(self.EXPECTED_MODULES)

        completeness = len(active & expected) / len(expected) if expected else 0

        healthy_count = sum(
            1 for r in module_reports.values()
            if r.get('health', 0) >= 0.6
        )
        health_ratio = healthy_count / len(module_reports) if module_reports else 0

        confidences = [r.get('confidence', 0.5) for r in module_reports.values()]
        if len(confidences) > 1:
            consistency = max(0, 1.0 - (max(confidences) - min(confidences)))
        else:
            consistency = 0.8

        productive = sum(
            1 for r in module_reports.values()
            if r.get('productive', False)
        )
        coverage = productive / len(module_reports) if module_reports else 0

        return min(1.0, completeness * 0.25 + health_ratio * 0.25 +
                   consistency * 0.25 + coverage * 0.25)

    def _compute_trend(self) -> str:
        """分析健康度趋势"""
        if len(self._history) < 3:
            return 'stable'

        recent = [h.overall for h in self._history[-5:]]
        older = [h.overall for h in self._history[-10:-5]] if len(self._history) >= 10 else recent

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        diff = recent_avg - older_avg

        if diff > 0.05:
            return 'improving'
        elif diff < -0.05:
            return 'declining'
        return 'stable'

    def get_trend_detail(self) -> Dict:
        """获取趋势详情"""
        if len(self._history) < 2:
            return {'trend': 'stable', 'data_points': len(self._history)}

        recent = [h.overall for h in self._history[-5:]]
        older = [h.overall for h in self._history[-10:-5]] if len(self._history) >= 10 else recent

        return {
            'trend': self._compute_trend(),
            'recent_avg': sum(recent) / len(recent),
            'older_avg': sum(older) / len(older),
            'data_points': len(self._history),
            'coordination_latest': self._history[-1].coordination if self._history else 0,
        }

    def get_stats(self) -> Dict:
        return {
            'total_assessments': len(self._history),
            'latest_overall': self._history[-1].overall if self._history else 0,
            'latest_coordination': self._history[-1].coordination if self._history else 0,
            'trend': self._compute_trend(),
        }


coordination_assessor = CoordinationAssessor()