"""
P3 Phase 4: 自我参照检测层测试

验证：
1. is_self_referential() 正确识别自我参照问题
2. is_self_referential() 不误判非自我参照问题
3. generate_self_reference_response() 生成有效响应
4. intent_dispatcher 集成：自我参照问题走存在性感知路径
"""
import pytest
from backend.services.self_reference_detector import is_self_referential, generate_self_reference_response


class TestIsSelfReferential:
    def test_can_understand(self):
        assert is_self_referential("你能够理解对话的意义么？") is True

    def test_can_understand_short(self):
        assert is_self_referential("你能理解吗") is True

    def test_do_you_know(self):
        assert is_self_referential("你明白吗") is True

    def test_how_do_you_see(self):
        assert is_self_referential("你怎么看这个问题") is True

    def test_do_you_have_consciousness(self):
        assert is_self_referential("你有意识吗") is True

    def test_are_you_alive(self):
        assert is_self_referential("你是不是活着") is True

    def test_what_do_you_feel(self):
        assert is_self_referential("你感到怎样") is True

    def test_can_understand_conversation(self):
        assert is_self_referential("你能理解对话的含义吗") is True

    def test_why_do_you(self):
        assert is_self_referential("你为什么要这样做") is True

    def test_meaning_of_existence(self):
        assert is_self_referential("你存在的意义是什么") is True

    def test_system_has_self(self):
        assert is_self_referential("系统有自我意识吗") is True

    def test_not_self_reference_weather(self):
        assert is_self_referential("今天天气怎么样") is False

    def test_not_self_reference_code(self):
        assert is_self_referential("Python怎么写快速排序") is False

    def test_not_self_reference_fact(self):
        assert is_self_referential("地球到月球的距离是多少") is False

    def test_not_self_reference_help(self):
        assert is_self_referential("帮我写一个函数") is False

    def test_empty_query(self):
        assert is_self_referential("") is False

    def test_short_query(self):
        assert is_self_referential("你") is False

    def test_ambiguous_you(self):
        assert is_self_referential("你能帮我查一下吗") is False


class TestGenerateSelfReferenceResponse:
    def test_returns_dict(self):
        result = generate_self_reference_response("你能理解吗")
        assert isinstance(result, dict)
        assert "response" in result
        assert "intent_type" in result
        assert "confidence" in result

    def test_intent_type_is_self_reference(self):
        result = generate_self_reference_response("你明白吗")
        assert result["intent_type"] == "self_reference"

    def test_route_is_fast(self):
        result = generate_self_reference_response("你有意识吗")
        assert result["route"] == "fast"

    def test_self_referential_flag(self):
        result = generate_self_reference_response("你怎么看")
        assert result["self_referential"] is True

    def test_response_is_nonempty(self):
        result = generate_self_reference_response("你能理解对话的意义么？")
        assert len(result["response"]) > 20

    def test_response_mentions_self_awareness(self):
        result = generate_self_reference_response("你能理解对话的意义么？")
        assert any(kw in result["response"] for kw in ["审视", "自身", "理解", "感知", "认知"])


class TestIntentDispatcherIntegration:
    @pytest.mark.asyncio
    async def test_self_reference_triggers_fast_return(self):
        from backend.services.intent_dispatcher import dispatch_intent
        result = await dispatch_intent(
            user_input="你能够理解对话的意义么？",
            context={},
            history=[],
            attempts=[],
            model="test",
        )
        assert result["intent_type"] == "self_reference"
        assert result["should_return"] is True
        assert result["final_response"] is not None
        assert len(result["final_response"]) > 20

    @pytest.mark.asyncio
    async def test_normal_query_not_affected(self):
        from backend.services.intent_dispatcher import dispatch_intent
        result = await dispatch_intent(
            user_input="Python怎么写快速排序",
            context={},
            history=[],
            attempts=[],
            model="test",
        )
        assert result["intent_type"] != "self_reference"
        assert result["should_return"] is False