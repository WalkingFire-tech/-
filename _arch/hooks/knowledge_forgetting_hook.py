
# AUTO-GENERATED HOOK for core\knowledge_forgetting.py
# 生成时间: 2026-07-24T02:51:22.977165
# 人工审核后移动到合适位置

try:
    from core.knowledge_forgetting import KnowledgeForgetting
    _knowledge_forgetting_available = True
except ImportError:
    _knowledge_forgetting_available = False
    logger.warning("knowledge_forgetting 模块加载失败")

def try_knowledge_forgetting(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _knowledge_forgetting_available:
        return None
    try:
        instance = KnowledgeForgetting()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "knowledge_forgetting"}
    except Exception as e:
        logger.warning(f"knowledge_forgetting 执行失败: {e}")
        return None
