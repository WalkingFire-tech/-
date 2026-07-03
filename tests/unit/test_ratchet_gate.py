"""
单元测试 - 棘轮门 (P2-7)
"""
import pytest
import os
import tempfile
from infrastructure.ratchet_gate import RatchetGate


@pytest.fixture
def gate():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    g = RatchetGate(db_path=db_path)
    yield g
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestRatchetGateValidation:
    def test_approve_improvement(self, gate):
        decision = gate.validate(0.9, "test_approve")
        assert decision.approved is True

    def test_reject_regression(self, gate):
        decision = gate.validate(0.1, "test_reject")
        assert decision.approved is False

    def test_tolerate_minor_regression(self, gate):
        level = gate.get_ratchet_level("test_minor")
        decision = gate.validate(level - 0.01, "test_minor")
        assert decision.approved is True

    def test_baseline_default(self, gate):
        level = gate.get_ratchet_level("nonexistent_domain_xyz")
        assert 0.0 <= level <= 1.0


class TestRatchetGateStats:
    def test_get_stats(self, gate):
        stats = gate.get_stats()
        assert "baselines" in stats
        assert "total_approved" in stats
        assert "total_rejected" in stats
