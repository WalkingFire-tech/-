
# AUTO-GENERATED HOOK for core\services\planner.py
# 生成时间: 2026-07-24T02:51:23.048221
# 人工审核后移动到合适位置

try:
    from core.services.planner import Planner
    _planner_available = True
except ImportError:
    _planner_available = False
    logger.warning("planner 模块加载失败")

def try_planner(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _planner_available:
        return None
    try:
        instance = Planner()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "planner"}
    except Exception as e:
        logger.warning(f"planner 执行失败: {e}")
        return None
