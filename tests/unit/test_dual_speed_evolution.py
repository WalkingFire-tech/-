"""
单元测试 - 双速进化 (P2-7)
"""
import pytest
from infrastructure.dual_speed_evolution import DualSpeedEvolutionCoordinator, PainSignal


@pytest.fixture
def coordinator():
    return DualSpeedEvolutionCoordinator()


class TestPainSignals:
    def test_record_pain_signal(self, coordinator):
        coordinator.record_pain_signal("test_domain", "test description", 0.7)
        signals = coordinator.get_pain_signals()
        assert len(signals) == 1
        assert signals[0].domain == "test_domain"
        assert signals[0].severity == 0.7

    def test_filter_by_domain(self, coordinator):
        coordinator.record_pain_signal("domain_a", "desc", 0.5)
        coordinator.record_pain_signal("domain_b", "desc", 0.8)
        signals = coordinator.get_pain_signals(domain="domain_a")
        assert len(signals) == 1
        assert signals[0].domain == "domain_a"

    def test_filter_by_severity(self, coordinator):
        coordinator.record_pain_signal("test", "low", 0.2)
        coordinator.record_pain_signal("test", "high", 0.8)
        signals = coordinator.get_pain_signals(min_severity=0.5)
        assert len(signals) == 1
        assert signals[0].severity == 0.8

    def test_clear_signals(self, coordinator):
        coordinator.record_pain_signal("test", "desc", 0.5)
        coordinator.clear_pain_signals()
        assert len(coordinator.get_pain_signals()) == 0

    def test_max_signals_limit(self, coordinator):
        for i in range(150):
            coordinator.record_pain_signal("test", f"signal {i}", 0.5)
        assert len(coordinator.get_pain_signals()) <= 100


class TestFastLoop:
    def test_fast_loop_increments_count(self, coordinator):
        initial = coordinator._fast_loop_count
        coordinator.run_fast_loop(question="test", response="test", fitness_score=50.0)
        assert coordinator._fast_loop_count == initial + 1

    def test_fast_loop_records_pain_on_low_fitness(self, coordinator):
        coordinator.run_fast_loop(question="test q", response="test r", fitness_score=20.0)
        signals = coordinator.get_pain_signals(domain="response_quality")
        assert len(signals) >= 1

    def test_fast_loop_no_pain_on_high_fitness(self, coordinator):
        coordinator.clear_pain_signals()
        coordinator.run_fast_loop(question="test q", response="test r", fitness_score=80.0)
        signals = coordinator.get_pain_signals(domain="response_quality")
        assert len(signals) == 0


class TestSlowLoop:
    def test_slow_loop_increments_count(self, coordinator):
        initial = coordinator._slow_loop_count
        result = coordinator.run_slow_loop()
        assert coordinator._slow_loop_count == initial + 1
        assert "steps" in result

    def test_slow_loop_returns_steps(self, coordinator):
        result = coordinator.run_slow_loop()
        assert "gene_evolution" in result["steps"]
        assert "ratchet_validation" in result["steps"]


class TestStatus:
    def test_get_status(self, coordinator):
        status = coordinator.get_status()
        assert "fast_loop_count" in status
        assert "slow_loop_count" in status
        assert "pain_signal_count" in status