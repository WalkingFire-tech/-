"""
情绪感知工具 — 从文本中感知用户的情绪状态

提取自 core/layers/l1_perception_enhanced.py
让系统能"看见用户"的情绪，包括情感倾向、紧迫度、困惑度
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class EmotionalState:
    primary_emotion: str
    confidence: float
    intensity: float
    urgency: float
    confusion: float
    sentiment: float
    keywords: List[str]
    timestamp: str


class EmotionDetector:

    def __init__(self):
        self.emotion_keywords = {
            "anger": ["气", "怒", "烦", "恼", "恨", "骂", "凭什么", "为什么不", "angry", "mad", "furious", "rage", "为什么", "怎么又"],
            "joy": ["好", "棒", "赞", "高兴", "开心", "喜欢", "爱", "好棒", "great", "good", "nice", "excellent", "perfect", "amazing"],
            "sadness": ["难过", "伤心", "失落", "遗憾", "后悔", "可惜", "痛", "sad", "upset", "depressed", "grief", "lonely"],
            "fear": ["害怕", "担心", "紧张", "焦虑", "不安", "恐惧", "慌", "fear", "afraid", "worried", "anxious", "scared"],
            "surprise": ["惊讶", "意外", "竟然", "没想到", "居然", "真的吗", "surprise", "shock", "unexpected", "wow"]
        }
        self.intensity_modifiers = {
            "high": ["非常", "极其", "特别", "超级", "很", "超", "极"],
            "medium": ["比较", "挺", "满", "还"],
            "low": ["有点", "稍微", "略", "有一点点"]
        }
        self.urgency_keywords = ["马上", "立刻", "赶紧", "尽快", "现在", "急", "紧急", "immediately", "urgent", "asap", "right now"]
        self.confusion_keywords = ["不懂", "不明白", "不理解", "迷糊", "困惑", "什么意思", "confused", "don't understand", "what do you mean", "unclear"]

    def detect(self, text: str, context: Optional[Dict] = None) -> EmotionalState:
        if not text or len(text.strip()) < 2:
            return self._neutral_state()
        primary, confidence = self._detect_primary_emotion(text)
        intensity = self._calculate_intensity(text)
        urgency = self._detect_urgency(text)
        confusion = self._detect_confusion(text)
        sentiment = self._calculate_sentiment(text)
        keywords = self._extract_keywords(text)
        return EmotionalState(
            primary_emotion=primary, confidence=confidence,
            intensity=min(1.0, intensity), urgency=min(1.0, urgency),
            confusion=min(1.0, confusion), sentiment=max(-1.0, min(1.0, sentiment)),
            keywords=keywords, timestamp=datetime.now().isoformat()
        )

    def _detect_primary_emotion(self, text: str) -> Tuple[str, float]:
        text_lower = text.lower()
        counts = {}
        for emotion, keywords in self.emotion_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                counts[emotion] = count
        if not counts:
            return "neutral", 0.5
        primary = max(counts, key=counts.get)
        total = sum(counts.values())
        ratio = counts[primary] / total
        length_factor = min(1.0, len(text) / 50)
        confidence = min(1.0, ratio * 0.7 + 0.3 * length_factor)
        return primary, confidence

    def _calculate_intensity(self, text: str) -> float:
        text_lower = text.lower()
        intensity = 0.3
        for level, modifiers in self.intensity_modifiers.items():
            for mod in modifiers:
                if mod in text_lower:
                    if level == "high":
                        intensity += 0.2
                    elif level == "medium":
                        intensity += 0.1
                    else:
                        intensity += 0.05
        if "！" in text or "!" in text:
            intensity += 0.1
        if "？？" in text or "??" in text:
            intensity += 0.1
        if re.search(r'(.)\1{2,}', text):
            intensity += 0.1
        return min(1.0, intensity)

    def _detect_urgency(self, text: str) -> float:
        text_lower = text.lower()
        urgency = 0.0
        for kw in self.urgency_keywords:
            if kw in text_lower:
                urgency += 0.2
        if len(text.split()) < 5:
            urgency += 0.1
        return min(1.0, urgency)

    def _detect_confusion(self, text: str) -> float:
        text_lower = text.lower()
        confusion = 0.0
        for kw in self.confusion_keywords:
            if kw in text_lower:
                confusion += 0.2
        if "?" in text:
            confusion += 0.1
        return min(1.0, confusion)

    def _calculate_sentiment(self, text: str) -> float:
        text_lower = text.lower()
        positive_words = ["好", "棒", "赞", "喜欢", "爱", "开心", "高兴", "优秀", "完美", "great", "good", "nice", "love", "like", "excellent"]
        negative_words = ["不好", "差", "坏", "讨厌", "恨", "伤心", "难过", "糟糕", "麻烦", "bad", "terrible", "awful", "hate", "dislike"]
        positive = sum(1 for w in positive_words if w in text_lower)
        negative = sum(1 for w in negative_words if w in text_lower)
        total = positive + negative
        if total == 0:
            return 0.0
        return (positive - negative) / total

    def _extract_keywords(self, text: str) -> List[str]:
        text_lower = text.lower()
        keywords = []
        for emotion, words in self.emotion_keywords.items():
            for w in words:
                if w in text_lower:
                    keywords.append(w)
                    if len(keywords) >= 5:
                        break
            if len(keywords) >= 5:
                break
        return keywords

    def _neutral_state(self) -> EmotionalState:
        return EmotionalState(
            primary_emotion="neutral", confidence=0.8, intensity=0.0,
            urgency=0.0, confusion=0.0, sentiment=0.0, keywords=[],
            timestamp=datetime.now().isoformat()
        )


_emotion_detector = None


def get_emotion_detector() -> EmotionDetector:
    global _emotion_detector
    if _emotion_detector is None:
        _emotion_detector = EmotionDetector()
    return _emotion_detector