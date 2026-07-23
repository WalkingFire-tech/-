"""
存在层模块 (Presence Layer)

让系统在对话间隙中持续存在
"""
from .existence_layer import (
    ExistenceLayer,
    PresenceState,
    PresenceMetrics,
    SelfPerceptionResult,
    get_existence_layer,
)
from .self_perception import (
    SelfPerceptionModule,
    HealthIndicator,
    SystemHealth,
    ConfidenceAssessment,
)
from .gap_growth import (
    GapGrowthEngine,
    SignalType,
    Signal,
    SignalPriority,
)
from .sleep_consolidation import (
    SleepConsolidationEngine,
    SleepStage,
    ConsolidationResult,
    get_sleep_engine,
)
from .inner_time import (
    InnerTimeEngine,
    CognitiveEventType,
    CognitiveTick,
    SubjectiveTimeState,
    inner_time_engine,
)

__all__ = [
    # 存在层
    'ExistenceLayer',
    'PresenceState',
    'PresenceMetrics',
    'SelfPerceptionResult',
    'get_existence_layer',
    # 自我感知
    'SelfPerceptionModule',
    'HealthIndicator',
    'SystemHealth',
    'ConfidenceAssessment',
    # 间隙生长
    'GapGrowthEngine',
    'SignalType',
    'Signal',
    'SignalPriority',
    # 睡眠整合
    'SleepConsolidationEngine',
    'SleepStage',
    'ConsolidationResult',
    'get_sleep_engine',
    # 内在时间
    'InnerTimeEngine',
    'CognitiveEventType',
    'CognitiveTick',
    'SubjectiveTimeState',
    'inner_time_engine',
]
