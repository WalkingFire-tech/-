"""
L1感知层增强 - 情绪感知模块

让系统能够从文本中感知用户的情绪状态，
包括情感倾向、紧迫度、困惑度等。

核心理念：
- 情绪感知是"看见用户"的第一步
- 情绪不仅仅是标签，而是理解用户状态的关键信号
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class EmotionalState:
    """用户情绪状态"""
    primary_emotion: str
    confidence: float
    intensity: float
    urgency: float
    confusion: float
    sentiment: float
    keywords: List[str]
    timestamp: str


class EmotionDetector:
    """情绪检测器"""

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

        logger.info("😊 情绪检测器已初始化")

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
            primary_emotion=primary,
            confidence=confidence,
            intensity=min(1.0, intensity),
            urgency=min(1.0, urgency),
            confusion=min(1.0, confusion),
            sentiment=max(-1.0, min(1.0, sentiment)),
            keywords=keywords,
            timestamp=datetime.now().isoformat()
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
            primary_emotion="neutral",
            confidence=0.8,
            intensity=0.0,
            urgency=0.0,
            confusion=0.0,
            sentiment=0.0,
            keywords=[],
            timestamp=datetime.now().isoformat()
        )


_emotion_detector = None

def get_emotion_detector() -> EmotionDetector:
    global _emotion_detector
    if _emotion_detector is None:
        _emotion_detector = EmotionDetector()
    return _emotion_detector


class L1PerceptionLayer:
    """
    L1: 感知层 - 快速感知用户输入
    
    职责：
    1. 情绪感知 - 理解用户情感状态
    2. 意图识别 - 判断用户想要什么
    3. 紧迫度评估 - 判断是否需要立即响应
    4. 困惑度检测 - 判断用户是否需要更多解释
    
    这是系统的"眼睛"，负责看见用户的真实状态。
    """
    
    def __init__(self):
        self.emotion_detector = get_emotion_detector()
        self.reporter = None
        self.collector = None
        self.heartbeat = None
        
        try:
            from core.introspection.layer_reporter import LayerReporter
            from core.reporting.state_collector import get_state_collector
            from core.introspection.heartbeat import get_heartbeat_manager
            from core.state_report import LayerHealth
            
            self.reporter = LayerReporter("L1")
            self.collector = get_state_collector()
            self.heartbeat = get_heartbeat_manager()
            self.reporter.report_idle()
        except Exception as e:
            logger.warning(f"L1状态报告初始化失败: {e}")
        
        self.stats = {
            'total_perceptions': 0,
            'emotion_distribution': {},
            'avg_confidence': 0.0,
            'high_urgency_count': 0,
            'high_confusion_count': 0
        }
        
        logger.info("👁️ L1感知层已初始化")
        if self.reporter:
            self.reporter.report_completed(
                metrics={"initialized": 1},
                confidence=1.0
            )
    
    def perceive(self, text: str, context: Optional[Dict] = None) -> Dict:
        """
        感知用户输入
        
        返回：
        - emotional_state: 情绪状态
        - intent: 初步意图判断
        - needs_immediate_response: 是否需要立即响应
        - needs_clarification: 是否需要澄清
        - confidence: 整体置信度
        """
        self.stats['total_perceptions'] += 1
        
        if self.reporter:
            self.reporter.report_busy(
                operation=f"感知: {text[:50]}",
                active_tasks=[f"分析用户输入"]
            )
        
        emotional_state = self.emotion_detector.detect(text, context)
        
        intent = self._detect_intent(text, emotional_state)
        needs_immediate = emotional_state.urgency > 0.7
        needs_clarification = emotional_state.confusion > 0.6
        
        self._update_stats(emotional_state)
        
        result = {
            'emotional_state': emotional_state,
            'intent': intent,
            'needs_immediate_response': needs_immediate,
            'needs_clarification': needs_clarification,
            'confidence': emotional_state.confidence,
            'text': text,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.reporter:
            self.reporter.report_completed(
                metrics={'perceived': 1, 'emotion': emotional_state.primary_emotion},
                confidence=emotional_state.confidence
            )
        
        return result
    
    def _detect_intent(self, text: str, emotional_state: EmotionalState) -> str:
        """初步意图判断"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['为什么', '怎么', '如何', 'why', 'how', 'what']):
            return 'question'
        elif any(kw in text_lower for kw in ['帮我', '请', '帮我', 'help', 'please']):
            return 'request'
        elif any(kw in text_lower for kw in ['谢谢', '感谢', '好的', 'thanks', 'ok']):
            return 'acknowledgment'
        elif emotional_state.primary_emotion == 'anger':
            return 'complaint'
        elif emotional_state.confusion > 0.5:
            return 'clarification'
        else:
            return 'statement'
    
    def _update_stats(self, emotional_state: EmotionalState):
        """更新统计信息"""
        emotion = emotional_state.primary_emotion
        self.stats['emotion_distribution'][emotion] = \
            self.stats['emotion_distribution'].get(emotion, 0) + 1
        
        total = self.stats['total_perceptions']
        prev_avg = self.stats['avg_confidence']
        self.stats['avg_confidence'] = (prev_avg * (total - 1) + emotional_state.confidence) / total
        
        if emotional_state.urgency > 0.7:
            self.stats['high_urgency_count'] += 1
        if emotional_state.confusion > 0.6:
            self.stats['high_confusion_count'] += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()