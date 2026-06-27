"""
伦理与安全模块

确保系统在开放学习中保持核心价值观不变

核心组件：
1. ValueAlignmentChecker - 价值对齐检查器
2. SafeLearningLayer - 安全学习层
3. ValueMonitor - 价值监控器
"""

from .value_alignment_checker import (
    ValueAlignmentChecker,
    ValueAlignmentResult,
    AlignmentStatus,
    check_value_alignment,
    get_value_checker
)

from .safe_learning import (
    SafeLearningLayer,
    learn_safely,
    get_safe_learning
)

__all__ = [
    'ValueAlignmentChecker',
    'ValueAlignmentResult',
    'AlignmentStatus',
    'check_value_alignment',
    'get_value_checker',
    'SafeLearningLayer',
    'learn_safely',
    'get_safe_learning',
]