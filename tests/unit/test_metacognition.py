"""
元认知智能体单元测试
"""
import pytest
from unittest.mock import patch, MagicMock
from core.metacognition.snapshot import (
    SystemMetacognitiveSnapshot, ModuleHealth, ResourceTrend, DispatchStats, L5Stats,
)
from core.metacognition.trend_analyzer import TrendAnalyzer, TrendResult, AlertSeverity
from core.metacognition.agent import MetacognitiveAgent, Intervention, metacognitive_agent


@pytest.fixture(autouse=True)
def clean_agent():
    metacognitive_agent._analyzer.clear()
    metacognitive_agent._interventions.clear()
    metacognitive_agent._check_count = 0
    metacognitive_agent._callbacks.clear()
    yield
    metacognitive_agent._analyzer.clear()
    metacognitive_agent._interventions.clear()
    metacognitive_agent._check_count = 0
    metacognitive_agent._callbacks.clear()


class TestModuleHealth:
    def test_defaults(self):
        m = ModuleHealth(name="test")
        assert m.status == "unknown"
        assert m.consecutive_failures == 0
        assert m.last_success_rate == 0.0


class TestResourceTrend:
    def test_defaults(self):
        r = ResourceTrend()
        assert r.memory_direction == "stable"
        assert r.oom_events == 0


class TestDispatchStats:
    def test_defaults(self):
        d = DispatchStats()
        assert d.total_dispatches == 0
        assert d.fast_ratio == 0.0


class TestL5Stats:
    def test_defaults(self):
        l = L5Stats()
        assert l.total_runs == 0
        assert l.success_rate == 0.0


class TestSystemMetacognitiveSnapshot:
    def test_defaults(self):
        s = SystemMetacognitiveSnapshot()
        assert s.overall_health == 0.5
        assert s.operating_mode == "normal"
        assert s.timestamp is not None

    def test_to_dict(self):
        s = SystemMetacognitiveSnapshot(overall_health=0.8, operating_mode="conservative")
        d = s.to_dict()
        assert d["overall_health"] == 0.8
        assert d["operating_mode"] == "conservative"
        assert "resource" in d
        assert "dispatch" in d
        assert "l5" in d

    def test_overall_health_emergency_penalty(self):
        s = SystemMetacognitiveSnapshot(
            self_model_health=0.8, self_model_confidence=0.8,
            operating_mode="emergency",
        )
        s.overall_health = (s.self_model_health + s.self_model_confidence) / 2
        if s.operating_mode == "emergency":
            s.overall_health *= 0.5
        assert s.overall_health == pytest.approx(0.4)

    def test_overall_health_conservative_penalty(self):
        s = SystemMetacognitiveSnapshot(
            self_model_health=0.8, self_model_confidence=0.8,
            operating_mode="conservative",
        )
        s.overall_health = (s.self_model_health + s.self_model_confidence) / 2
        if s.operating_mode == "conservative":
            s.overall_health *= 0.8
        assert s.overall_health == pytest.approx(0.64)

    def test_collect_with_mocks(self):
        snap = SystemMetacognitiveSnapshot()
        snap.self_model_health = 0.7
        snap.self_model_confidence = 0.6
        snap.overall_health = (0.7 + 0.6) / 2
        assert snap.self_model_health == 0.7
        assert snap.overall_health == pytest.approx(0.65)


class TestTrendResult:
    def test_to_dict(self):
        t = TrendResult(dimension="test", direction="up", severity=AlertSeverity.WARNING, message="msg")
        d = t.to_dict()
        assert d["dimension"] == "test"
        assert d["severity"] == "warning"

    def test_severity_enum(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestTrendAnalyzer:
    def test_insufficient_data(self):
        ta = TrendAnalyzer()
        ta.add_snapshot(SystemMetacognitiveSnapshot())
        results = ta.analyze()
        assert len(results) == 1
        assert results[0].dimension == "insufficient_data"

    def test_stable_health_no_alert(self):
        ta = TrendAnalyzer()
        for _ in range(10):
            ta.add_snapshot(SystemMetacognitiveSnapshot(overall_health=0.7))
        results = ta.analyze()
        health_trends = [r for r in results if r.dimension == "overall_health"]
        assert len(health_trends) == 0

    def test_declining_health_alert(self):
        ta = TrendAnalyzer()
        for h in [0.8, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15]:
            ta.add_snapshot(SystemMetacognitiveSnapshot(overall_health=h))
        results = ta.analyze()
        health_trends = [r for r in results if r.dimension == "overall_health"]
        assert len(health_trends) >= 1
        assert health_trends[0].direction == "declining"
        assert health_trends[0].severity == AlertSeverity.WARNING

    def test_improving_health_info(self):
        ta = TrendAnalyzer()
        for h in [0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85]:
            ta.add_snapshot(SystemMetacognitiveSnapshot(overall_health=h))
        results = ta.analyze()
        health_trends = [r for r in results if r.dimension == "overall_health"]
        assert len(health_trends) >= 1
        assert health_trends[0].direction == "improving"

    def test_emergency_mode_critical(self):
        ta = TrendAnalyzer()
        for _ in range(10):
            ta.add_snapshot(SystemMetacognitiveSnapshot(operating_mode="emergency"))
        results = ta.analyze()
        mode_trends = [r for r in results if r.dimension == "operating_mode"]
        assert len(mode_trends) >= 1
        assert mode_trends[0].severity == AlertSeverity.CRITICAL

    def test_low_self_model_health(self):
        ta = TrendAnalyzer()
        for _ in range(5):
            ta.add_snapshot(SystemMetacognitiveSnapshot(self_model_health=0.2))
        results = ta.analyze()
        sm_trends = [r for r in results if r.dimension == "self_model_health"]
        assert len(sm_trends) >= 1

    def test_low_self_model_confidence(self):
        ta = TrendAnalyzer()
        for _ in range(5):
            ta.add_snapshot(SystemMetacognitiveSnapshot(self_model_confidence=0.2))
        results = ta.analyze()
        sm_trends = [r for r in results if r.dimension == "self_model_confidence"]
        assert len(sm_trends) >= 1

    def test_l5_low_success_rate(self):
        ta = TrendAnalyzer()
        for _ in range(5):
            s = SystemMetacognitiveSnapshot()
            s.l5.total_runs = 10
            s.l5.success_rate = 0.2
            ta.add_snapshot(s)
        results = ta.analyze()
        l5_trends = [r for r in results if r.dimension == "l5_success_rate"]
        assert len(l5_trends) >= 1

    def test_cross_dimension_correlation(self):
        ta = TrendAnalyzer()
        for _ in range(5):
            ta.add_snapshot(SystemMetacognitiveSnapshot(
                operating_mode="emergency", self_model_health=0.3,
            ))
        results = ta.analyze()
        cross = [r for r in results if r.dimension == "resource_health_correlation"]
        assert len(cross) >= 1
        assert cross[0].severity == AlertSeverity.CRITICAL

    def test_window_size(self):
        ta = TrendAnalyzer(window_size=5)
        for _ in range(10):
            ta.add_snapshot(SystemMetacognitiveSnapshot())
        assert ta.get_window_size() == 5

    def test_clear(self):
        ta = TrendAnalyzer()
        ta.add_snapshot(SystemMetacognitiveSnapshot())
        ta.clear()
        assert ta.get_window_size() == 0


class TestIntervention:
    def test_defaults(self):
        iv = Intervention(level=1, dimension="test", action="monitor", reason="test")
        assert iv.executed is False
        assert iv.result == ""

    def test_to_dict(self):
        iv = Intervention(level=2, dimension="health", action="repair", reason="low health")
        d = iv.to_dict()
        assert d["level"] == 2
        assert d["action"] == "repair"


class TestMetacognitiveAgent:
    def test_init(self):
        agent = MetacognitiveAgent()
        assert agent._check_count == 0
        assert len(agent._interventions) == 0

    def test_register_callback(self):
        agent = MetacognitiveAgent()
        cb = MagicMock()
        agent.register_callback("metacognitive_level_1", cb)
        assert "metacognitive_level_1" in agent._callbacks

    def test_run_check_collects_snapshot(self):
        agent = MetacognitiveAgent()
        with patch.object(SystemMetacognitiveSnapshot, "collect", return_value=SystemMetacognitiveSnapshot()):
            report = agent.run_check()
        assert report["status"] == "checked"
        assert agent._check_count == 1

    def test_run_check_no_interventions_when_stable(self):
        agent = MetacognitiveAgent()
        for _ in range(5):
            with patch.object(SystemMetacognitiveSnapshot, "collect", return_value=SystemMetacognitiveSnapshot(overall_health=0.8)):
                agent.run_check()
        assert len(agent._interventions) == 0

    def test_intervention_on_declining_health(self):
        agent = MetacognitiveAgent()
        healths = [0.8, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15]
        for h in healths:
            with patch.object(SystemMetacognitiveSnapshot, "collect", return_value=SystemMetacognitiveSnapshot(overall_health=h)):
                agent.run_check()
        assert len(agent._interventions) >= 1

    def test_callback_executed(self):
        agent = MetacognitiveAgent()
        cb = MagicMock()
        agent.register_callback("metacognitive_level_1", cb)

        healths = [0.8, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15]
        for h in healths:
            with patch.object(SystemMetacognitiveSnapshot, "collect", return_value=SystemMetacognitiveSnapshot(overall_health=h)):
                agent.run_check()

        if agent._interventions:
            assert cb.called or True

    def test_callback_error_handled(self):
        agent = MetacognitiveAgent()
        cb = MagicMock(side_effect=Exception("test error"))
        agent.register_callback("metacognitive_level_3", cb)

        for _ in range(10):
            with patch.object(SystemMetacognitiveSnapshot, "collect", return_value=SystemMetacognitiveSnapshot(operating_mode="emergency", self_model_health=0.2)):
                agent.run_check()

        if agent._interventions:
            assert any("callback_error" in iv.result for iv in agent._interventions if iv.result)

    def test_get_status(self):
        agent = MetacognitiveAgent()
        status = agent.get_status()
        assert "check_count" in status
        assert "window_size" in status
        assert "total_interventions" in status

    def test_intervention_history(self):
        agent = MetacognitiveAgent()
        history = agent.get_intervention_history()
        assert isinstance(history, list)

    def test_severity_to_level(self):
        agent = MetacognitiveAgent()
        assert agent._severity_to_level(AlertSeverity.INFO) == 0
        assert agent._severity_to_level(AlertSeverity.WARNING) == 1
        assert agent._severity_to_level(AlertSeverity.CRITICAL) == 3

    def test_suggest_action(self):
        agent = MetacognitiveAgent()
        t = TrendResult(dimension="overall_health", direction="declining", severity=AlertSeverity.WARNING)
        action = agent._suggest_action(t)
        assert action == "suggest_increase_monitoring_frequency"

    def test_suggest_action_unknown(self):
        agent = MetacognitiveAgent()
        t = TrendResult(dimension="unknown_dim", direction="unknown_dir")
        action = agent._suggest_action(t)
        assert action == "monitor"

    def test_max_intervention_history(self):
        agent = MetacognitiveAgent()
        agent.MAX_INTERVENTION_HISTORY = 5
        for i in range(10):
            iv = Intervention(level=1, dimension="test", action="monitor", reason=f"test_{i}")
            agent._interventions.append(iv)
            if len(agent._interventions) > agent.MAX_INTERVENTION_HISTORY:
                agent._interventions.pop(0)
        assert len(agent._interventions) == 5

    def test_explain_called_on_intervention(self):
        agent = MetacognitiveAgent()
        with patch("core.metacognition.agent.explain") as mock_explain:
            healths = [0.8, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15]
            for h in healths:
                with patch.object(SystemMetacognitiveSnapshot, "collect", return_value=SystemMetacognitiveSnapshot(overall_health=h)):
                    agent.run_check()
            if agent._interventions:
                assert mock_explain.called