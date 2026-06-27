"""
学习进化系统 - 七大核心机制

核心理念：学习不是功能，而是存在方式

七大机制：
1. 增量感知学习 - 从每次交互中吸收信号
2. 经验反馈回路 - 验证知识有效性
3. 失败的炼金术 - 从错误中提炼黄金
4. 工具自我构建 - 从需求中生成工具
5. 知识网络编织 - 建立知识连接
6. 认知节奏控制器 - 动态调整学习节奏
7. 元学习策略优化 - 学习如何学习
"""

from .incremental_perception import (
    IncrementalPerception,
    Signal,
    SignalType,
    PerceptionResult,
)
from .feedback_loop import (
    LearningFeedbackLoop,
    Feedback,
    FeedbackType,
    ValidationRule,
    LoopResult,
)
from .error_alchemy import (
    ErrorAlchemy,
    LearningSignal,
    LearningSignalType,
    ErrorCategory,
    ErrorRecord,
    AlchemyResult,
)
from .tool_builder import (
    ToolSelfBuilder,
    ToolNeed,
    Tool,
    ToolStatus,
    NeedPriority,
    BuildResult,
)
from .knowledge_weaver import (
    KnowledgeWeaver,
    Node,
    Connection,
    ConnectionType,
    NodeType,
    Network,
    WeavingResult,
)
from .rhythm_controller import (
    CognitiveRhythmController,
    LearningPhase,
    LearningState,
    RhythmConfig,
    StateSnapshot,
    RhythmAdjustment,
)
from .meta_learning import (
    MetaLearner,
    LearningStrategy,
    StrategyType,
    EvaluationMetric,
    StrategyEvaluation,
    StrategyRecommendation,
)

try:
    from core.external_learner import ExternalLearner
    enhanced_learner = ExternalLearner()
except ImportError:
    enhanced_learner = None

__all__ = [
    # 增量感知学习
    'IncrementalPerception',
    'Signal',
    'SignalType',
    'PerceptionResult',
    # 经验反馈回路
    'LearningFeedbackLoop',
    'Feedback',
    'FeedbackType',
    'ValidationRule',
    'LoopResult',
    # 失败的炼金术
    'ErrorAlchemy',
    'LearningSignal',
    'LearningSignalType',
    'ErrorCategory',
    'ErrorRecord',
    'AlchemyResult',
    # 工具自我构建
    'ToolSelfBuilder',
    'ToolNeed',
    'Tool',
    'ToolStatus',
    'NeedPriority',
    'BuildResult',
    # 知识网络编织
    'KnowledgeWeaver',
    'Node',
    'Connection',
    'ConnectionType',
    'NodeType',
    'Network',
    'WeavingResult',
    # 认知节奏控制器
    'CognitiveRhythmController',
    'LearningPhase',
    'LearningState',
    'RhythmConfig',
    'StateSnapshot',
    'RhythmAdjustment',
    # 元学习策略优化
    'MetaLearner',
    'LearningStrategy',
    'StrategyType',
    'EvaluationMetric',
    'StrategyEvaluation',
    'StrategyRecommendation',
    # 增强学习器
    'enhanced_learner',
]