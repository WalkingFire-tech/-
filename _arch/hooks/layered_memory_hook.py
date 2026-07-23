
# AUTO-GENERATED HOOK for core\memory\layered_memory.py
# 生成时间: 2026-07-24T02:51:22.997798
# 人工审核后移动到合适位置

try:
    from core.memory.layered_memory import LayeredMemory
    _layered_memory_available = True
except ImportError:
    _layered_memory_available = False
    logger.warning("layered_memory 模块加载失败")

def try_layered_memory(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _layered_memory_available:
        return None
    try:
        instance = LayeredMemory()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "layered_memory"}
    except Exception as e:
        logger.warning(f"layered_memory 执行失败: {e}")
        return None
