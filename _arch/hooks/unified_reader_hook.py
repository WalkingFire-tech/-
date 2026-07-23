
# AUTO-GENERATED HOOK for core\unified_reader.py
# 生成时间: 2026-07-24T02:51:23.075879
# 人工审核后移动到合适位置

try:
    from core.unified_reader import UnifiedReader
    _unified_reader_available = True
except ImportError:
    _unified_reader_available = False
    logger.warning("unified_reader 模块加载失败")

def try_unified_reader(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _unified_reader_available:
        return None
    try:
        instance = UnifiedReader()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "unified_reader"}
    except Exception as e:
        logger.warning(f"unified_reader 执行失败: {e}")
        return None
