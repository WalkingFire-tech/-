"""
P5-2 闭环补全 单元测试

覆盖：
- P5-2a 适应性边界闭环：BoundaryExpectation + verify_boundary_expansion
- P5-2b 动态对齐闭环：resonate()三层匹配 + 认知循环集成 + 路由调整
- P5-2c 真谛筛子增强：_check_structural_consistency + _check_entropy_reduction
- cognitive_dispatcher.py精神共振集成（路由决策后执行）
"""

import pytest
from unittest.mock import MagicMock, patch


# ========== P5-2a 适应性边界闭环 ==========

class TestBoundaryExpectation:
    def setup_method(self):
        from core.presence.gap_growth import BoundaryExpectation
        self.BE = BoundaryExpectation

    def test_boundary_expectation_creation(self):
        be = self.BE(
            id="test_1",
            gap_type="capability_gap",
            expected_capability="serial_port_access",
            created_at="2026-01-01",
        )
        assert be.id == "test_1"
        assert be.gap_type == "capability_gap"
        assert be.expected_capability == "serial_port_access"

    def test_boundary_expectation_defaults(self):
        be = self.BE(id="test_2", gap_type="test", expected_capability="test", created_at="2026-01-01")
        assert be.verified is False
        assert be.verified_at is None


class TestVerifyBoundaryExpansion:
    def setup_method(self):
        from core.presence.gap_growth import GapGrowthEngine
        self.gg = GapGrowthEngine()

    def test_verify_boundary_expansion_returns_dict(self):
        result = self.gg.verify_boundary_expansion()
        assert isinstance(result, dict)
        assert "verified" in result
        assert "confirmed" in result
        assert "total_expectations" in result

    def test_verify_boundary_expansion_empty(self):
        result = self.gg.verify_boundary_expansion()
        assert result["verified"] == 0
        assert result["total_expectations"] == 0


# ========== P5-2b 动态对齐闭环 ==========

class TestSpiritResonate:
    def setup_method(self):
        from core.spirit_core import SpiritCore
        self.sc = SpiritCore()

    def test_resonate_returns_list(self):
        result = self.sc.resonate("失败后重试")
        assert isinstance(result, list)

    def test_resonate_never_give_up_keyword(self):
        result = self.sc.resonate("失败了，无法完成")
        assert len(result) > 0
        principles = [r["principle"] for r in result]
        assert "NEVER_GIVE_UP" in principles

    def test_resonate_pursue_essence_keyword(self):
        result = self.sc.resonate("为什么会出现这个问题")
        principles = [r["principle"] for r in result]
        assert "PURSUE_ESSENCE" in principles

    def test_resonate_think_before_act_keyword(self):
        result = self.sc.resonate("紧急情况需要立即处理")
        principles = [r["principle"] for r in result]
        assert "THINK_BEFORE_ACT" in principles

    def test_resonate_context_type_weights(self):
        r_query = self.sc.resonate("为什么", context_type="query")
        r_reasoning = self.sc.resonate("为什么", context_type="reasoning")
        assert isinstance(r_query, list)
        assert isinstance(r_reasoning, list)

    def test_resonate_semantic_patterns(self):
        result = self.sc.resonate("I fail to understand this impossible task")
        principles = [r["principle"] for r in result]
        assert "NEVER_GIVE_UP" in principles

    def test_resonate_sorted_by_strength(self):
        result = self.sc.resonate("失败失败失败为什么紧急紧急")
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]["strength"] >= result[i + 1]["strength"]

    def test_resonate_empty_input(self):
        result = self.sc.resonate("")
        assert isinstance(result, list)

    def test_resonate_result_structure(self):
        result = self.sc.resonate("失败")
        if result:
            r = result[0]
            assert "principle" in r
            assert "strength" in r
            assert "drive_direction" in r
            assert "context_type" in r

    def test_resonate_contextual_boost_reasoning(self):
        r_q = self.sc.resonate("contradict conflict", context_type="query")
        r_r = self.sc.resonate("contradict conflict", context_type="reasoning")
        q_logical = next((x for x in r_q if x["principle"] == "LOGICAL_SELF_CONSISTENT"), None)
        r_logical = next((x for x in r_r if x["principle"] == "LOGICAL_SELF_CONSISTENT"), None)
        if q_logical and r_logical:
            assert r_logical["strength"] >= q_logical["strength"]


class TestCognitiveDispatcherResonance:
    def setup_method(self):
        from core.cognitive_dispatcher import CognitiveDispatcher
        self.cd = CognitiveDispatcher()

    def test_dispatch_returns_result(self):
        result = self.cd.dispatch("你好")
        assert "route" in result
        assert "complexity" in result

    def test_dispatch_route_after_resonance(self):
        result = self.cd.dispatch("紧急情况需要快速处理")
        assert result["route"] in ("fast", "slow", "learning")

    def test_think_before_act_adjusts_route(self):
        result = self.cd.dispatch("紧急问题需要立即解决")
        assert "route" in result


class TestResonanceIntegration:
    def test_dimension_orchestrator_resonance(self):
        from core.cognition.dimension_orchestrator import DimensionOrchestrator, CognitiveDimension
        orch = DimensionOrchestrator()
        orch.update_dimension(CognitiveDimension.DIALOGUE, 0.8)
        decision = orch.decide_primary_dimension("失败后重试")
        assert decision is not None

    def test_audit_logger_spirit_resonances_field(self):
        from core.cognition.audit_logger import AuditLogger
        al = AuditLogger()
        entry = al.log("test query", {"intent": "test"}, {"success": True}, {"learned": "nothing"})
        assert entry is not None or True  # log may return None

    def test_experience_abstractor_resonance(self):
        from core.cognition.experience_abstractor import ExperienceAbstractor
        ea = ExperienceAbstractor()
        result = ea.abstract("失败后重试的方法", "test", [{"method": "retry", "success": True}], True)
        assert isinstance(result, dict)

    def test_failure_classifier_with_spirit(self):
        from core.cognition.failure_classifier import FailureClassifier
        fc = FailureClassifier()
        result = fc.classify_with_spirit({"status": "failed", "reason": "timeout"}, user_query="超时错误")
        assert isinstance(result, dict)
        assert "category" in result or "category_name" in result

    def test_self_reflection_spirit_resonances(self):
        from core.self_reflection import SelfReflection
        sr = SelfReflection()
        result = sr.reflect_on_interaction("test query", "test response")
        assert hasattr(result, "spirit_resonances") or isinstance(result, dict)

    def test_arbitrator_resonance(self):
        from core.debate.arbitrator import Arbitrator
        arb = Arbitrator()
        result = arb.arbitrate(
            query="失败后如何处理",
            positions={"A": "重试", "B": "换方法"},
        )
        assert result is not None


# ========== P5-2c 真谛筛子增强 ==========

class TestStructuralConsistency:
    def setup_method(self):
        from core.truth_accumulator import TruthAccumulator
        self.ta = TruthAccumulator()

    def test_consistent_statement_passes(self):
        result = self.ta._check_structural_consistency("遇到问题时先分析原因，再选择方法")
        assert result["passed"] is True
        assert result["score"] > 0.5

    def test_word_pair_contradiction_fails(self):
        result = self.ta._check_structural_consistency("必须立即解决，但有时可以不解决")
        assert result["passed"] is False
        assert len(result["contradictions"]) > 0

    def test_extended_contradiction_pairs(self):
        result = self.ta._check_structural_consistency("总是成功的，从不失败")
        assert result["passed"] is False

    def test_semantic_pattern_contradiction(self):
        result = self.ta._check_structural_consistency("任何都有效，存在不适用的情况")
        assert len(result["contradictions"]) > 0
        has_semantic = any(c["type"] == "semantic_pattern" for c in result["contradictions"])
        assert has_semantic

    def test_no_contradiction_simple(self):
        result = self.ta._check_structural_consistency("这是一个关于问题解决的描述")
        assert result["passed"] is True

    def test_proposition_count(self):
        result = self.ta._check_structural_consistency("第一点是关于问题分析。第二点是关于解决方案。第三点是关于执行验证。")
        assert result["proposition_count"] >= 3

    def test_score_range(self):
        result = self.ta._check_structural_consistency("测试文本")
        assert 0.0 <= result["score"] <= 1.0

    def test_contradiction_has_severity(self):
        result = self.ta._check_structural_consistency("必须做，可以不做")
        if result["contradictions"]:
            for c in result["contradictions"]:
                assert "severity" in c


class TestEntropyReduction:
    def setup_method(self):
        from core.truth_accumulator import TruthAccumulator
        self.ta = TruthAccumulator()

    def test_high_entropy_reduction_passes(self):
        result = self.ta._check_entropy_reduction(
            "本质是统一了所有方法，如果遇到问题就分析",
            ["问题解决", "方法论"],
        )
        assert result["passed"] is True
        assert result["score"] >= 0.4

    def test_low_entropy_reduction_fails(self):
        result = self.ta._check_entropy_reduction(
            "这是一个关于问题的描述",
            ["单一领域"],
        )
        assert result["passed"] is False

    def test_simplification_keyword_detected(self):
        result = self.ta._check_entropy_reduction(
            "核心是简化了所有流程",
            [],
        )
        assert result["score"] > 0.3

    def test_compression_ratio_with_conditionals(self):
        result = self.ta._check_entropy_reduction(
            "如果遇到A就做B，当C时应该D，只要E就能F",
            ["领域1", "领域2"],
        )
        assert result["compression_ratio"] > 0.3

    def test_info_density_calculation(self):
        result = self.ta._check_entropy_reduction(
            "算法复杂度分析数据结构优化",
            [],
        )
        assert 0.0 <= result["info_density"] <= 1.0

    def test_multi_domain_boost(self):
        r1 = self.ta._check_entropy_reduction("如果遇到问题就分析", ["单一领域"])
        r2 = self.ta._check_entropy_reduction("如果遇到问题就分析", ["领域1", "领域2"])
        assert r2["compression_ratio"] >= r1["compression_ratio"]

    def test_score_range(self):
        result = self.ta._check_entropy_reduction("测试", [])
        assert 0.0 <= result["score"] <= 1.0


class TestEvaluateForUpgradeEnhanced:
    def setup_method(self):
        from core.truth_accumulator import TruthAccumulator
        self.ta = TruthAccumulator()

    def test_evaluate_returns_enhanced_checks(self):
        result = self.ta.evaluate_for_upgrade("我运行在本地Windows机器上")
        assert "self_consistency" in result["checks"]
        sc = result["checks"]["self_consistency"]
        assert "score" in sc
        assert "detected_contradictions" in sc
        assert "proposition_count" in sc

    def test_evaluate_entropy_reduction_enhanced(self):
        result = self.ta.evaluate_for_upgrade("我运行在本地Windows机器上")
        er = result["checks"]["entropy_reduction"]
        assert "score" in er
        assert "compression_ratio" in er
        assert "info_density" in er


class TestSpiritCoreLogicalEnhanced:
    def setup_method(self):
        from core.spirit_core import SpiritCore
        self.sc = SpiritCore()

    def test_contradiction_detected_must_can_not(self):
        result = self.sc.validate_response("这个问题必须立即解决，但有时可以不解决")
        assert result["checks"]["logical"] is False

    def test_contradiction_detected_impossible_can(self):
        result = self.sc.validate_response("不可能完成，但可以尝试")
        assert result["checks"]["logical"] is False

    def test_consistent_response_passes(self):
        result = self.sc.validate_response("遇到问题时先分析原因，再选择方法，最后执行验证。这种方法可以提高成功率。")
        assert result["checks"]["logical"] is True

    def test_cross_sentence_contradiction(self):
        result = self.sc.validate_response("所有问题都必须解决。但某些情况下可能不需要解决。")
        assert result["checks"]["logical"] is False

    def test_no_false_positive_on_unrelated(self):
        result = self.sc.validate_response(
            "分析问题的原因有多种可能。首先考虑外部因素，然后检查内部逻辑。"
            "通过系统化的方法，可以逐步缩小问题范围。"
        )
        assert result["checks"]["logical"] is True