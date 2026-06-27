"""
反馈信号路由器 - 扩展L2学习层，将信号分类并路由到不同处理管道
"""

from typing import Dict, List
from enum import Enum
from dataclasses import dataclass


class SignalCategory(Enum):
    """信号分类"""
    PAIRWISE_PREFERENCE = "pairwise_preference"
    ADOPTION = "adoption"
    KNOWLEDGE_GAP = "knowledge_gap"
    AFFECTIVE = "affective"
    CORRECTION = "correction"
    AMBIGUOUS = "ambiguous"


@dataclass
class RoutedSignal:
    """路由后的信号"""
    original_signal: Dict
    category: SignalCategory
    confidence: float
    routing_reason: str
    priority: int


class FeedbackSignalRouter:
    """反馈信号路由器"""
    
    def route(self, signal: Dict) -> RoutedSignal:
        """路由一个反馈信号"""
        signal_type = signal.get("feedback_type")
        context = signal.get("context", {})
        
        if signal_type == "correction":
            return RoutedSignal(signal, SignalCategory.CORRECTION, 0.9, "用户主动纠正", 9)
        
        elif signal_type == "copy":
            return RoutedSignal(signal, SignalCategory.ADOPTION, 0.7, "用户复制回答", 6)
        
        elif signal_type == "follow_up":
            return RoutedSignal(signal, SignalCategory.KNOWLEDGE_GAP, 0.7, "用户追问", 7)
        
        elif signal_type == "dislike" and context.get("reason"):
            return RoutedSignal(signal, SignalCategory.KNOWLEDGE_GAP, 0.75, f"点踩+原因", 8)
        
        elif signal_type == "like":
            return RoutedSignal(signal, SignalCategory.AFFECTIVE, 0.6, "点赞", 5)
        
        else:
            return RoutedSignal(signal, SignalCategory.AMBIGUOUS, 0.3, "无法明确分类", 3)


feedback_router = FeedbackSignalRouter()