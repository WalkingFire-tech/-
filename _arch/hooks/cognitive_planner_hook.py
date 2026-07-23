
# AUTO-GENERATED HOOK for core\services\cognitive_planner.py
# 生成时间: 2026-07-24T02:51:23.046226
# 人工审核后移动到合适位置

try:
    from core.services.cognitive_planner import CognitivePlanner
    _cognitive_planner_available = True
except ImportError:
    _cognitive_planner_available = False
    logger.warning("cognitive_planner 模块加载失败")

def try_cognitive_planner(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _cognitive_planner_available:
        return None
    try:
        instance = CognitivePlanner()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "cognitive_planner"}
    except Exception as e:
        logger.warning(f"cognitive_planner 执行失败: {e}")
        return None
