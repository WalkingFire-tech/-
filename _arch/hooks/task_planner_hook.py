
# AUTO-GENERATED HOOK for core\task_planner.py
# 生成时间: 2026-07-24T02:51:23.062326
# 人工审核后移动到合适位置

try:
    from core.task_planner import TaskPlanner
    _task_planner_available = True
except ImportError:
    _task_planner_available = False
    logger.warning("task_planner 模块加载失败")

def try_task_planner(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _task_planner_available:
        return None
    try:
        instance = TaskPlanner()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "task_planner"}
    except Exception as e:
        logger.warning(f"task_planner 执行失败: {e}")
        return None
