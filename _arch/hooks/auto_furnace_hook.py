
# AUTO-GENERATED HOOK for core\auto_furnace.py
# 生成时间: 2026-07-24T02:51:22.898898
# 人工审核后移动到合适位置

try:
    from core.auto_furnace import AutoFurnace
    _auto_furnace_available = True
except ImportError:
    _auto_furnace_available = False
    logger.warning("auto_furnace 模块加载失败")

def try_auto_furnace(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _auto_furnace_available:
        return None
    try:
        instance = AutoFurnace()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "auto_furnace"}
    except Exception as e:
        logger.warning(f"auto_furnace 执行失败: {e}")
        return None
