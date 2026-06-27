"""
反馈系统集成 - 多维信号捕获与知识晋升管道

核心理念：
- 用户反馈是多维信号，而非单一决策
- 建立多阶段验证流程：捕获 → 路由 → 验证 → 晋升 → 存储
- 与现有六层架构自然融合
- 形成数据闭环
"""

from .signal_capture import (
    FeedbackSignalCapture,
    FeedbackSignal,
    FeedbackType
)

from .feedback_router import (
    FeedbackSignalRouter,
    SignalCategory,
    RoutedSignal
)

from .knowledge_validator import (
    KnowledgeValidator,
    ValidationResult
)

from .knowledge_pipeline import (
    KnowledgePromotionPipeline,
    KnowledgeStatus
)

__all__ = [
    'FeedbackSignalCapture',
    'FeedbackSignal',
    'FeedbackType',
    'FeedbackSignalRouter',
    'SignalCategory',
    'RoutedSignal',
    'KnowledgeValidator',
    'ValidationResult',
    'KnowledgePromotionPipeline',
    'KnowledgeStatus'
]