import pytest
import os
import json
from unittest.mock import MagicMock, patch

TEST_DB = "data/test_world_model.db"


@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    from infrastructure.database_manager import DatabaseManager
    inst = DatabaseManager._instances.pop(TEST_DB, None)
    if inst:
        try:
            inst.close()
        except Exception:
            pass
    import time
    time.sleep(0.1)
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass


@pytest.fixture
def wm():
    from core.world_model import WorldModel
    model = WorldModel(db_path=TEST_DB)
    model.learn_from_experience({"intent_type": "greeting", "model_name": "ollama", "success": True, "quality_score": 80})
    model.learn_from_experience({"intent_type": "greeting", "model_name": "rule", "success": False, "quality_score": 30})
    model.learn_from_experience({"intent_type": "analysis", "model_name": "ollama", "success": True, "quality_score": 90})
    return model


class TestGetRelatedNodes:
    def test_returns_neighbors(self, wm):
        related = wm.get_related_nodes("intent:greeting")
        ids = [r["id"] for r in related]
        assert any("method:ollama" in i for i in ids)

    def test_depth_limit(self, wm):
        shallow = wm.get_related_nodes("intent:greeting", max_depth=1)
        deep = wm.get_related_nodes("intent:greeting", max_depth=2)
        assert len(deep) >= len(shallow)

    def test_max_results(self, wm):
        results = wm.get_related_nodes("intent:greeting", max_results=2)
        assert len(results) <= 2

    def test_nonexistent_node(self, wm):
        results = wm.get_related_nodes("intent:nonexistent")
        assert results == []

    def test_includes_depth_info(self, wm):
        results = wm.get_related_nodes("intent:greeting")
        for r in results:
            assert "depth" in r
            assert "relation" in r


class TestSimulate:
    def test_simulate_improvement(self, wm):
        result = wm.simulate(
            {"intent": "greeting"},
            {"action": "ollama"},
            intent="greeting"
        )
        assert "original_prediction" in result
        assert "simulated_prediction" in result
        assert "delta_probability" in result
        assert "risk_level" in result

    def test_simulate_risk_levels(self, wm):
        result = wm.simulate(
            {"intent": "greeting"},
            {"action": "bad_choice"},
            intent="greeting"
        )
        assert result["risk_level"] in ("low", "medium", "high")

    def test_simulate_no_side_effects(self, wm):
        stats_before = wm.get_stats()
        wm.simulate({"intent": "greeting"}, {"action": "test"}, intent="greeting")
        stats_after = wm.get_stats()
        assert stats_before["edge_count"] == stats_after["edge_count"]

    def test_simulate_empty_changes(self, wm):
        result = wm.simulate({"intent": "greeting"}, {}, intent="greeting")
        assert result["delta_probability"] == 0.0 or result["delta_probability"] == 0

    def test_simulate_includes_override_count(self, wm):
        result = wm.simulate({"intent": "greeting"}, {"action": "ollama"}, intent="greeting")
        assert "override_edges_applied" in result
        assert isinstance(result["override_edges_applied"], int)


class TestFindCausalPaths:
    def test_direct_path(self, wm):
        paths = wm.find_causal_paths("intent:greeting", "outcome:success")
        assert isinstance(paths, list)

    def test_no_path(self, wm):
        paths = wm.find_causal_paths("intent:nonexistent", "outcome:impossible")
        assert paths == []

    def test_path_structure(self, wm):
        paths = wm.find_causal_paths("intent:greeting", "outcome:success")
        for p in paths:
            assert "path" in p
            assert "probability" in p
            assert "confidence" in p
            assert "score" in p
            assert "length" in p

    def test_max_results(self, wm):
        paths = wm.find_causal_paths("intent:greeting", "outcome:success")
        assert len(paths) <= 5

    def test_paths_sorted_by_score(self, wm):
        paths = wm.find_causal_paths("intent:greeting", "outcome:success")
        if len(paths) > 1:
            for i in range(len(paths) - 1):
                assert paths[i]["score"] >= paths[i + 1]["score"]


class TestEvaluatePredictionFix:
    def test_exact_match(self, wm):
        assert wm._evaluate_prediction({"outcome": "success"}, {"outcome": "success"}) is True

    def test_chinese_english_match(self, wm):
        assert wm._evaluate_prediction({"outcome": "成功"}, {"outcome": "success"}) is True

    def test_edge_type_no_longer_matches(self, wm):
        assert wm._evaluate_prediction({"outcome": "success", "edge_type": "causes"}, {"outcome": "failure", "edge_type": "causes"}) is False

    def test_different_outcomes(self, wm):
        assert wm._evaluate_prediction({"outcome": "success"}, {"outcome": "failure"}) is False

    def test_substring_match(self, wm):
        assert wm._evaluate_prediction({"outcome": "success"}, {"outcome": "success_partial"}) is True


class TestIndirectEdges:
    def test_indirect_edge_discovery(self, wm):
        wm.add_causal_node("intent:deep", "intent", "deep")
        wm.add_causal_node("method:deep_method", "method", "deep_method")
        wm.add_causal_node("outcome:deep_result", "outcome", "deep_result")
        wm.add_causal_edge("intent:deep", "method:deep_method", probability=0.8, confidence=0.7)
        wm.add_causal_edge("method:deep_method", "outcome:deep_result", probability=0.9, confidence=0.8)

        edges = wm._find_relevant_edges({"intent": "deep"}, "deep")
        targets = [e.target_id for e in edges]
        assert any("deep_method" in t for t in targets)
        indirect = [e for e in edges if "deep_result" in e.target_id]
        if indirect:
            assert indirect[0].probability < 0.9