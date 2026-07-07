"""
CBNR核心枢纽 - 认知规范化-瓶颈-残差架构

将深度学习中最成功的三种结构模式映射为认知处理引擎：
- L1 认知规范化(BN)：稳定思维链路，防止偏差累积
- L2 认知瓶颈(Bottleneck)：压缩核心，高效推理，重构输出
- L3 认知残差(ResNet)：经验复用，增量学习，防止退化

CBNR-AGI 2.0增强：
- L1 + 预测编码 + 不确定性感知
- L2 + 双模型架构(因果+反事实)
- L3 + 树搜索工作记忆 + 多智能体制衡
"""

from core.cbnr.cognitive_normalization import CognitiveNormalization
from core.cbnr.cognitive_bottleneck import CognitiveBottleneck
from core.cbnr.cognitive_residual import CognitiveResidual
from core.cbnr.hub import CBNRHub

__all__ = [
    'CognitiveNormalization',
    'CognitiveBottleneck',
    'CognitiveResidual',
    'CBNRHub',
]