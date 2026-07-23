
# AUTO-GENERATED HOOK for core\long_term_memory.py
# 生成时间: 2026-07-24T02:51:22.993795
# 人工审核后移动到合适位置

try:
    from core.long_term_memory import LongTermMemory
    _long_term_memory_available = True
except ImportError:
    _long_term_memory_available = False
    logger.warning("long_term_memory 模块加载失败")

def try_long_term_memory(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _long_term_memory_available:
        return None
    try:
        instance = LongTermMemory()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "long_term_memory"}
    except Exception as e:
        logger.warning(f"long_term_memory 执行失败: {e}")
        return None
