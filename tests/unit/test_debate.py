"""
P4-4 多智能体辩论 单元测试
"""
import pytest
import asyncio
from core.debate.arena import DebateArena, DebateResult
from core.debate.personas import Persona, PRAGMATIST, IDEALIST, SKEPTIC, ALL_PERSONAS
from core.debate.arbitrator import Arbitrator, ArbitrationResult


class TestPersonas:
    def test_all_personas_defined(self):
        assert len(ALL_PERSONAS) == 3
        roles = [p.role for p in ALL_PERSONAS]
        assert "pragmatist" in roles
        assert "idealist" in roles
        assert "skeptic" in roles

    def test_persona_has_required_fields(self):
        for p in ALL_PERSONAS:
            assert p.name
            assert p.role
            assert p.focus
            assert p.bias_prompt
            assert len(p.evaluation_criteria) > 0

    def test_pragmatist_focus(self):
        assert "可行" in PRAGMATIST.focus

    def test_idealist_focus(self):
        assert "本质" in IDEALIST.focus or "最优" in IDEALIST.focus

    def test_skeptic_focus(self):
        assert "盲" in SKEPTIC.focus or "质疑" in SKEPTIC.focus


class TestArbitrator:
    def test_arbitrate_basic(self):
        arb = Arbitrator()
        result = arb.arbitrate(
            query="测试问题",
            positions={
                "pragmatist": "务实方案：快速实现",
                "idealist": "理想方案：追求本质",
                "skeptic": "质疑：假设可能不成立",
            },
        )
        assert isinstance(result, ArbitrationResult)
        assert result.confidence > 0
        assert result.consensus_level in ("strong", "moderate", "weak")
        assert len(result.persona_weights) == 3

    def test_arbitrate_with_spirit_resonance(self):
        arb = Arbitrator()
        resonances = [{"drive_direction": "deep_reasoning", "strength": 0.8}]
        result = arb.arbitrate(
            query="为什么底层原理",
            positions={"pragmatist": "p1", "idealist": "i1", "skeptic": "s1"},
            spirit_resonances=resonances,
        )
        assert result.persona_weights.get("idealist", 0) > 0.33
        assert result.spirit_drive == "deep_reasoning"

    def test_weights_sum_to_one(self):
        arb = Arbitrator()
        result = arb.arbitrate(
            query="test",
            positions={"pragmatist": "p", "idealist": "i", "skeptic": "s"},
        )
        total = sum(result.persona_weights.values())
        assert abs(total - 1.0) < 0.05

    def test_detect_disagreements(self):
        arb = Arbitrator()
        result = arb.arbitrate(
            query="test",
            positions={
                "pragmatist": "这个方案不可行",
                "idealist": "应该追求最优解",
                "skeptic": "建议重新考虑",
            },
        )
        assert isinstance(result.disagreements, list)

    def test_consensus_strong(self):
        arb = Arbitrator()
        result = arb.arbitrate(
            query="test",
            positions={
                "pragmatist": "方案可行，建议实施",
                "idealist": "方案合理，值得推进",
                "skeptic": "方案基本可靠，可以尝试",
            },
        )
        assert result.consensus_level == "strong"

    def test_arbitrate_to_dict(self):
        arb = Arbitrator()
        result = arb.arbitrate(
            query="test",
            positions={"pragmatist": "p", "idealist": "i", "skeptic": "s"},
        )
        d = result.to_dict()
        assert "confidence" in d
        assert "consensus_level" in d
        assert "persona_weights" in d


class TestDebateArena:
    @pytest.mark.asyncio
    async def test_debate_basic(self):
        arena = DebateArena()
        result = await arena.debate(
            query="如何优化系统性能？",
            candidates=[
                {"source": "experience", "response": "增加缓存", "quality": 70},
                {"source": "ollama", "response": "重构架构", "quality": 65},
            ],
        )
        assert isinstance(result, DebateResult)
        assert len(result.positions) == 3
        assert result.arbitration.confidence > 0

    @pytest.mark.asyncio
    async def test_debate_no_candidates(self):
        arena = DebateArena()
        result = await arena.debate(query="测试问题")
        assert isinstance(result, DebateResult)
        assert len(result.positions) == 3

    @pytest.mark.asyncio
    async def test_debate_with_spirit_resonance(self):
        arena = DebateArena()
        resonances = [{"drive_direction": "persist", "strength": 0.9}]
        result = await arena.debate(
            query="失败后如何继续",
            candidates=[{"source": "experience", "response": "重试", "quality": 50}],
            spirit_resonances=resonances,
        )
        assert result.arbitration.spirit_drive == "persist"

    @pytest.mark.asyncio
    async def test_debate_to_dict(self):
        arena = DebateArena()
        result = await arena.debate(query="test")
        d = result.to_dict()
        assert "positions" in d
        assert "arbitration" in d

    @pytest.mark.asyncio
    async def test_debate_cross_examine(self):
        arena = DebateArena()
        result = await arena.debate(
            query="复杂问题",
            candidates=[{"source": "knowledge", "response": "方案A", "quality": 60}],
            max_rounds=2,
        )
        for pos in result.positions.values():
            if "质询回应" in pos:
                assert len(pos) > 20
                break

    @pytest.mark.asyncio
    async def test_debate_custom_personas(self):
        custom = [PRAGMATIST, SKEPTIC]
        arena = DebateArena(personas=custom)
        result = await arena.debate(query="test")
        assert len(result.positions) == 2