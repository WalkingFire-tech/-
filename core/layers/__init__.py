"""
六层架构模块

基于认知科学和控制论的分层架构：
- L1: 感知增强层（快速感知）
- L2: 学习层（经验积累）
- L3: 整合层（知识整合）
- L4: 验证层（结果验证）
- L5: 进化层（自我进化）
- L6: 内省层（元认知）
"""

from core.layers.l1_perception_enhanced import L1PerceptionLayer
from core.layers.l2_learning import L2LearningLayer
from core.layers.l3_integration import L3IntegrationLayer
from core.layers.l4_validation import L4ValidationLayer
from core.layers.l5_evolution import L5EvolutionLayer
from core.layers.l6_introspection import L6IntrospectionLayer

__all__ = [
    "L1PerceptionLayer",
    "L2LearningLayer",
    "L3IntegrationLayer",
    "L4ValidationLayer",
    "L5EvolutionLayer",
    "L6IntrospectionLayer",
]