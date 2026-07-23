"""
StrategyEvolver 策略进化器测试
"""
import pytest
from unittest.mock import patch, MagicMock
from core.self_modification.strategy_evolver import StrategyEvolver, StrategyParams, CategoryStats


class TestStrategyParams:
    def test_defaults(self):
        p = StrategyParams()
        assert p.template_threshold == 0.9
        assert p.llm_threshold == 0.95
        assert p.auto_approve_categories == ["exception_handling"]
        assert p.self_mod_confidence_bonus == -0.1
        assert p.min_samples_for_adjustment == 5
        assert p.max_adjustment_per_cycle == 0.1

    def test_custom_values(self):
        p = StrategyParams(template_threshold=0.8, llm_threshold=0.85, self_mod_confidence_bonus=0.0)
        assert p.template_threshold == 0.8
        assert p.llm_threshold == 0.85
        assert p.self_mod_confidence_bonus == 0.0


class TestCategoryStats:
    def test_defaults(self):
        s = CategoryStats(category="test")
        assert s.total == 0
        assert s.success == 0
        assert s.failed == 0
        assert s.success_rate == 0.0
        assert s.self_mod_total == 0
        assert s.self_mod_success == 0

    def test_success_rate_calculation(self):
        s = CategoryStats(category="test", total=10, success=7, failed=3)
        s.success_rate = s.success / s.total
        assert s.success_rate == 0.7


class TestStrategyEvolverInit:
    def test_default_init(self):
        evolver = StrategyEvolver()
        assert evolver.db_path == "data/l5_audit.db"
        assert isinstance(evolver.params, StrategyParams)
        assert evolver._adjustment_history == []

    def test_custom_db_path(self):
        evolver = StrategyEvolver(db_path="/tmp/test_audit.db")
        assert evolver.db_path == "/tmp/test_audit.db"


class TestGetEffectiveConfidence:
    def test_normal_confidence(self):
        evolver = StrategyEvolver()
        assert evolver.get_effective_confidence(0.9, "exception_handling") == 0.9

    def test_self_mod_penalty(self):
        evolver = StrategyEvolver()
        result = evolver.get_effective_confidence(0.9, "exception_handling", is_self_mod=True)
        assert result == pytest.approx(0.8)

    def test_clamp_to_zero(self):
        evolver = StrategyEvolver()
        result = evolver.get_effective_confidence(0.05, "exception_handling", is_self_mod=True)
        assert result == 0.0

    def test_clamp_to_one(self):
        evolver = StrategyEvolver()
        evolver.params.self_mod_confidence_bonus = 0.2
        result = evolver.get_effective_confidence(0.95, "exception_handling", is_self_mod=True)
        assert result == 1.0


class TestShouldAutoApprove:
    def test_auto_approve_exception_handling_high_confidence(self):
        evolver = StrategyEvolver()
        assert evolver.should_auto_approve(0.95, "exception_handling") is True

    def test_no_auto_approve_unknown_category(self):
        evolver = StrategyEvolver()
        assert evolver.should_auto_approve(0.99, "unknown_category") is False

    def test_no_auto_approve_low_confidence(self):
        evolver = StrategyEvolver()
        assert evolver.should_auto_approve(0.5, "exception_handling") is False

    def test_self_mod_higher_threshold(self):
        evolver = StrategyEvolver()
        assert evolver.should_auto_approve(0.9, "exception_handling", is_self_mod=False) is True
        assert evolver.should_auto_approve(0.9, "exception_handling", is_self_mod=True) is False


class TestEvolveModificationStrategy:
    def test_no_data_returns_no_data(self):
        evolver = StrategyEvolver()
        with patch.object(evolver, '_analyze_history', return_value=[]):
            report = evolver.evolve_modification_strategy()
        assert report["status"] == "no_data"

    def test_high_success_rate_lowers_threshold(self):
        evolver = StrategyEvolver()
        stats = [CategoryStats(category="exception_handling", total=10, success=9, failed=1, success_rate=0.9)]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                report = evolver.evolve_modification_strategy()
        assert report["status"] == "adjusted"
        assert any(a["direction"] == "lower_threshold" for a in report["adjustments"])
        assert evolver.params.template_threshold < 0.9

    def test_low_success_rate_raises_threshold(self):
        evolver = StrategyEvolver()
        stats = [CategoryStats(category="logic_error", total=10, success=3, failed=7, success_rate=0.3)]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                report = evolver.evolve_modification_strategy()
        assert report["status"] == "adjusted"
        assert any(a["direction"] == "raise_threshold" for a in report["adjustments"])
        assert evolver.params.llm_threshold > 0.95

    def test_insufficient_samples_no_adjustment(self):
        evolver = StrategyEvolver()
        stats = [CategoryStats(category="exception_handling", total=3, success=3, failed=0, success_rate=1.0)]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                report = evolver.evolve_modification_strategy()
        assert report["status"] == "no_change"

    def test_self_mod_bonus_adjustment(self):
        evolver = StrategyEvolver()
        stats = [CategoryStats(
            category="exception_handling", total=10, success=8, failed=2, success_rate=0.8,
            self_mod_total=5, self_mod_success=4,
        )]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                report = evolver.evolve_modification_strategy()
        assert evolver.params.self_mod_confidence_bonus > -0.1

    def test_threshold_floor_at_07(self):
        evolver = StrategyEvolver()
        evolver.params.template_threshold = 0.71
        stats = [CategoryStats(category="exception_handling", total=10, success=9, failed=1, success_rate=0.9)]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                evolver.evolve_modification_strategy()
        assert evolver.params.template_threshold >= 0.7

    def test_threshold_ceiling_at_10(self):
        evolver = StrategyEvolver()
        evolver.params.llm_threshold = 0.96
        stats = [CategoryStats(category="logic_error", total=10, success=2, failed=8, success_rate=0.2)]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                evolver.evolve_modification_strategy()
        assert evolver.params.llm_threshold <= 1.0

    def test_adjustment_history_recorded(self):
        evolver = StrategyEvolver()
        stats = [CategoryStats(category="exception_handling", total=10, success=9, failed=1, success_rate=0.9)]
        with patch.object(evolver, '_analyze_history', return_value=stats):
            with patch.object(evolver, '_update_priority_files', return_value=[]):
                evolver.evolve_modification_strategy()
        assert len(evolver._adjustment_history) == 1
        assert "timestamp" in evolver._adjustment_history[0]


class TestAnalyzeHistory:
    def test_db_error_returns_empty(self):
        evolver = StrategyEvolver()
        with patch("infrastructure.database_manager.DatabaseManager", side_effect=Exception("no db")):
            result = evolver._analyze_history()
        assert result == []

    def test_dict_rows_parsed(self):
        evolver = StrategyEvolver()
        mock_db = MagicMock()
        mock_db.query.return_value = [
            {"defect_category": "exception_handling", "result_status": "completed", "patch_confidence": 0.9, "is_self_modification": 0},
            {"defect_category": "exception_handling", "result_status": "failed", "patch_confidence": 0.7, "is_self_modification": 1},
            {"defect_category": "logic_error", "result_status": "completed", "patch_confidence": 0.85, "is_self_modification": 0},
        ]
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.return_value = mock_db
            result = evolver._analyze_history()
        assert len(result) == 2
        eh = next(s for s in result if s.category == "exception_handling")
        assert eh.total == 2
        assert eh.success == 1
        assert eh.self_mod_total == 1

    def test_tuple_rows_parsed(self):
        evolver = StrategyEvolver()
        mock_db = MagicMock()
        mock_db.query.return_value = [
            ("exception_handling", "sandbox_passed", 0.88, 0),
        ]
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.return_value = mock_db
            result = evolver._analyze_history()
        assert len(result) == 1
        assert result[0].category == "exception_handling"
        assert result[0].success == 1


class TestThresholdMapping:
    def test_exception_handling_uses_template(self):
        evolver = StrategyEvolver()
        assert evolver._get_threshold_for_category("exception_handling") == evolver.params.template_threshold

    def test_other_uses_llm(self):
        evolver = StrategyEvolver()
        assert evolver._get_threshold_for_category("logic_error") == evolver.params.llm_threshold

    def test_set_template_threshold(self):
        evolver = StrategyEvolver()
        evolver._set_threshold_for_category("exception_handling", 0.8)
        assert evolver.params.template_threshold == 0.8

    def test_set_llm_threshold(self):
        evolver = StrategyEvolver()
        evolver._set_threshold_for_category("logic_error", 0.88)
        assert evolver.params.llm_threshold == 0.88