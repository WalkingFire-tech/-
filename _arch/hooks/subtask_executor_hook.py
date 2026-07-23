
# AUTO-GENERATED HOOK for core\services\subtask_executor.py
# 生成时间: 2026-07-24T02:51:23.050221
# 人工审核后移动到合适位置

try:
    from core.services.subtask_executor import SubtaskExecutor
    _subtask_executor_available = True
except ImportError:
    _subtask_executor_available = False
    logger.warning("subtask_executor 模块加载失败")

def try_subtask_executor(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _subtask_executor_available:
        return None
    try:
        instance = SubtaskExecutor()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "subtask_executor"}
    except Exception as e:
        logger.warning(f"subtask_executor 执行失败: {e}")
        return None
