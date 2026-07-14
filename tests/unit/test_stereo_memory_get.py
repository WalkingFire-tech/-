"""
单元测试 — StereoMemory.get() 修复：确保睡眠整合消费端正常工作
"""
import pytest


class TestStereoMemoryGet:
    """验证StereoMemory.get() dict兼容访问器"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys
        from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        yield

    def _make_memory(self, content="test", consolidated=True, topic="general", feedback=None):
        from core.memory.stereo_memory import (
            StereoMemory, MemoryType, SelfDimension, TimeDimension, MemoryContext,
        )
        return StereoMemory(
            memory_id="test-001",
            content=content,
            memory_type=MemoryType.CONVERSATION,
            importance=0.5,
            self_dimension=SelfDimension(),
            time_dimension=TimeDimension(),
            context=MemoryContext(),
            metadata={
                "consolidated": consolidated,
                "topic": topic,
                "feedback": feedback,
            },
        )

    def test_get_content_returns_field(self):
        m = self._make_memory(content="hello world")
        assert m.get("content") == "hello world"

    def test_get_content_default_returns_none(self):
        m = self._make_memory()
        assert m.get("nonexistent") is None

    def test_get_content_with_custom_default(self):
        m = self._make_memory()
        assert m.get("nonexistent", "fallback") == "fallback"

    def test_get_consolidated_from_metadata(self):
        m = self._make_memory(consolidated=True)
        assert m.get("consolidated") is True

    def test_get_topic_from_metadata(self):
        m = self._make_memory(topic="weather")
        assert m.get("topic") == "weather"

    def test_get_feedback_from_metadata(self):
        m = self._make_memory(feedback="good answer")
        assert m.get("feedback") == "good answer"

    def test_get_feedback_none(self):
        m = self._make_memory(feedback=None)
        assert m.get("feedback") is None

    def test_get_memory_id_from_field(self):
        m = self._make_memory()
        assert m.get("memory_id") == "test-001"

    def test_get_importance_from_field(self):
        m = self._make_memory()
        assert m.get("importance") == 0.5

    def test_sleep_consolidation_pattern(self):
        m1 = self._make_memory(content="test1", consolidated=True, topic="science")
        m2 = self._make_memory(content="test2", consolidated=False, topic="weather")

        recent = [m1, m2]
        unprocessed = sum(1 for m in recent if not m.get("consolidated", False))
        assert unprocessed == 1, f"should detect 1 unprocessed, got {unprocessed}"

        topics = [m.get("topic", "general") for m in recent]
        assert topics == ["science", "weather"]

        contents = [str(m.get("content", ""))[:50] for m in recent]
        assert contents == ["test1", "test2"]
