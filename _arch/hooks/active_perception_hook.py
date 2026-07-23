
# AUTO-GENERATED HOOK for core\presence\active_perception.py
# 生成时间: 2026-07-24T02:51:23.012057
# 人工审核后移动到合适位置

try:
    from core.presence.active_perception import ActivePerception
    _active_perception_available = True
except ImportError:
    _active_perception_available = False
    logger.warning("active_perception 模块加载失败")

def try_active_perception(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _active_perception_available:
        return None
    try:
        instance = ActivePerception()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "active_perception"}
    except Exception as e:
        logger.warning(f"active_perception 执行失败: {e}")
        return None
