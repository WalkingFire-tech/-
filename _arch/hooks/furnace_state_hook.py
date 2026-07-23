
# AUTO-GENERATED HOOK for core\furnace_state.py
# 生成时间: 2026-07-24T02:51:22.955185
# 人工审核后移动到合适位置

try:
    from core.furnace_state import FurnaceState
    _furnace_state_available = True
except ImportError:
    _furnace_state_available = False
    logger.warning("furnace_state 模块加载失败")

def try_furnace_state(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _furnace_state_available:
        return None
    try:
        instance = FurnaceState()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "furnace_state"}
    except Exception as e:
        logger.warning(f"furnace_state 执行失败: {e}")
        return None
