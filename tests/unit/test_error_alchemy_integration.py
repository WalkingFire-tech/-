"""
ErrorAlchemy接入测试 — 验证chat_orchestrator关键except块的错误炼金集成
"""
import pytest
from unittest.mock import patch, MagicMock
from core.learning.error_alchemy import ErrorAlchemy, AlchemyResult, LearningSignalType


class TestErrorAlchemyCore:
    def test_record_error_returns_id(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(ValueError("test"), context={"phase": "test"})
        assert err_id.startswith("err_")

    def test_alchemize_extracts_signals(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(ValueError("bad value"), context={"phase": "test"})
        result = ea.alchemize(err_id)
        assert isinstance(result, AlchemyResult)
        assert result.gold_extracted
        assert result.lessons_learned > 0

    def test_alchemize_unknown_error_id(self):
        ea = ErrorAlchemy()
        result = ea.alchemize("nonexistent_id")
        assert not result.gold_extracted
        assert result.lessons_learned == 0

    def test_categorize_value_error_as_logic(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(ValueError("x"))
        record = ea.error_records[err_id]
        from core.learning.error_alchemy import ErrorCategory
        assert record.category == ErrorCategory.LOGIC

    def test_categorize_connection_error_as_external(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(ConnectionError("network failure"))
        record = ea.error_records[err_id]
        from core.learning.error_alchemy import ErrorCategory
        assert record.category == ErrorCategory.EXTERNAL

    def test_avoid_pattern_confidence_increases(self):
        ea = ErrorAlchemy()
        err1 = ea.record_error(ValueError("bad"))
        ea.alchemize(err1)
        err2 = ea.record_error(ValueError("bad"))
        result = ea.alchemize(err2)
        avoid_signals = [s for s in result.signals_extracted if s.type == LearningSignalType.AVOID_PATTERN]
        assert len(avoid_signals) > 0
        assert avoid_signals[0].confidence >= 0.4

    def test_retry_strategy_for_resource_error(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(RuntimeError("resource exhausted"), context={"phase": "test"})
        result = ea.alchemize(err_id)
        retry_signals = [s for s in result.signals_extracted if s.type == LearningSignalType.RETRY_STRATEGY]
        assert len(retry_signals) > 0

    def test_fallback_for_external_error(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(ConnectionError("network"), context={"phase": "test"})
        result = ea.alchemize(err_id)
        fallback_signals = [s for s in result.signals_extracted if s.type == LearningSignalType.FALLBACK_OPTION]
        assert len(fallback_signals) > 0

    def test_precondition_for_data_error(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(RuntimeError("data format invalid"), context={"phase": "test"})
        result = ea.alchemize(err_id)
        precondition_signals = [s for s in result.signals_extracted if s.type == LearningSignalType.PRECONDITION]
        assert len(precondition_signals) > 0

    def test_resolve_error(self):
        ea = ErrorAlchemy()
        err_id = ea.record_error(ValueError("test"))
        assert not ea.error_records[err_id].resolved
        ea.resolve_error(err_id, "fixed")
        assert ea.error_records[err_id].resolved
        assert ea.error_records[err_id].resolution == "fixed"

    def test_get_lessons_learned(self):
        ea = ErrorAlchemy()
        ea.record_error(ValueError("a"))
        ea.record_error(ConnectionError("b"))
        lessons = ea.get_lessons_learned()
        assert lessons["total_errors"] == 2
        assert "LOGIC" in lessons["error_categories"] or "logic" in str(lessons["error_categories"])

    def test_export_state(self):
        ea = ErrorAlchemy()
        ea.record_error(ValueError("test"))
        state = ea.export_state()
        assert state["error_count"] == 1
        assert "lessons" in state


class TestAlchemizeErrorHelper:
    def test_helper_records_and_alchemizes(self):
        from backend.services.orchestrator_helpers import alchemize_error
        import backend.services.orchestrator_helpers as helpers
        helpers._error_alchemy_instance = None
        result = alchemize_error(ValueError("helper test"), context={"phase": "unit_test"}, phase="test_phase")
        assert result is not None
        assert result.gold_extracted
        helpers._error_alchemy_instance = None

    def test_helper_returns_none_on_no_gold(self):
        from backend.services.orchestrator_helpers import alchemize_error
        import backend.services.orchestrator_helpers as helpers
        helpers._error_alchemy_instance = None
        result = alchemize_error(Exception("unknown"), context={}, phase="test")
        assert result is None or isinstance(result, AlchemyResult)
        helpers._error_alchemy_instance = None

    def test_helper_survives_bad_error(self):
        from backend.services.orchestrator_helpers import alchemize_error
        import backend.services.orchestrator_helpers as helpers
        helpers._error_alchemy_instance = None
        result = alchemize_error(RuntimeError("weird \x00 error"), context={}, phase="test")
        assert result is None or isinstance(result, AlchemyResult)
        helpers._error_alchemy_instance = None


class TestOrchestratorErrorAlchemyIntegration:
    def test_chat_orchestrator_has_alchemize_import(self):
        import backend.services.chat_orchestrator as co
        assert hasattr(co, '_alchemize_error') or '_alchemize_error' in dir(co)

    def test_all_key_phases_covered(self):
        import inspect
        from backend.services import chat_orchestrator
        source = inspect.getsource(chat_orchestrator)
        expected_phases = [
            "chat_history_init",
            "chat_history_write",
            "CBNR_L1",
            "input_distill",
            "tool_builder_observe",
            "contrib_attribution",
            "probability_field",
            "world_model_counterfactual",
            "debate_arena",
            "L2_cognitive_learning",
            "L3_cognitive_integration",
        ]
        for phase in expected_phases:
            assert phase in source, f"Missing ErrorAlchemy phase: {phase}"