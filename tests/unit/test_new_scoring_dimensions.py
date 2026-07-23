"""
P1-1: 新评分维度测试 — 集成度 + 自我模型成熟度

验证：
1. PerformanceMetric新增INTEGRATION和SELF_MODEL_MATURITY枚举值
2. 权重总和为1.0
3. _evaluate_metrics返回新维度
4. 集成度基于RuntimeTriggerMonitor统计
5. 自我模型成熟度基于SelfModel.get_maturity_score()
"""
import pytest
from unittest.mock import MagicMock, patch
from core.presence.self_assessment import (
    ContinuousSelfAssessment, PerformanceMetric, AssessmentResult,
)


@pytest.fixture
def assessor():
    return ContinuousSelfAssessment()


class TestNewPerformanceMetrics:
    """新枚举值"""

    def test_integration_metric_exists(self):
        assert PerformanceMetric.INTEGRATION.value == "integration"

    def test_self_model_maturity_metric_exists(self):
        assert PerformanceMetric.SELF_MODEL_MATURITY.value == "self_model_maturity"

    def test_seven_metrics_total(self):
        assert len(PerformanceMetric) == 7


class TestMetricWeights:
    """权重总和为1.0"""

    def test_weights_sum_to_one(self, assessor):
        total = sum(c["weight"] for c in assessor.assessment_criteria.values())
        assert abs(total - 1.0) < 0.001

    def test_integration_weight(self, assessor):
        assert assessor.assessment_criteria[PerformanceMetric.INTEGRATION]["weight"] == 0.10

    def test_maturity_weight(self, assessor):
        assert assessor.assessment_criteria[PerformanceMetric.SELF_MODEL_MATURITY]["weight"] == 0.10

    def test_config_weights_sum_to_one(self, assessor):
        total = sum(assessor.config['metric_weights'].values())
        assert abs(total - 1.0) < 0.001


class TestEvaluateMetricsNewDimensions:
    """_evaluate_metrics返回新维度"""

    def test_returns_integration(self, assessor):
        with patch('core.presence.self_assessment.DatabaseManager'):
            metrics = assessor._evaluate_metrics("test", "response", {}, None)
        assert PerformanceMetric.INTEGRATION.value in metrics
        assert 0.0 <= metrics[PerformanceMetric.INTEGRATION.value] <= 1.0

    def test_returns_self_model_maturity(self, assessor):
        with patch('core.presence.self_assessment.DatabaseManager'):
            metrics = assessor._evaluate_metrics("test", "response", {}, None)
        assert PerformanceMetric.SELF_MODEL_MATURITY.value in metrics
        assert 0.0 <= metrics[PerformanceMetric.SELF_MODEL_MATURITY.value] <= 1.0

    def test_integration_default_when_no_monitor(self, assessor):
        with patch('core.presence.self_assessment.DatabaseManager'):
            metrics = assessor._evaluate_metrics("test", "response", {}, None)
        assert metrics[PerformanceMetric.INTEGRATION.value] == 0.5

    def test_maturity_default_when_no_self_model(self, assessor):
        with patch('core.presence.self_assessment.DatabaseManager'):
            metrics = assessor._evaluate_metrics("test", "response", {}, None)
        assert 0.0 <= metrics[PerformanceMetric.SELF_MODEL_MATURITY.value] <= 1.0

    def test_integration_from_trigger_monitor(self, assessor):
        mock_monitor = MagicMock()
        mock_monitor.get_all_stats.return_value = {
            "trace_with_spirit": {"trigger_count": 5},
            "resonate": {"trigger_count": 3},
            "validate_response": {"trigger_count": 0},
        }
        with patch('core.monitoring.runtime_trigger_monitor.trigger_monitor', mock_monitor):
            with patch('core.presence.self_assessment.DatabaseManager'):
                metrics = assessor._evaluate_metrics("test", "response", {}, None)
        assert metrics[PerformanceMetric.INTEGRATION.value] == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_maturity_from_self_model(self, assessor):
        mock_sm = MagicMock()
        mock_sm.get_maturity_score.return_value = {"overall": 0.75}
        with patch('core.self.model.get_self_model', return_value=mock_sm):
            with patch('core.presence.self_assessment.DatabaseManager'):
                metrics = assessor._evaluate_metrics("test", "response", {}, None)
        assert metrics[PerformanceMetric.SELF_MODEL_MATURITY.value] == 0.75


class TestOverallScoreWithNewDimensions:
    """综合评分包含新维度"""

    def test_overall_score_includes_new_dims(self, assessor):
        with patch('core.presence.self_assessment.DatabaseManager'):
            metrics = assessor._evaluate_metrics("什么是Python?", "Python是解释型编程语言", {}, None)
        overall = assessor._calculate_overall_score(metrics)
        assert 0.0 <= overall <= 1.0
        assert overall > 0.0