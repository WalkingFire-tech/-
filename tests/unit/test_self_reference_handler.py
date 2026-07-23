"""
P3 Phase 4: 锚点查询响应路径测试

验证：
1. query_anchor() 返回三层锚点结构
2. 本心锚定查询
3. 状态感知查询
4. 方向感知查询
5. 响应组合逻辑
6. InnerTimeEngine SELF_REFERENCE 事件类型
"""
import pytest
from backend.services.self_reference_handler import query_anchor, _query_core_alignment, _query_state_perception, _query_direction_sensing


class TestQueryAnchor:
    def test_returns_anchor_structure(self):
        result = query_anchor("你能理解吗")
        assert "response" in result
        assert "anchor_layers" in result
        assert "intent_type" in result
        assert "confidence" in result

    def test_intent_type_is_self_reference(self):
        result = query_anchor("你有意识吗")
        assert result["intent_type"] == "self_reference"

    def test_anchor_layers_has_three_layers(self):
        result = query_anchor("你怎么看")
        layers = result["anchor_layers"]
        assert "core_alignment" in layers
        assert "state_perception" in layers
        assert "direction_sensing" in layers

    def test_response_is_nonempty(self):
        result = query_anchor("你能够理解对话的意义么？")
        assert len(result["response"]) > 50

    def test_response_mentions_self_examination(self):
        result = query_anchor("你能够理解对话的意义么？")
        assert any(kw in result["response"] for kw in ["审视", "自身", "理解", "感知", "认知", "核心"])


class TestCoreAlignment:
    def test_returns_dict(self):
        result = _query_core_alignment()
        assert isinstance(result, dict)
        assert "aligned" in result
        assert "principle_count" in result


class TestStatePerception:
    def test_returns_dict(self):
        result = _query_state_perception()
        assert isinstance(result, dict)
        assert "maturity" in result
        assert "self_description" in result


class TestDirectionSensing:
    def test_returns_dict(self):
        result = _query_direction_sensing()
        assert isinstance(result, dict)
        assert "curiosity_strength" in result


class TestInnerTimeSelfReference:
    def test_self_reference_event_type_exists(self):
        from core.presence.inner_time import CognitiveEventType
        assert hasattr(CognitiveEventType, 'SELF_REFERENCE')
        assert CognitiveEventType.SELF_REFERENCE.value == "self_reference"

    def test_tick_with_self_reference(self):
        from core.presence.inner_time import inner_time_engine, CognitiveEventType
        ct = inner_time_engine.tick(CognitiveEventType.SELF_REFERENCE, intensity=0.9, description="test")
        assert ct.event_type == CognitiveEventType.SELF_REFERENCE
        assert ct.intensity == 0.9