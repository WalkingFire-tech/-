
# AUTO-GENERATED HOOK for core\tool_registry.py
# 生成时间: 2026-07-24T02:51:23.065659
# 人工审核后移动到合适位置

try:
    from core.tool_registry import ToolRegistry
    _tool_registry_available = True
except ImportError:
    _tool_registry_available = False
    logger.warning("tool_registry 模块加载失败")

def try_tool_registry(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _tool_registry_available:
        return None
    try:
        instance = ToolRegistry()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "tool_registry"}
    except Exception as e:
        logger.warning(f"tool_registry 执行失败: {e}")
        return None
