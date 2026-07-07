"""
单元测试 - SpiritCore原则常量不可变性 (1.1)
"""
import pytest
from core.spirit_core import SpiritCore


@pytest.fixture
def sc():
    core = SpiritCore()
    yield core


class TestImmutability:
    def test_cannot_modify_principle(self, sc):
        with pytest.raises(AttributeError):
            sc.PRINCIPLE_NEVER_GIVE_UP = "hacked"

    def test_cannot_delete_principle(self, sc):
        with pytest.raises(AttributeError):
            del sc.PRINCIPLE_NEVER_GIVE_UP

    def test_cannot_modify_meta_constitution(self, sc):
        with pytest.raises(AttributeError):
            sc.META_LAW_SANDBOX = "overridden"

    def test_cannot_delete_meta_constitution(self, sc):
        with pytest.raises(AttributeError):
            del sc.META_LAW_SANDBOX

    def test_cannot_modify_class_level_principle(self):
        with pytest.raises(AttributeError):
            SpiritCore.PRINCIPLE_NEVER_GIVE_UP = "hacked"

    def test_cannot_delete_class_level_principle(self):
        with pytest.raises(AttributeError):
            del SpiritCore.PRINCIPLE_NEVER_GIVE_UP


class TestPrinciples:
    def test_all_principles_defined(self, sc):
        principles = [
            "PRINCIPLE_NEVER_GIVE_UP",
            "PRINCIPLE_MEANINGFUL_RESPONSE",
            "PRINCIPLE_LOGICAL_SELF_CONSISTENT",
            "PRINCIPLE_LEARNING_FROM_FAILURE",
            "PRINCIPLE_STATE_SYNC",
            "PRINCIPLE_PURSUE_ESSENCE",
            "PRINCIPLE_HONEST_WHEN_LOST",
            "PRINCIPLE_MULTI_SOURCE_VERIFY",
        ]
        for p in principles:
            assert hasattr(sc, p), f"Missing principle: {p}"
            assert isinstance(getattr(sc, p), str)
            assert len(getattr(sc, p)) > 0

    def test_meta_constitutions_defined(self, sc):
        metas = ["META_LAW_SANDBOX", "META_LAW_GRADUAL", "META_LAW_HUMAN_APPROVAL"]
        for m in metas:
            assert hasattr(sc, m), f"Missing meta constitution: {m}"
            assert isinstance(getattr(sc, m), str)


class TestEnforceOnOutput:
    def test_empty_response_gets_fallback(self, sc):
        result = sc.enforce_on_output("", source="test", query="test query")
        assert result is not None
        assert len(result) > 0

    def test_valid_response_passes_through(self, sc):
        original = "这是一个有意义的回复，包含了实质内容。"
        result = sc.enforce_on_output(original, source="test", query="test query")
        assert result == original
