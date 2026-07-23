
# AUTO-GENERATED HOOK for core\active_scheduler.py
# 生成时间: 2026-07-24T02:51:22.890117
# 人工审核后移动到合适位置

try:
    from core.active_scheduler import ActiveScheduler
    _active_scheduler_available = True
except ImportError:
    _active_scheduler_available = False
    logger.warning("active_scheduler 模块加载失败")

def try_active_scheduler(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _active_scheduler_available:
        return None
    try:
        instance = ActiveScheduler()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "active_scheduler"}
    except Exception as e:
        logger.warning(f"active_scheduler 执行失败: {e}")
        return None
