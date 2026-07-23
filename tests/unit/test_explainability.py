"""
可解释性模块单元测试
"""
import pytest
from core.explainability.explanation_types import Explanation, ExplanationLevel, DecisionDomain
from core.explainability.decision_explainer import (
    explain, get_explanation, get_recent_explanations, clear_store,
)
from core.explainability.l5_explainer import L5Explainer
from core.explainability.path_explainer import PathExplainer
from core.explainability.truth_explainer import TruthExplainer


@pytest.fixture(autouse=True)
def clean_store():
    clear_store()
    yield
    clear_store()


class TestExplanationTypes:
    def test_explanation_creation(self):
        e = Explanation(
            domain=DecisionDomain.L5_MODIFICATION,
            decision="test",
            outcome=True,
            reasoning="test reason",
        )
        assert e.domain == DecisionDomain.L5_MODIFICATION
        assert e.reasoning == "test reason"
        assert e.inputs == {}
        assert e.timestamp is not None

    def test_summary(self):
        e = Explanation(domain=DecisionDomain.PATH_SELECTION, decision="route", outcome="fast", reasoning="简单意图")
        assert e.summary() == "简单意图"

    def test_details(self):
        e = Explanation(
            domain=DecisionDomain.L5_MODIFICATION,
            decision="auto_approve",
            outcome=True,
            reasoning="置信度足够",
            inputs={"confidence": 0.95},
            alternatives=["manual_approve"],
            trace=[{"action": "检查阈值", "result": "0.95>=0.9"}],
        )
        d = e.details()
        assert "置信度足够" in d
        assert "confidence=0.950" in d
        assert "manual_approve" in d
        assert "检查阈值" in d

    def test_to_dict(self):
        e = Explanation(domain=DecisionDomain.TRUTH_UPGRADE, decision="sieve", outcome="passed", reasoning="ok")
        d = e.to_dict()
        assert d["domain"] == "truth_upgrade"
        assert d["decision"] == "sieve"
        assert d["reasoning"] == "ok"

    def test_format_dict_float(self):
        e = Explanation(
            domain=DecisionDomain.L5_MODIFICATION, decision="t", outcome=True, reasoning="r",
            inputs={"val": 0.123456},
        )
        d = e.details()
        assert "val=0.123" in d

    def test_explanation_level_enum(self):
        assert ExplanationLevel.BRIEF.value == "brief"
        assert ExplanationLevel.DETAILED.value == "detailed"

    def test_decision_domain_enum(self):
        assert DecisionDomain.L5_MODIFICATION.value == "l5_modification"
        assert DecisionDomain.PATH_SELECTION.value == "path_selection"
        assert DecisionDomain.TRUTH_UPGRADE.value == "truth_upgrade"
        assert DecisionDomain.RESOURCE_ALLOCATION.value == "resource_allocation"
        assert DecisionDomain.CURIOSITY_EXPLORATION.value == "curiosity_exploration"


class TestDecisionExplainer:
    def test_explain_creates_and_stores(self):
        e = explain(
            domain=DecisionDomain.L5_MODIFICATION,
            decision="test",
            outcome=True,
            reasoning="test reason",
        )
        assert e._id is not None
        assert e.reasoning == "test reason"

    def test_get_explanation_by_id(self):
        e = explain(domain=DecisionDomain.PATH_SELECTION, decision="route", outcome="fast", reasoning="r")
        found = get_explanation(e._id)
        assert found is not None
        assert found._id == e._id

    def test_get_explanation_not_found(self):
        assert get_explanation("nonexistent") is None

    def test_get_recent_explanations_all(self):
        explain(domain=DecisionDomain.L5_MODIFICATION, decision="a", outcome=True, reasoning="r1")
        explain(domain=DecisionDomain.PATH_SELECTION, decision="b", outcome="fast", reasoning="r2")
        results = get_recent_explanations()
        assert len(results) == 2

    def test_get_recent_explanations_by_domain(self):
        explain(domain=DecisionDomain.L5_MODIFICATION, decision="a", outcome=True, reasoning="r1")
        explain(domain=DecisionDomain.PATH_SELECTION, decision="b", outcome="fast", reasoning="r2")
        results = get_recent_explanations(domain=DecisionDomain.L5_MODIFICATION)
        assert len(results) == 1
        assert results[0].domain == DecisionDomain.L5_MODIFICATION

    def test_get_recent_explanations_limit(self):
        for i in range(5):
            explain(domain=DecisionDomain.L5_MODIFICATION, decision=f"d{i}", outcome=True, reasoning=f"r{i}")
        results = get_recent_explanations(limit=3)
        assert len(results) == 3

    def test_recent_order_is_newest_first(self):
        explain(domain=DecisionDomain.L5_MODIFICATION, decision="first", outcome=True, reasoning="r1")
        explain(domain=DecisionDomain.L5_MODIFICATION, decision="second", outcome=True, reasoning="r2")
        results = get_recent_explanations()
        assert results[0].decision == "second"

    def test_clear_store(self):
        explain(domain=DecisionDomain.L5_MODIFICATION, decision="a", outcome=True, reasoning="r")
        count = clear_store()
        assert count == 1
        assert len(get_recent_explanations()) == 0

    def test_store_ring_buffer(self):
        from core.explainability.decision_explainer import _MAX_STORED
        for i in range(_MAX_STORED + 50):
            explain(domain=DecisionDomain.L5_MODIFICATION, decision=f"d{i}", outcome=True, reasoning=f"r{i}")
        results = get_recent_explanations(limit=2000)
        assert len(results) == _MAX_STORED

    def test_explain_with_all_fields(self):
        e = explain(
            domain=DecisionDomain.L5_MODIFICATION,
            decision="full_test",
            outcome="result",
            reasoning="reason",
            inputs={"a": 1},
            context={"b": 2},
            alternatives=["alt1"],
            trace=[{"action": "step1", "result": "ok"}],
        )
        assert e.inputs == {"a": 1}
        assert e.context == {"b": 2}
        assert e.alternatives == ["alt1"]
        assert len(e.trace) == 1


class TestL5Explainer:
    def test_explain_patch_strategy_template(self):
        e = L5Explainer.explain_patch_strategy(
            strategy="template", category="exception_handling",
            reason="裸except→except Exception", confidence=0.95,
        )
        assert e.outcome == "template"
        assert "模板补丁" in e.reasoning
        assert e.domain == DecisionDomain.L5_MODIFICATION

    def test_explain_patch_strategy_llm(self):
        e = L5Explainer.explain_patch_strategy(
            strategy="llm", category="logic_error",
            reason="模板未匹配，LLM生成补丁", alternatives=["template"],
        )
        assert e.outcome == "llm"
        assert "LLM" in e.reasoning

    def test_explain_patch_strategy_none(self):
        e = L5Explainer.explain_patch_strategy(
            strategy="none", category="unknown", reason="所有策略失败",
        )
        assert e.outcome == "none"
        assert "无可用" in e.reasoning

    def test_explain_patch_strategy_with_library_hit(self):
        e = L5Explainer.explain_patch_strategy(
            strategy="strategy_library", category="exception_handling",
            reason="命中已知策略", strategy_library_hit=True,
        )
        assert "策略库命中" in e.reasoning
        assert any(s["action"] == "策略库查询" for s in e.trace)

    def test_explain_safety_rejection(self):
        e = L5Explainer.explain_safety_rejection(
            file_path="core/test.py", violations=["危险导入os", "eval调用"],
        )
        assert e.outcome == "rejected"
        assert "安全验证未通过" in e.reasoning
        assert "危险导入os" in e.reasoning

    def test_explain_bootstrap_passed(self):
        e = L5Explainer.explain_bootstrap_verification(
            file_path="core/self_modification/loop.py", can_bootstrap=True,
        )
        assert e.outcome == "passed"
        assert "自举验证通过" in e.reasoning

    def test_explain_bootstrap_failed(self):
        e = L5Explainer.explain_bootstrap_verification(
            file_path="core/self_modification/loop.py", can_bootstrap=False,
            errors=["语法错误", "安全检查失败"],
        )
        assert e.outcome == "failed"
        assert "语法错误" in e.reasoning

    def test_explain_world_model_high_risk(self):
        e = L5Explainer.explain_world_model_risk(
            file_path="core/test.py", risk_level="high", improves_outcome=False,
        )
        assert e.outcome == "rejected"
        assert "高风险" in e.reasoning

    def test_explain_world_model_improves(self):
        e = L5Explainer.explain_world_model_risk(
            file_path="core/test.py", risk_level="low", improves_outcome=True,
            confidence_delta=0.1,
        )
        assert e.outcome == "approved"
        assert "改善预期" in e.reasoning

    def test_explain_auto_approve_approved(self):
        e = L5Explainer.explain_auto_approve(
            approved=True, confidence=0.95, threshold=0.9,
            category="exception_handling", auto_approve_categories=["exception_handling"],
        )
        assert e.outcome is True
        assert "0.95" in e.reasoning
        assert "0.90" in e.reasoning

    def test_explain_auto_approve_rejected_category(self):
        e = L5Explainer.explain_auto_approve(
            approved=False, confidence=0.99, threshold=0.95,
            category="logic_error", auto_approve_categories=["exception_handling"],
        )
        assert "不在白名单" in e.reasoning

    def test_explain_auto_approve_rejected_confidence(self):
        e = L5Explainer.explain_auto_approve(
            approved=False, confidence=0.8, threshold=0.9,
            category="exception_handling", auto_approve_categories=["exception_handling"],
        )
        assert "0.80" in e.reasoning
        assert "0.90" in e.reasoning

    def test_explain_auto_approve_self_mod(self):
        e = L5Explainer.explain_auto_approve(
            approved=False, confidence=0.85, threshold=0.9,
            category="exception_handling", is_self_mod=True,
            effective_threshold=1.0, auto_approve_categories=["exception_handling"],
        )
        assert "自修改" in e.reasoning

    def test_explain_deployment_stage_passed(self):
        e = L5Explainer.explain_deployment_stage(
            file_path="core/test.py", stage="sandbox_verify", passed=True,
        )
        assert e.outcome == "passed"
        assert "通过" in e.reasoning

    def test_explain_deployment_stage_failed_rollback(self):
        e = L5Explainer.explain_deployment_stage(
            file_path="core/test.py", stage="inject_100pct", passed=False,
            rollback=True, details="导入验证失败",
        )
        assert "rollback" in e.outcome
        assert "回滚" in e.reasoning

    def test_explain_strategy_evolution_with_adjustments(self):
        e = L5Explainer.explain_strategy_evolution(
            adjustments=[
                {"category": "exception_handling", "direction": "lower_threshold", "old": 0.9, "new": 0.8},
            ],
            current_params={"template_threshold": 0.8},
        )
        assert "1项调整" in e.reasoning

    def test_explain_strategy_evolution_no_adjustments(self):
        e = L5Explainer.explain_strategy_evolution(adjustments=[])
        assert "无调整" in e.reasoning


class TestPathExplainer:
    def test_resource_protection_triggered(self):
        e = PathExplainer.explain_resource_protection(
            triggered=True, memory_usage=0.9, health_score=0.2,
        )
        assert e.outcome == "lightweight"
        assert "资源保护" in e.reasoning

    def test_resource_protection_normal(self):
        e = PathExplainer.explain_resource_protection(
            triggered=False, memory_usage=0.5, health_score=0.8,
        )
        assert e.outcome == "normal"
        assert "资源正常" in e.reasoning

    def test_route_decision_fast(self):
        e = PathExplainer.explain_route_decision(
            route="fast", intent_type="greeting",
        )
        assert e.outcome == "fast"
        assert "简单类型" in e.reasoning

    def test_route_decision_slow(self):
        e = PathExplainer.explain_route_decision(
            route="slow", intent_type="complex_query", complexity=0.8,
        )
        assert "完整认知流程" in e.reasoning

    def test_route_decision_learning(self):
        e = PathExplainer.explain_route_decision(
            route="learning", intent_type="unknown", confidence=0.3, learning_threshold=0.5,
        )
        assert "学习" in e.reasoning

    def test_route_alternatives(self):
        e = PathExplainer.explain_route_decision(route="fast", intent_type="greeting")
        assert "slow" in e.alternatives
        assert "learning" in e.alternatives

    def test_urgency_override(self):
        e = PathExplainer.explain_urgency_override(
            original_route="slow", overridden_route="fast", urgency=0.9,
        )
        assert e.outcome == "fast"
        assert "0.9" in e.reasoning
        assert "覆盖" in e.reasoning

    def test_fast_path_branch_handled(self):
        e = PathExplainer.explain_fast_path_branch(
            intent_type="greeting", handler="direct_reply", handled=True,
        )
        assert "greeting" in e.reasoning

    def test_fast_path_branch_fallback(self):
        e = PathExplainer.explain_fast_path_branch(
            intent_type="unknown", handler="", handled=False,
        )
        assert "降级到慢路径" in e.reasoning


class TestTruthExplainer:
    def test_sieve_result_passed(self):
        e = TruthExplainer.explain_sieve_result(
            truth_name="测试真谛", sieve_name="cross_domain", passed=True,
            details={"domains": 3, "evidence": 5},
        )
        assert e.outcome == "passed"
        assert "跨域普适性" in e.reasoning

    def test_sieve_result_failed(self):
        e = TruthExplainer.explain_sieve_result(
            truth_name="测试真谛", sieve_name="self_consistency", passed=False,
            details={"reason": "包含矛盾词对"},
        )
        assert e.outcome == "failed"
        assert "逻辑自洽性" in e.reasoning
        assert "矛盾词对" in e.reasoning

    def test_upgrade_verdict_eligible(self):
        e = TruthExplainer.explain_upgrade_verdict(
            truth_name="测试真谛", eligible=True, score=1.0,
            checks={
                "cross_domain": {"passed": True},
                "self_consistency": {"passed": True},
                "entropy_reduction": {"passed": True},
                "antifragility": {"passed": True},
            },
        )
        assert e.outcome == "eligible"
        assert "通过全部" in e.reasoning
        assert len(e.trace) == 4

    def test_upgrade_verdict_ineligible(self):
        e = TruthExplainer.explain_upgrade_verdict(
            truth_name="测试真谛", eligible=False, score=0.5,
            checks={
                "cross_domain": {"passed": True},
                "self_consistency": {"passed": False},
                "entropy_reduction": {"passed": True},
                "antifragility": {"passed": False},
            },
        )
        assert e.outcome == "ineligible"
        assert "逻辑自洽性" in e.reasoning
        assert "反脆弱性" in e.reasoning

    def test_upgrade_verdict_seed(self):
        e = TruthExplainer.explain_upgrade_verdict(
            truth_name="种子", eligible=False, score=0.25,
            checks={"cross_domain": {"passed": False}, "self_consistency": {"passed": False},
                    "entropy_reduction": {"passed": True}, "antifragility": {"passed": False}},
            is_seed=True,
        )
        assert "种子真谛" in e.reasoning

    def test_seed_write_passed(self):
        e = TruthExplainer.explain_seed_write(
            truth_name="种子1", passed_sieves=True,
        )
        assert "通过筛子验证" in e.reasoning

    def test_seed_write_failed(self):
        e = TruthExplainer.explain_seed_write(
            truth_name="种子2", passed_sieves=False,
            sieve_details={"cross_domain": {"passed": False}, "self_consistency": {"passed": True}},
        )
        assert "跨域普适性" in e.reasoning
        assert "仍作为种子写入" in e.reasoning