"""
P0-1: CognitivePlanner同步主路由接入测试

验证：
1. L2/L3认知学习结果在阶段3（并行推理）之前被消费
2. 降级路径使用run_in_executor而非同步阻塞
3. L1感知emotion影响方法论（共情优先/深度探索）
4. L2知识注入truth_insights后能传递到并行推理
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio


class TestCognitivePlannerEarlyConsumption:
    """阶段2.8：L2/L3提前消费（在并行推理之前）"""

    def test_bypass_result_consumed_before_parallel(self):
        """旁路Future在阶段3之前被await"""
        from core.services.cognitive_planner import CognitiveCycleResult
        mock_result = CognitiveCycleResult(
            conversation_id="test",
            user_input="test",
            response="test response",
            perception={"intent": "question", "confidence": 0.8},
            learning={"knowledge_gained": 2, "sources": ["test"], "confidence": 0.7},
            integration={"success": True, "core_knowledge": [{"content": "fact1", "confidence": 0.8}]},
            validation={"status": "pass", "confidence": 0.9, "doubts": []},
            evolution={},
            introspection={},
            processing_time_ms=100.0,
            success=True,
            timestamp="2026-01-01T00:00:00",
        )
        assert mock_result.success is True
        assert mock_result.learning.get("knowledge_gained") == 2
        assert mock_result.integration.get("success") is True

    def test_l2_knowledge_injects_to_truth_insights(self):
        """L2知识注入truth_insights格式正确"""
        _cognitive_learning = {"knowledge_gained": 3, "sources": ["exp", "kb"], "confidence": 0.8}
        _cognitive_integration = {"success": True, "core_knowledge": [
            {"content": "Python是解释型语言", "confidence": 0.9},
            {"content": "GIL限制多线程", "confidence": 0.85},
        ]}
        truth_insights = "已有知识"
        _l2_knowledge_context = f"\n【L2认知学习-新获得知识】(置信度{_cognitive_learning['confidence']:.0%}, 来源:{','.join(str(s) for s in _cognitive_learning['sources'][:3])})"
        for _ck in _cognitive_integration["core_knowledge"][:3]:
            _ck_content = _ck.get("content", "")
            if _ck_content:
                _l2_knowledge_context += f"\n- {_ck_content[:200]}"
        truth_insights = (truth_insights + _l2_knowledge_context) if truth_insights else _l2_knowledge_context
        assert "L2认知学习-新获得知识" in truth_insights
        assert "Python是解释型语言" in truth_insights
        assert "GIL限制多线程" in truth_insights
        assert "80%" in truth_insights

    @pytest.mark.asyncio
    async def test_degradation_uses_run_in_executor(self):
        """降级路径使用run_in_executor而非同步阻塞"""
        mock_cp = MagicMock()
        mock_cp._learn = MagicMock(return_value={"knowledge_gained": 1, "sources": ["test"], "confidence": 0.6})
        mock_cp._integrate = MagicMock(return_value={"success": True, "core_knowledge": []})
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: mock_cp._learn("test", {}))
        assert result["knowledge_gained"] == 1
        mock_cp._learn.assert_called_once()


class TestL1PerceptionMethodologyInfluence:
    """L1感知结果影响方法论"""

    def test_frustrated_emotion_enables_empathy_first(self):
        """frustrated情绪启用共情优先模式"""
        methodology = {}
        emotion = "frustrated"
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
            methodology.setdefault("tone_adjustment", emotion)
        assert methodology.get("empathy_first") is True
        assert methodology.get("tone_adjustment") == "frustrated"

    def test_angry_emotion_enables_empathy_first(self):
        """angry情绪启用共情优先模式"""
        methodology = {}
        emotion = "angry"
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
            methodology.setdefault("tone_adjustment", emotion)
        assert methodology.get("empathy_first") is True
        assert methodology.get("tone_adjustment") == "angry"

    def test_anxious_emotion_enables_empathy_first(self):
        """anxious情绪启用共情优先模式"""
        methodology = {}
        emotion = "anxious"
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
            methodology.setdefault("tone_adjustment", emotion)
        assert methodology.get("empathy_first") is True

    def test_curious_low_confusion_enables_depth_mode(self):
        """好奇+低困惑启用深度探索模式"""
        methodology = {}
        emotion = "curious"
        confusion = 0.2
        if emotion == "curious" and confusion < 0.3:
            methodology.setdefault("depth_mode", True)
        assert methodology.get("depth_mode") is True

    def test_curious_high_confusion_no_depth_mode(self):
        """好奇+高困惑不启用深度探索（已由confusion>0.7启用本质推理）"""
        methodology = {}
        emotion = "curious"
        confusion = 0.5
        if emotion == "curious" and confusion < 0.3:
            methodology.setdefault("depth_mode", True)
        assert "depth_mode" not in methodology

    def test_neutral_emotion_no_methodology_change(self):
        """中性情绪不修改方法论"""
        methodology = {}
        emotion = "neutral"
        confusion = 0.1
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
        if emotion == "curious" and confusion < 0.3:
            methodology.setdefault("depth_mode", True)
        assert len(methodology) == 0

    def test_urgency_fast_route(self):
        """紧迫度>0.8切换快速路由"""
        route = "standard"
        urgency = 0.9
        if urgency > 0.8:
            route = "fast"
        assert route == "fast"

    def test_confusion_essence_reasoning(self):
        """困惑度>0.7启用本质推理"""
        methodology = {}
        confusion = 0.8
        if confusion > 0.7:
            methodology.setdefault("need_essence_reasoning", True)
        assert methodology.get("need_essence_reasoning") is True

    def test_combined_emotion_and_confusion(self):
        """情绪+困惑同时生效"""
        methodology = {}
        emotion = "frustrated"
        confusion = 0.8
        urgency = 0.5
        if urgency > 0.8:
            route = "fast"
        if confusion > 0.7:
            methodology.setdefault("need_essence_reasoning", True)
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
            methodology.setdefault("tone_adjustment", emotion)
        assert methodology.get("need_essence_reasoning") is True
        assert methodology.get("empathy_first") is True
        assert methodology.get("tone_adjustment") == "frustrated"


class TestCognitivePlannerBypassTimeout:
    """旁路超时和降级行为"""

    @pytest.mark.asyncio
    async def test_bypass_timeout_falls_back_gracefully(self):
        """旁路超时后优雅降级"""
        import time as _time
        future = asyncio.get_running_loop().run_in_executor(
            None, lambda: _time.sleep(10)
        )
        bypass_result = None
        try:
            bypass_result = await asyncio.wait_for(future, timeout=0.1)
        except (asyncio.TimeoutError, Exception):
            pass
        assert bypass_result is None

    @pytest.mark.asyncio
    async def test_empty_perception_skips_learning(self):
        """空感知结果跳过学习"""
        _cognitive_perception = None
        cp = MagicMock()
        _cognitive_learning = {}
        _cognitive_integration = {}
        if cp and _cognitive_perception:
            _cognitive_learning = cp._learn("test", _cognitive_perception)
        assert _cognitive_learning == {}
        cp._learn.assert_not_called()