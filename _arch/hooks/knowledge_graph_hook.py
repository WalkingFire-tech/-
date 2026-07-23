
# AUTO-GENERATED HOOK for core\knowledge_graph.py
# 生成时间: 2026-07-24T02:51:22.979446
# 人工审核后移动到合适位置

try:
    from core.knowledge_graph import KnowledgeGraph
    _knowledge_graph_available = True
except ImportError:
    _knowledge_graph_available = False
    logger.warning("knowledge_graph 模块加载失败")

def try_knowledge_graph(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _knowledge_graph_available:
        return None
    try:
        instance = KnowledgeGraph()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "knowledge_graph"}
    except Exception as e:
        logger.warning(f"knowledge_graph 执行失败: {e}")
        return None
