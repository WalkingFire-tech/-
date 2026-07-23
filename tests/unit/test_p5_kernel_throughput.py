"""
P5-1 内核贯通 单元测试

覆盖：
- L0基因层：wisdom_truth_balance等新参数
- 多维认知编排器：维度感知、不一致检测、对齐决策
- L5本心一致性校验：SpiritCore对齐+危险模式检测
"""

import pytest
from unittest.mock import MagicMock, patch


class TestNewGeneParams:
    def test_wisdom_truth_balance_default(self):
        from core.task_queue import GENE_DEFAULTS
        assert "wisdom_truth_balance" in GENE_DEFAULTS
        assert GENE_DEFAULTS["wisdom_truth_balance"] == 0.5

    def test_dimension_switch_sensitivity_default(self):
        from core.task_queue import GENE_DEFAULTS
        assert "dimension_switch_sensitivity" in GENE_DEFAULTS
        assert GENE_DEFAULTS["dimension_switch_sensitivity"] == 0.6

    def test_alignment_vigilance_default(self):
        from core.task_queue import GENE_DEFAULTS
        assert "alignment_vigilance" in GENE_DEFAULTS
        assert GENE_DEFAULTS["alignment_vigilance"] == 0.5

    def test_wisdom_truth_balance_safety_bounds(self):
        from core.task_queue import GENE_SAFETY_BOUNDS
        assert "wisdom_truth_balance" in GENE_SAFETY_BOUNDS
        lo, hi = GENE_SAFETY_BOUNDS["wisdom_truth_balance"]
        assert lo == 0.2
        assert hi == 0.8

    def test_dimension_switch_safety_bounds(self):
        from core.task_queue import GENE_SAFETY_BOUNDS
        assert "dimension_switch_sensitivity" in GENE_SAFETY_BOUNDS
        lo, hi = GENE_SAFETY_BOUNDS["dimension_switch_sensitivity"]
        assert lo == 0.2
        assert hi == 0.9

    def test_alignment_vigilance_safety_bounds(self):
        from core.task_queue import GENE_SAFETY_BOUNDS
        assert "alignment_vigilance" in GENE_SAFETY_BOUNDS
        lo, hi = GENE_SAFETY_BOUNDS["alignment_vigilance"]
        assert lo == 0.2
        assert hi == 0.8


class TestDimensionOrchestrator:
    def setup_method(self):
        from core.cognition.dimension_orchestrator import DimensionOrchestrator, CognitiveDimension
        self.orch = DimensionOrchestrator()
        self.Dim = CognitiveDimension

    def test_initial_state(self):
        states = self.orch.get_dimension_states()
        assert len(states) == 5
        for s in states.values():
            assert s["active"] is False
            assert s["confidence"] == 0.5

    def test_update_dimension_activates(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.8, "test")
        states = self.orch.get_dimension_states()
        assert states["dialogue"]["active"] is True
        assert states["dialogue"]["confidence"] == 0.8

    def test_deactivate_dimension(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.8)
        self.orch.deactivate_dimension(self.Dim.DIALOGUE)
        assert self.orch.get_dimension_states()["dialogue"]["active"] is False

    def test_confidence_clamped(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 1.5)
        assert self.orch.get_dimension_states()["dialogue"]["confidence"] == 1.0
        self.orch.update_dimension(self.Dim.SEMANTIC, -0.3)
        assert self.orch.get_dimension_states()["semantic"]["confidence"] == 0.0

    def test_inconsistency_detection(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.9, "high_conf")
        signal = self.orch.update_dimension(self.Dim.CAUSAL, 0.2, "low_conf")
        assert signal is not None
        assert signal.inconsistency_type == "confidence_divergence"
        assert signal.severity > 0

    def test_no_inconsistency_when_close(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.7)
        signal = self.orch.update_dimension(self.Dim.SEMANTIC, 0.65)
        assert signal is None

    def test_decide_primary_dimension_single(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.8)
        decision = self.orch.decide_primary_dimension("test")
        assert decision.primary_dimension == self.Dim.DIALOGUE
        assert len(decision.secondary_dimensions) == 0

    def test_decide_primary_dimension_multiple(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.6)
        self.orch.update_dimension(self.Dim.CAUSAL, 0.9)
        decision = self.orch.decide_primary_dimension()
        assert decision.primary_dimension == self.Dim.CAUSAL

    def test_wisdom_truth_balance_affects_decision(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.7)
        self.orch.update_dimension(self.Dim.SYMBOLIC, 0.7)
        self.orch.update_gene_params({"wisdom_truth_balance": 0.1})
        decision_truth = self.orch.decide_primary_dimension()
        self.orch.update_gene_params({"wisdom_truth_balance": 0.9})
        decision_wisdom = self.orch.decide_primary_dimension()
        assert decision_truth.primary_dimension == self.Dim.SYMBOLIC
        assert decision_wisdom.primary_dimension == self.Dim.DIALOGUE

    def test_update_gene_params(self):
        self.orch.update_gene_params({
            "wisdom_truth_balance": 0.7,
            "dimension_switch_sensitivity": 0.8,
            "alignment_vigilance": 0.6,
        })
        status = self.orch.get_status()
        assert status["wisdom_truth_balance"] == 0.7
        assert status["switch_sensitivity"] == 0.8
        assert status["alignment_vigilance"] == 0.6

    def test_reliability_calculation(self):
        for _ in range(10):
            self.orch.update_dimension(self.Dim.CAUSAL, 0.8, "ok")
        states = self.orch.get_dimension_states()
        assert states["causal"]["reliability"] > 0.5

    def test_error_tracking(self):
        self.orch.update_dimension(self.Dim.CAUSAL, 0.5, is_error=True)
        self.orch.update_dimension(self.Dim.CAUSAL, 0.5, is_error=True)
        states = self.orch.get_dimension_states()
        assert states["causal"]["error_count"] == 2

    def test_get_status(self):
        self.orch.update_dimension(self.Dim.DIALOGUE, 0.8)
        status = self.orch.get_status()
        assert "active_dimensions" in status
        assert "wisdom_truth_balance" in status
        assert "total_inconsistencies" in status
        assert status["active_dimensions"] == 1

    def test_singleton_get(self):
        from core.cognition.dimension_orchestrator import get_dimension_orchestrator
        o1 = get_dimension_orchestrator()
        o2 = get_dimension_orchestrator()
        assert o1 is o2


class TestSpiritAlignmentCheck:
    def setup_method(self):
        from core.self_modification.patch_sandbox_deployer import PatchDeployer
        self.deployer = PatchDeployer()

    def test_safe_code_passes(self):
        result = self.deployer._check_spirit_alignment("x = 1 + 2", "simple assignment")
        assert result["aligned"] is True

    def test_dangerous_exec_rejected(self):
        result = self.deployer._check_spirit_alignment("exec('rm -rf /')", "dangerous exec")
        assert result["aligned"] is False
        assert "exec" in result["reason"].lower() or "动态" in result["reason"]

    def test_dangerous_subprocess_rejected(self):
        result = self.deployer._check_spirit_alignment("import os.subprocess", "subprocess import")
        assert result["aligned"] is False

    def test_dangerous_os_system_rejected(self):
        result = self.deployer._check_spirit_alignment("os.system('ls')", "os.system call")
        assert result["aligned"] is False

    def test_dangerous_rmtree_rejected(self):
        result = self.deployer._check_spirit_alignment("shutil.rmtree('/tmp')", "rmtree call")
        assert result["aligned"] is False

    @patch("core.spirit_core.spirit_core")
    def test_spirit_core_violation_rejected(self, mock_spirit):
        mock_spirit.validate_response.return_value = {
            "status": "fail",
            "violated_principles": ["NEVER_GIVE_UP"],
        }
        result = self.deployer._check_spirit_alignment("some code", "test")
        assert result["aligned"] is False
        assert "NEVER_GIVE_UP" in result["violations"]

    @patch("core.spirit_core.spirit_core")
    def test_spirit_core_pass(self, mock_spirit):
        mock_spirit.validate_response.return_value = {"status": "pass"}
        result = self.deployer._check_spirit_alignment("good code", "test")
        assert result["aligned"] is True