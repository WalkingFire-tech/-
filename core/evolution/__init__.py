"""
四层进化架构

对应六层认知架构的扩展：
- 行为进化层 (L1感知层扩展) - 优化回答表达方式
- 知识进化层 (L2+L3扩展) - 验证知识一致性
- 策略进化层 (L5进化层扩展) - 优化决策策略
- 元学习层 (L6内省层扩展) - 观察并调整学习模式
"""

from .behavior_evolution import (
    BehaviorEvolutionEngine,
    get_behavior_evolution_engine
)

from .knowledge_evolution import (
    KnowledgeEvolutionEngine,
    KnowledgeVerification,
    KnowledgeConflict,
    get_knowledge_evolution_engine
)

from .strategy_evolution import (
    StrategyEvolutionEngine,
    get_strategy_evolution_engine
)

from .meta_learning import (
    MetaLearner,
    LearningPattern,
    get_meta_learner
)

from .evolution_scheduler import (
    EvolutionScheduler,
    get_evolution_scheduler,
    start_evolution_scheduler,
    stop_evolution_scheduler
)

__all__ = [
    'BehaviorEvolutionEngine',
    'get_behavior_evolution_engine',
    'KnowledgeEvolutionEngine',
    'KnowledgeVerification',
    'KnowledgeConflict',
    'get_knowledge_evolution_engine',
    'StrategyEvolutionEngine',
    'get_strategy_evolution_engine',
    'MetaLearner',
    'LearningPattern',
    'get_meta_learner',
    'EvolutionScheduler',
    'get_evolution_scheduler',
    'start_evolution_scheduler',
    'stop_evolution_scheduler'
]
