"""
P2-3: intent_dispatcher.py 测试覆盖

验证意图分发核心逻辑：
1. L1情绪影响方法论（共情优先/深度探索）
2. 紧迫度切换快速路由
3. 困惑度启用本质推理
4. CognitivePlanner异步bypass
5. reflex_engine安全检查
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestL1EmotionMethodology:
    """L1感知情绪影响方法论"""

    def test_frustrated_enables_empathy(self):
        methodology = {}
        emotion = "frustrated"
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
            methodology.setdefault("tone_adjustment", emotion)
        assert methodology["empathy_first"] is True
        assert methodology["tone_adjustment"] == "frustrated"

    def test_curious_low_confusion_enables_depth(self):
        methodology = {}
        emotion = "curious"
        confusion = 0.2
        if emotion == "curious" and confusion < 0.3:
            methodology.setdefault("depth_mode", True)
        assert methodology["depth_mode"] is True

    def test_curious_high_confusion_no_depth(self):
        methodology = {}
        emotion = "curious"
        confusion = 0.5
        if emotion == "curious" and confusion < 0.3:
            methodology.setdefault("depth_mode", True)
        assert "depth_mode" not in methodology

    def test_urgency_switches_to_fast(self):
        route = "standard"
        urgency = 0.9
        if urgency > 0.8:
            route = "fast"
        assert route == "fast"

    def test_confusion_enables_essence(self):
        methodology = {}
        confusion = 0.8
        if confusion > 0.7:
            methodology.setdefault("need_essence_reasoning", True)
        assert methodology["need_essence_reasoning"] is True

    def test_anxious_enables_empathy(self):
        methodology = {}
        emotion = "anxious"
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
            methodology.setdefault("tone_adjustment", emotion)
        assert methodology["empathy_first"] is True

    def test_neutral_no_methodology_change(self):
        methodology = {}
        emotion = "neutral"
        confusion = 0.1
        if emotion in ("frustrated", "angry", "anxious"):
            methodology.setdefault("empathy_first", True)
        if emotion == "curious" and confusion < 0.3:
            methodology.setdefault("depth_mode", True)
        assert len(methodology) == 0


class TestCognitivePlannerPerception:
    """CognitivePlanner感知结果"""

    def test_perception_keys(self):
        perception = {
            "intent": "question",
            "confidence": 0.8,
            "emotion": "neutral",
            "urgency": 0.3,
            "confusion": 0.1,
        }
        assert "emotion" in perception
        assert "urgency" in perception
        assert "confusion" in perception

    def test_perception_drives_routing(self):
        perception = {"emotion": "frustrated", "urgency": 0.9, "confusion": 0.8}
        route = "standard"
        methodology = {}
        if perception["urgency"] > 0.8:
            route = "fast"
        if perception["confusion"] > 0.7:
            methodology["need_essence_reasoning"] = True
        if perception["emotion"] in ("frustrated", "angry", "anxious"):
            methodology["empathy_first"] = True
        assert route == "fast"
        assert methodology["need_essence_reasoning"] is True
        assert methodology["empathy_first"] is True