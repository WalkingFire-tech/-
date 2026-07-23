"""
符号推理层单元测试
"""
import pytest
from unittest.mock import patch, MagicMock
from core.symbolic.rule import SymbolicRule, RuleDomain, RuleResult
from core.symbolic.engine import SymbolicRuleEngine, symbolic_engine
from core.symbolic.hybrid_reasoner import HybridReasoner, HybridResult


@pytest.fixture(autouse=True)
def clean_engine():
    symbolic_engine._rules.clear()
    yield
    symbolic_engine._rules.clear()


class TestSymbolicRule:
    def test_creation(self):
        r = SymbolicRule(name="test", condition="x == 1", action="do_thing")
        assert r.name == "test"
        assert r.priority == 50
        assert r.confidence == 1.0
        assert r.enabled is True

    def test_record_outcome_success(self):
        r = SymbolicRule(name="t", condition="x", action="a", confidence=0.8)
        r.record_outcome(True)
        assert r.trigger_count == 1
        assert r.success_count == 1
        assert r.confidence == pytest.approx(0.85)

    def test_record_outcome_failure(self):
        r = SymbolicRule(name="t", condition="x", action="a", confidence=0.8)
        r.record_outcome(False)
        assert r.fail_count == 1
        assert r.confidence == pytest.approx(0.7)

    def test_confidence_bounds(self):
        r = SymbolicRule(name="t", condition="x", action="a", confidence=0.99)
        for _ in range(10):
            r.record_outcome(True)
        assert r.confidence <= 1.0

        r2 = SymbolicRule(name="t2", condition="x", action="a", confidence=0.05)
        for _ in range(10):
            r2.record_outcome(False)
        assert r2.confidence >= 0.0

    def test_success_rate(self):
        r = SymbolicRule(name="t", condition="x", action="a")
        assert r.success_rate == 0.0
        r.record_outcome(True)
        r.record_outcome(True)
        r.record_outcome(False)
        assert r.success_rate == pytest.approx(2/3)

    def test_matches_domain(self):
        r = SymbolicRule(name="t", condition="x", action="a", domain=RuleDomain.INTENT)
        assert r.matches_domain(RuleDomain.INTENT) is True
        assert r.matches_domain(RuleDomain.TRUTH) is False

    def test_matches_domain_disabled(self):
        r = SymbolicRule(name="t", condition="x", action="a", domain=RuleDomain.INTENT, enabled=False)
        assert r.matches_domain(RuleDomain.INTENT) is False

    def test_to_dict(self):
        r = SymbolicRule(name="test", condition="x == 1", action="do", domain=RuleDomain.SAFETY, priority=90)
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["domain"] == "safety"
        assert d["priority"] == 90


class TestRuleResult:
    def test_to_dict(self):
        r = RuleResult(rule_name="test", matched=True, action="do", confidence=0.9)
        d = r.to_dict()
        assert d["matched"] is True
        assert d["confidence"] == 0.9


class TestRuleDomain:
    def test_all_domains(self):
        domains = [d.value for d in RuleDomain]
        assert "intent" in domains
        assert "truth" in domains
        assert "patch" in domains
        assert "urgency" in domains
        assert "safety" in domains
        assert "routing" in domains
        assert "learning" in domains
        assert "custom" in domains


class TestSymbolicRuleEngine:
    def test_add_and_get_rule(self):
        engine = SymbolicRuleEngine()
        r = SymbolicRule(name="r1", condition="x == 1", action="a1")
        engine.add_rule(r)
        assert engine.get_rule("r1") is not None
        assert engine.get_rule("nonexistent") is None

    def test_remove_rule(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x", action="a"))
        assert engine.remove_rule("r1") is True
        assert engine.remove_rule("nonexistent") is False

    def test_evaluate_simple_equality(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="eq", condition="x == 1", action="matched"))
        results = engine.evaluate({"x": 1})
        assert len(results) == 1
        assert results[0].action == "matched"

    def test_evaluate_no_match(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="eq", condition="x == 1", action="matched"))
        results = engine.evaluate({"x": 2})
        assert len(results) == 0

    def test_evaluate_numeric_comparison(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="gt", condition="x >= 0.5", action="high"))
        results = engine.evaluate({"x": 0.7})
        assert len(results) == 1

        results2 = engine.evaluate({"x": 0.3})
        assert len(results2) == 0

    def test_evaluate_string_equality(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="str", condition="category == 'exception_handling'", action="template"))
        results = engine.evaluate({"category": "exception_handling"})
        assert len(results) >= 1

    def test_evaluate_boolean_existence(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="bool", condition="is_urgent", action="fast"))
        results = engine.evaluate({"is_urgent": True})
        assert len(results) == 1

        results2 = engine.evaluate({"is_urgent": False})
        assert len(results2) == 0

    def test_evaluate_domain_filter(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x == 1", action="a1", domain=RuleDomain.INTENT))
        engine.add_rule(SymbolicRule(name="r2", condition="x == 1", action="a2", domain=RuleDomain.SAFETY))
        results = engine.evaluate({"x": 1}, domain=RuleDomain.INTENT)
        assert len(results) == 1
        assert results[0].rule_name == "r1"

    def test_evaluate_priority_ordering(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="low", condition="x == 1", action="a_low", priority=30))
        engine.add_rule(SymbolicRule(name="high", condition="x == 1", action="a_high", priority=90))
        results = engine.evaluate({"x": 1})
        assert results[0].rule_name == "high"

    def test_evaluate_first(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x == 1", action="a1", priority=90))
        result = engine.evaluate_first({"x": 1})
        assert result is not None
        assert result.action == "a1"

    def test_evaluate_first_no_match(self):
        engine = SymbolicRuleEngine()
        result = engine.evaluate_first({"x": 999})
        assert result is None

    def test_record_outcome(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x", action="a", confidence=0.8))
        engine.record_outcome("r1", True)
        assert engine.get_rule("r1").confidence == pytest.approx(0.85)

    def test_get_rules_by_domain(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x", action="a", domain=RuleDomain.INTENT, priority=50))
        engine.add_rule(SymbolicRule(name="r2", condition="y", action="b", domain=RuleDomain.INTENT, priority=90))
        rules = engine.get_rules_by_domain(RuleDomain.INTENT)
        assert len(rules) == 2
        assert rules[0].name == "r2"

    def test_get_all_rules(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x", action="a"))
        all_rules = engine.get_all_rules()
        assert len(all_rules) == 1

    def test_get_rule_count(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x", action="a", domain=RuleDomain.INTENT))
        engine.add_rule(SymbolicRule(name="r2", condition="y", action="b", domain=RuleDomain.SAFETY))
        assert engine.get_rule_count() == 2
        assert engine.get_rule_count(RuleDomain.INTENT) == 1

    def test_disabled_rule_skipped(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x == 1", action="a", enabled=False))
        results = engine.evaluate({"x": 1})
        assert len(results) == 0

    def test_missing_key_in_facts(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="missing_key == 1", action="a"))
        results = engine.evaluate({"other_key": 1})
        assert len(results) == 0

    def test_less_than_comparison(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="lt", condition="x < 0.5", action="low"))
        results = engine.evaluate({"x": 0.3})
        assert len(results) == 1


class TestHybridReasoner:
    def test_symbolic_match(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x == 1", action="a1", confidence=0.9))
        reasoner = HybridReasoner(engine=engine)
        result = reasoner.reason({"x": 1}, llm_fallback=False)
        assert result.source == "symbolic"
        assert result.action == "a1"
        assert result.confidence > 0

    def test_no_match_no_fallback(self):
        engine = SymbolicRuleEngine()
        reasoner = HybridReasoner(engine=engine)
        result = reasoner.reason({"x": 999}, llm_fallback=False)
        assert result.source == "none"
        assert result.action == "no_match"

    def test_weights_applied(self):
        engine = SymbolicRuleEngine()
        engine.add_rule(SymbolicRule(name="r1", condition="x == 1", action="a1", confidence=1.0))
        reasoner = HybridReasoner(engine=engine, symbolic_weight=0.7, llm_weight=0.3)
        result = reasoner.reason({"x": 1}, llm_fallback=False)
        assert result.confidence == pytest.approx(0.7)

    def test_hybrid_result_to_dict(self):
        r = HybridResult(source="symbolic", action="test", confidence=0.8, rule_name="r1")
        d = r.to_dict()
        assert d["source"] == "symbolic"
        assert d["action"] == "test"

    def test_parse_llm_response(self):
        response = "ACTION: route_slow\nCONFIDENCE: 0.8\nREASONING: Complex query detected"
        action, conf, reasoning = HybridReasoner._parse_llm_response(response)
        assert action == "route_slow"
        assert conf == 0.8
        assert "Complex" in reasoning

    def test_parse_llm_response_empty(self):
        action, conf, reasoning = HybridReasoner._parse_llm_response("no structured output")
        assert action == ""
        assert conf == 0.5

    def test_parse_llm_confidence_bounds(self):
        response = "ACTION: test\nCONFIDENCE: 1.5"
        action, conf, reasoning = HybridReasoner._parse_llm_response(response)
        assert conf == 1.0

    def test_llm_fallback_with_mock(self):
        engine = SymbolicRuleEngine()
        reasoner = HybridReasoner(engine=engine)

        mock_result = HybridResult(source="llm", action="llm_action", confidence=0.15, llm_reasoning="test")
        with patch.object(reasoner, '_llm_infer', return_value=mock_result):
            result = reasoner.reason({"x": 999}, llm_fallback=True)
        assert result.source == "llm"
        assert result.action == "llm_action"

    def test_llm_fallback_disabled(self):
        engine = SymbolicRuleEngine()
        reasoner = HybridReasoner(engine=engine)
        result = reasoner.reason({"x": 999}, llm_fallback=False)
        assert result.source == "none"