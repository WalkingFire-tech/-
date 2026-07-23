
# AUTO-GENERATED HOOK for core\spirit_core.py
# 生成时间: 2026-07-24T02:51:23.056918
# 人工审核后移动到合适位置

try:
    from core.spirit_core import SpiritCore
    _spirit_core_available = True
except ImportError:
    _spirit_core_available = False
    logger.warning("spirit_core 模块加载失败")

def try_spirit_core(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _spirit_core_available:
        return None
    try:
        instance = SpiritCore()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "spirit_core"}
    except Exception as e:
        logger.warning(f"spirit_core 执行失败: {e}")
        return None
