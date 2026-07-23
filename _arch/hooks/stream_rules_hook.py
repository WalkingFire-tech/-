
# AUTO-GENERATED HOOK for core\stream_rules.py
# 生成时间: 2026-07-24T02:51:23.059051
# 人工审核后移动到合适位置

try:
    from core.stream_rules import StreamRules
    _stream_rules_available = True
except ImportError:
    _stream_rules_available = False
    logger.warning("stream_rules 模块加载失败")

def try_stream_rules(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _stream_rules_available:
        return None
    try:
        instance = StreamRules()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "stream_rules"}
    except Exception as e:
        logger.warning(f"stream_rules 执行失败: {e}")
        return None
