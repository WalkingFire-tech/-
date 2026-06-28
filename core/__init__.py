"""
核心逻辑模块

包含：
- orchestrator: 系统编排器
- metacognitive_executor: 元认知执行引擎
- cognitive_dispatcher: 认知调度器
- sleep_consolidator: 记忆巩固器（T3）
- canary_evaluator: 金丝雀验证器

注意：不在__init__.py中自动导入，避免触发沉重的初始化链。
请使用 from core.xxx import Yyy 的方式按需导入。
"""

__all__ = [
    "SystemOrchestrator",
    "MetacognitiveExecutor",
    "CognitiveDispatcher",
    "SleepConsolidator",
    "CanaryEvaluator",
]


def __getattr__(name):
    """延迟导入：仅在访问时才加载对应模块"""
    _lazy_map = {
        "SystemOrchestrator": "core.orchestrator",
        "MetacognitiveExecutor": "core.metacognitive_executor",
        "CognitiveDispatcher": "core.cognitive_dispatcher",
        "SleepConsolidator": "core.sleep_consolidator",
        "CanaryEvaluator": "core.canary_evaluator",
    }
    if name in _lazy_map:
        import importlib
        module = importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module 'core' has no attribute {name!r}")