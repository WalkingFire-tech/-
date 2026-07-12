"""
自生本能层 (Instinct Layer)

核心理念：从"被赋予能力"到"自生能力"
- 免疫：自动识别和规避异常
- 自愈：止血→消炎→再生→疤痕
- 本能：推理链编译为快速路径
- 饥饿：能力缺口驱动主动学习
- 代谢：摄入→消化→生长→排泄

当前实施：代谢编排器（Phase 1）
"""

from .metabolism import MetabolismOrchestrator

__all__ = ["MetabolismOrchestrator"]