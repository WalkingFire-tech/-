"""
核心逻辑模块

包含：
- orchestrator: 系统编排器
- metacognitive_executor: 元认知执行引擎
- cognitive_dispatcher: 认知调度器
- sleep_consolidator: 记忆巩固器（T3）
- canary_evaluator: 金丝雀验证器
"""

from core.orchestrator import SystemOrchestrator
from core.metacognitive_executor import MetacognitiveExecutor
from core.cognitive_dispatcher import CognitiveDispatcher
from core.sleep_consolidator import SleepConsolidator
from core.canary_evaluator import CanaryEvaluator

__all__ = [
    "SystemOrchestrator",
    "MetacognitiveExecutor",
    "CognitiveDispatcher",
    "SleepConsolidator",
    "CanaryEvaluator",
]