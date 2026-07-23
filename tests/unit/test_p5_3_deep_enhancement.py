"""
P5-3 深度增强 单元测试

覆盖：
- P5-3a 因果推理增强：trace_with_spirit + _extract_causal_seeds + _compute_truth_feedback
- P5-3b 可解释性增强：CausalExplainer + DecisionDomain.CAUSAL_REASONING
- P5-3c 记忆真理权重：compute_truth_weight + get_weighted_truths + analogize排序
"""

import pytest
from unittest.mock import MagicMock, patch


# ========== P5-3a 因果推理增强 ==========

class TestTraceWithSpirit:
    def setup_method(self):
        from core.world_model import WorldModel
        self.wm = WorldModel()

    def test_trace_returns_dict(self):
        result = self.wm.trace_with_spirit("测试查询")
        assert isinstance(result, dict)
        assert "resonances" in result
        assert "causal_paths" in result
        assert "deep_trace" in result
        assert "truth_feedback" in result

    def test_trace_resonances_populated(self):
        result = self.wm.trace_with_spirit("失败后为什么无法完成")
        assert isinstance(result["resonances"], list)

    def test_trace_no_spirit_core_graceful(self):
        with patch.dict("sys.modules", {"core.spirit_core": None}):
            result = self.wm.trace_with_spirit("测试")
            assert result["resonances"] == [] or isinstance(result["resonances"], list)

    def test_extract_causal_seeds(self):
        seeds = self.wm._extract_causal_seeds("为什么会出现问题")
        assert isinstance(seeds, list)
        assert len(seeds) > 0
        assert all(s.startswith("intent:") for s in seeds)

    def test_compute_truth_feedback_no_paths(self):
        result = self.wm._compute_truth_feedback([], [])
        assert result["action"] == "none"

    def test_compute_truth_feedback_high_confidence(self):
        paths = [{"score": 0.8, "confidence": 0.8, "path": ["a", "b"]}]
        result = self.wm._compute_truth_feedback([], paths)
        assert result["action"] == "boost_evidence"

    def test_compute_truth_feedback_low_confidence(self):
        paths = [{"score": 0.1, "confidence": 0.1, "path": ["a", "b"]}]
        result = self.wm._compute_truth_feedback([], paths)
        assert result["action"] == "flag_uncertainty"

    def test_compute_truth_feedback_moderate(self):
        paths = [{"score": 0.5, "confidence": 0.5, "path": ["a", "b"]}]
        result = self.wm._compute_truth_feedback([], paths)
        assert result["action"] == "neutral"


class TestWorldModelBasic:
    def setup_method(self):
        from core.world_model import WorldModel
        self.wm = WorldModel()

    def test_add_causal_node(self):
        result = self.wm.add_causal_node("test_node", "test_type", "test content")
        assert result is True

    def test_add_causal_edge(self):
        from core.world_model import CausalEdgeType
        self.wm.add_causal_node("src", "test", "source")
        self.wm.add_causal_node("tgt", "test", "target")
        result = self.wm.add_causal_edge("src", "tgt", CausalEdgeType.CAUSES, 0.7, 0.5)
        assert result is True

    def test_predict_no_data(self):
        result = self.wm.predict({"intent": "nonexistent"})
        assert result.probability < 0.5
        assert result.confidence < 0.3

    def test_get_stats(self):
        stats = self.wm.get_stats()
        assert "node_count" in stats
        assert "edge_count" in stats


# ========== P5-3b 可解释性增强 ==========

class TestCausalExplainer:
    def test_explain_trace_none(self):
        from core.explainability.causal_explainer import CausalExplainer
        result = CausalExplainer.explain_trace(None)
        assert result is None

    def test_explain_trace_empty(self):
        from core.explainability.causal_explainer import CausalExplainer
        result = CausalExplainer.explain_trace({})
        assert isinstance(result, str)

    def test_explain_trace_with_resonance(self):
        from core.explainability.causal_explainer import CausalExplainer
        trace = {
            "resonances": [{"principle": "PURSUE_ESSENCE", "strength": 0.8, "drive_direction": "deep_reasoning"}],
            "deep_trace": None,
            "truth_feedback": {"action": "none", "reason": "no_causal_paths"},
        }
        result = CausalExplainer.explain_trace(trace)
        assert "PURSUE_ESSENCE" in result

    def test_explain_trace_with_deep_trace(self):
        from core.explainability.causal_explainer import CausalExplainer
        trace = {
            "resonances": [],
            "deep_trace": {
                "trigger": "PURSUE_ESSENCE",
                "seed_nodes": ["intent:问题"],
                "best_path": {"path": ["a", "b", "c"], "confidence": 0.75},
                "total_paths_found": 2,
            },
            "truth_feedback": {"action": "boost_evidence", "path_confidence": 0.75},
        }
        result = CausalExplainer.explain_trace(trace)
        assert "PURSUE_ESSENCE" in result or "追求本质" in result

    def test_explain_trace_contradiction(self):
        from core.explainability.causal_explainer import CausalExplainer
        trace = {
            "resonances": [],
            "deep_trace": {
                "trigger": "LOGICAL_SELF_CONSISTENT",
                "contradictions": [{"seed": "x", "success_path": ["a", "b"], "failure_path": ["a", "c"]}],
            },
            "truth_feedback": {"action": "none"},
        }
        result = CausalExplainer.explain_trace(trace)
        assert "LOGICAL_SELF_CONSISTENT" in result or "逻辑自洽" in result

    def test_explain_prediction_none(self):
        from core.explainability.causal_explainer import CausalExplainer
        result = CausalExplainer.explain_prediction(None)
        assert "无" in result

    def test_explain_prediction_dict(self):
        from core.explainability.causal_explainer import CausalExplainer
        pred = {
            "predicted_state": {"outcome": "success"},
            "probability": 0.8,
            "confidence": 0.7,
            "causal_path": ["a", "b"],
        }
        result = CausalExplainer.explain_prediction(pred)
        assert "success" in result

    def test_explain_counterfactual(self):
        from core.explainability.causal_explainer import CausalExplainer
        cf = {
            "actual": {"action": "A", "score": 0.5},
            "counterfactual": {"action": "B", "score": 0.8},
            "would_have_been_better": True,
            "advantage": 0.3,
        }
        result = CausalExplainer.explain_counterfactual(cf)
        assert "B" in result

    def test_explain_sieve_enhanced(self):
        from core.explainability.causal_explainer import CausalExplainer
        checks = {
            "self_consistency": {"score": 0.8, "proposition_count": 3, "detected_contradictions": []},
            "entropy_reduction": {"score": 0.6, "compression_ratio": 0.4, "info_density": 0.3},
        }
        result = CausalExplainer.explain_sieve_enhanced(checks)
        assert "逻辑自洽" in result
        assert "认知降熵" in result


class TestDecisionDomainCausal:
    def test_causal_reasoning_domain_exists(self):
        from core.explainability.explanation_types import DecisionDomain
        assert hasattr(DecisionDomain, "CAUSAL_REASONING")
        assert DecisionDomain.CAUSAL_REASONING.value == "causal_reasoning"


# ========== P5-3c 记忆真理权重 ==========

class TestTruthWeight:
    def setup_method(self):
        from core.truth_accumulator import TruthAccumulator
        self.ta = TruthAccumulator()

    def test_compute_truth_weight_returns_float(self):
        tw = self.ta.compute_truth_weight("我运行在本地Windows机器上")
        assert isinstance(tw, float)
        assert 0.0 <= tw <= 1.0

    def test_compute_truth_weight_nonexistent(self):
        tw = self.ta.compute_truth_weight("nonexistent_truth_xyz")
        assert tw == 0.3

    def test_compute_truth_weight_l4_higher(self):
        tw_l4 = self.ta.compute_truth_weight("我运行在本地Windows机器上")
        assert tw_l4 > 0.3

    def test_get_weighted_truths_returns_list(self):
        results = self.ta.get_weighted_truths(limit=5)
        assert isinstance(results, list)

    def test_get_weighted_truths_has_weight(self):
        results = self.ta.get_weighted_truths(limit=5)
        for r in results:
            assert "truth_weight" in r
            assert 0.0 <= r["truth_weight"] <= 1.0

    def test_get_weighted_truths_sorted(self):
        results = self.ta.get_weighted_truths(limit=5)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["truth_weight"] >= results[i + 1]["truth_weight"]

    def test_analogize_includes_truth_weight(self):
        results = self.ta.analogize("硬件", "串口")
        for r in results:
            assert "truth_weight" in r

    def test_analogize_sorted_by_combined_score(self):
        results = self.ta.analogize("硬件", "串口")
        if len(results) > 1:
            scores = [r["relevance"] * 0.6 + r.get("truth_weight", 0.5) * 0.4 for r in results]
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1]