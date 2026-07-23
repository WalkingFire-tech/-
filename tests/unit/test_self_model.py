"""
SelfModel P4-2 连续自我机制 单元测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from core.self.model import SelfModel, get_self_model, _SELF_STATE_DB


@pytest.fixture
def self_model():
    return SelfModel()


@pytest.fixture(autouse=True)
def clean_inner_time():
    try:
        from core.presence.inner_time import inner_time_engine
        inner_time_engine.reset()
    except ImportError:
        pass
    yield
    try:
        from core.presence.inner_time import inner_time_engine
        inner_time_engine.reset()
    except ImportError:
        pass


class TestSelfModelRestore:
    def test_restore_from_db_with_saved_state(self, self_model):
        mock_db = MagicMock()
        saved = json.dumps({
            "values": {"principles_count": 5},
            "health": {"score": 0.8},
            "capability_profile": {"overall_strength": 0.6},
            "recent_learning": [{"summary": "test"}],
        })
        mock_db.query_one.return_value = (saved,)
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.return_value = mock_db
            sm = SelfModel()
            assert sm.values.get("principles_count") == 5
            assert sm.health.get("score") == 0.8

    def test_restore_from_db_no_saved_state(self, self_model):
        mock_db = MagicMock()
        mock_db.query_one.return_value = None
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.return_value = mock_db
            sm = SelfModel()
            assert sm.values == {}
            assert sm.health == {}

    def test_restore_graceful_on_db_error(self):
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.side_effect = Exception("DB error")
            sm = SelfModel()
            assert sm.values == {}


class TestSelfModelPersist:
    def test_persist_state_saves_snapshot(self, self_model):
        self_model.health = {"score": 0.9, "confidence": 0.7}
        mock_db = MagicMock()
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.return_value = mock_db
            self_model.persist_state()
            mock_db.execute.assert_called()
            args = mock_db.execute.call_args[0][0]
            assert "INSERT OR REPLACE" in args

    def test_persist_graceful_on_error(self, self_model):
        with patch("infrastructure.database_manager.DatabaseManager") as MockDB:
            MockDB.get.side_effect = Exception("DB error")
            self_model.persist_state()


class TestBehavioralDirective:
    def test_get_behavioral_directive_returns_dict(self, self_model):
        directive = self_model.get_behavioral_directive()
        assert isinstance(directive, dict)
        assert "presence_state" in directive
        assert "inner_time_phase" in directive
        assert "response_pace" in directive
        assert "preferred_depth" in directive
        assert "exploration_drive" in directive
        assert "consolidation_need" in directive
        assert "cognitive_density" in directive
        assert "rhythm_bpm" in directive

    def test_directive_sleeping_state(self, self_model):
        mock_el = MagicMock()
        mock_state = MagicMock()
        mock_state.value = "sleeping"
        mock_el.state = mock_state
        with patch("core.presence.existence_layer.get_existence_layer", return_value=mock_el):
            directive = self_model.get_behavioral_directive()
            assert directive["presence_state"] == "sleeping"
            assert directive["response_pace"] == "slow"
            assert directive["preferred_depth"] == "shallow"
            assert directive["consolidation_need"] >= 0.8
            assert directive["exploration_drive"] <= 0.1

    def test_directive_growing_state(self, self_model):
        mock_el = MagicMock()
        mock_state = MagicMock()
        mock_state.value = "growing"
        mock_el.state = mock_state
        with patch("core.presence.existence_layer.get_existence_layer", return_value=mock_el):
            directive = self_model.get_behavioral_directive()
            assert directive["presence_state"] == "growing"
            assert directive["preferred_depth"] == "deep"
            assert directive["exploration_drive"] >= 0.8

    def test_directive_awake_high_density(self, self_model):
        mock_el = MagicMock()
        mock_state = MagicMock()
        mock_state.value = "awake"
        mock_el.state = mock_state
        mock_it_state = MagicMock()
        mock_it_state.current_phase = "awake"
        mock_it_state.cognitive_density = 2.0
        mock_it_state.rhythm_bpm = 120.0
        with patch("core.presence.existence_layer.get_existence_layer", return_value=mock_el):
            with patch("core.presence.inner_time.inner_time_engine") as mock_it:
                mock_it.get_state.return_value = mock_it_state
                directive = self_model.get_behavioral_directive()
                assert directive["response_pace"] == "fast"
                assert directive["preferred_depth"] == "deep"

    def test_directive_resting_state(self, self_model):
        mock_el = MagicMock()
        mock_state = MagicMock()
        mock_state.value = "resting"
        mock_el.state = mock_state
        with patch("core.presence.existence_layer.get_existence_layer", return_value=mock_el):
            directive = self_model.get_behavioral_directive()
            assert directive["response_pace"] == "slow"
            assert directive["consolidation_need"] >= 0.4

    def test_directive_perceiving_state(self, self_model):
        mock_el = MagicMock()
        mock_state = MagicMock()
        mock_state.value = "perceiving"
        mock_el.state = mock_state
        with patch("core.presence.existence_layer.get_existence_layer", return_value=mock_el):
            directive = self_model.get_behavioral_directive()
            assert directive["preferred_depth"] == "moderate"
            assert directive["exploration_drive"] >= 0.6


class TestEvaluateAndActNewRules:
    def test_consolidate_action_when_sleeping(self, self_model):
        self_model.health = {"score": 0.8}
        self_model.relationship = {"trust": 0.5}
        self_model.evolution = {"progress": 0.5}
        with patch.object(self_model, "get_behavioral_directive") as mock_dir:
            mock_dir.return_value = {
                "presence_state": "sleeping",
                "consolidation_need": 0.8,
                "exploration_drive": 0.1,
                "inner_time_phase": "sleeping",
                "cognitive_density": 0.0,
                "rhythm_bpm": 30.0,
                "response_pace": "slow",
                "preferred_depth": "shallow",
            }
            actions = self_model.evaluate_and_act()
            action_names = [a["action"] for a in actions]
            assert "consolidate_memories" in action_names

    def test_deep_exploration_when_growing(self, self_model):
        self_model.health = {"score": 0.8}
        self_model.relationship = {"trust": 0.5}
        self_model.evolution = {"progress": 0.5}
        with patch.object(self_model, "get_behavioral_directive") as mock_dir:
            mock_dir.return_value = {
                "presence_state": "growing",
                "consolidation_need": 0.1,
                "exploration_drive": 0.9,
                "inner_time_phase": "growing",
                "cognitive_density": 0.3,
                "rhythm_bpm": 50.0,
                "response_pace": "normal",
                "preferred_depth": "deep",
            }
            actions = self_model.evaluate_and_act()
            action_names = [a["action"] for a in actions]
            assert "deep_exploration" in action_names


class TestSelfModelSnapshot:
    def test_snapshot_includes_all_dimensions(self, self_model):
        self_model.values = {"test": 1}
        self_model.health = {"score": 0.5}
        snap = self_model.snapshot()
        assert "values" in snap
        assert "health" in snap
        assert "_meta" in snap
        assert snap["values"]["test"] == 1

    def test_snapshot_meta_has_update_count(self, self_model):
        self_model.update("health", {"score": 0.9})
        snap = self_model.snapshot()
        assert snap["_meta"]["update_count"] == 1


class TestGetSelfModel:
    def test_singleton(self):
        sm1 = get_self_model()
        sm2 = get_self_model()
        assert sm1 is sm2
