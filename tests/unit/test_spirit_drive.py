"""
P4-3 SpiritCore驱动层进化 单元测试
"""
import pytest
from core.spirit_core import SpiritCore, spirit_core
from core.metacognition.agent import MetacognitiveAgent
from core.presence.curiosity_engine import CuriosityEngine


class TestSpiritCoreResonate:
    def test_resonate_returns_list(self):
        result = spirit_core.resonate("为什么这个程序会失败？")
        assert isinstance(result, list)

    def test_resonate_pursue_essence(self):
        result = spirit_core.resonate("为什么底层原理是这样的？")
        assert len(result) > 0
        principles = [r["principle"] for r in result]
        assert "PURSUE_ESSENCE" in principles

    def test_resonate_never_give_up(self):
        result = spirit_core.resonate("这个任务失败了无法完成")
        principles = [r["principle"] for r in result]
        assert "NEVER_GIVE_UP" in principles or "LEARNING_FROM_FAILURE" in principles

    def test_resonate_honest_when_lost(self):
        result = spirit_core.resonate("这个问题的答案可能是不确定的")
        principles = [r["principle"] for r in result]
        assert "HONEST_WHEN_LOST" in principles

    def test_resonate_think_before_act(self):
        result = spirit_core.resonate("紧急情况需要立即处理")
        principles = [r["principle"] for r in result]
        assert "THINK_BEFORE_ACT" in principles

    def test_resonate_no_match(self):
        result = spirit_core.resonate("今天天气不错")
        assert isinstance(result, list)

    def test_resonate_sorted_by_strength(self):
        result = spirit_core.resonate("为什么失败的原因是什么底层原理")
        if len(result) > 1:
            assert result[0]["strength"] >= result[1]["strength"]

    def test_resonate_has_drive_direction(self):
        result = spirit_core.resonate("为什么会失败")
        for r in result:
            assert "drive_direction" in r
            assert "drive_description" in r
            assert "strength" in r

    def test_resonate_context_type(self):
        result = spirit_core.resonate("测试", context_type="reasoning")
        for r in result:
            assert r["context_type"] == "reasoning"

    def test_resonate_empty_context(self):
        result = spirit_core.resonate("")
        assert isinstance(result, list)

    def test_resonance_strings_defined(self):
        assert len(SpiritCore.RESONANCE_STRINGS) == 9
        for key, val in SpiritCore.RESONANCE_STRINGS.items():
            assert "trigger_keywords" in val
            assert "drive_direction" in val
            assert "drive_description" in val


class TestMetacognitiveStagnation:
    def test_record_fingerprint(self):
        agent = MetacognitiveAgent()
        agent.record_reasoning_fingerprint("coding", "slow", "ollama", 0.8)
        assert len(agent._reasoning_fingerprints) == 1

    def test_detect_stagnation_insufficient_data(self):
        agent = MetacognitiveAgent()
        result = agent.detect_stagnation()
        assert result["stagnation_detected"] is False
        assert result["reason"] == "insufficient_data"

    def test_detect_stagnation_no_stagnation(self):
        agent = MetacognitiveAgent()
        for i, (intent, route, source) in enumerate([
            ("coding", "slow", "ollama"),
            ("chat", "fast", "experience"),
            ("reasoning", "slow", "knowledge"),
            ("coding", "fast", "ollama"),
            ("chat", "slow", "self_reason"),
        ]):
            agent.record_reasoning_fingerprint(intent, route, source, 0.7)
        result = agent.detect_stagnation(window=5)
        assert result["stagnation_detected"] is False

    def test_detect_stagnation_repetitive(self):
        agent = MetacognitiveAgent()
        for _ in range(10):
            agent.record_reasoning_fingerprint("coding", "fast", "experience", 0.8)
        result = agent.detect_stagnation(window=10)
        assert result["stagnation_detected"] is True
        assert result["stagnation_score"] > 0.8
        assert "perturbation" in result

    def test_stagnation_perturbation_force_deep(self):
        agent = MetacognitiveAgent()
        for _ in range(10):
            agent.record_reasoning_fingerprint("chat", "fast", "experience", 0.9)
        result = agent.detect_stagnation(window=10)
        if result["stagnation_detected"]:
            assert result["perturbation"]["action"] == "force_deep_path"

    def test_fingerprint_max_size(self):
        agent = MetacognitiveAgent()
        for i in range(60):
            agent.record_reasoning_fingerprint("test", "slow", "source", 0.5)
        assert len(agent._reasoning_fingerprints) == 50


class TestCuriosityFrontier:
    def test_perceive_frontier_returns_dict(self):
        engine = CuriosityEngine()
        result = engine.perceive_frontier()
        assert isinstance(result, dict)
        assert "mastery_score" in result
        assert "gap_count" in result
        assert "frontier_density" in result
        assert "curiosity_strength" in result
        assert "exploration_direction" in result

    def test_frontier_values_in_range(self):
        engine = CuriosityEngine()
        result = engine.perceive_frontier()
        assert 0 <= result["mastery_score"] <= 1
        assert 0 <= result["frontier_density"] <= 1
        assert 0 <= result["curiosity_strength"] <= 1

    def test_frontier_direction_is_valid(self):
        engine = CuriosityEngine()
        result = engine.perceive_frontier()
        assert result["exploration_direction"] in ("expand_boundary", "deepen_understanding", "consolidate")