"""
单元测试 - 多路径树搜索 (P2-3)
"""
import pytest
from core.beam_search import BeamSearchEngine, BeamNode


@pytest.fixture
def engine():
    return BeamSearchEngine(max_depth=2, beam_width=2, min_quality_to_skip=60.0)


class TestShouldTrigger:
    def test_trigger_on_empty(self, engine):
        assert engine.should_trigger([]) is True

    def test_trigger_on_low_quality(self, engine):
        assert engine.should_trigger([{"quality": 30}]) is True

    def test_skip_on_high_quality(self, engine):
        assert engine.should_trigger([{"quality": 70}]) is False

    def test_skip_on_mixed_high_best(self, engine):
        assert engine.should_trigger([{"quality": 70}, {"quality": 30}]) is False

    def test_trigger_on_mixed_low_best(self, engine):
        assert engine.should_trigger([{"quality": 50}, {"quality": 30}]) is True


class TestSelectBeam:
    def test_select_top_n(self, engine):
        candidates = [
            {"quality": 30, "source": "a"},
            {"quality": 80, "source": "b"},
            {"quality": 50, "source": "c"},
        ]
        beam = engine.select_beam(candidates)
        assert len(beam) == 2
        assert beam[0]["quality"] == 80
        assert beam[1]["quality"] == 50


class TestExpansionQueries:
    def test_low_quality_expansion(self, engine):
        queries = engine.generate_expansion_queries(
            "what is AI",
            {"quality": 20, "source": "test", "response": "short"}
        )
        assert len(queries) == 2
        assert "更详细" in queries[0] or "另一个角度" in queries[1]

    def test_medium_quality_expansion(self, engine):
        queries = engine.generate_expansion_queries(
            "what is AI",
            {"quality": 40, "source": "test", "response": "a" * 200}
        )
        assert len(queries) == 2

    def test_high_quality_expansion(self, engine):
        queries = engine.generate_expansion_queries(
            "what is AI",
            {"quality": 55, "source": "test", "response": "detailed"}
        )
        assert len(queries) == 2


class TestBeamSearchAsync:
    def test_skip_when_quality_sufficient(self, engine):
        import asyncio
        candidates = [{"quality": 70, "response": "good", "source": "test"}]
        results = asyncio.get_event_loop().run_until_complete(
            engine.search("test", candidates)
        )
        assert len(results) == 1