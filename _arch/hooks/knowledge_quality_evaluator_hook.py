
# AUTO-GENERATED HOOK for core\knowledge_quality_evaluator.py
# 生成时间: 2026-07-24T02:51:22.981644
# 人工审核后移动到合适位置

try:
    from core.knowledge_quality_evaluator import KnowledgeQualityEvaluator
    _knowledge_quality_evaluator_available = True
except ImportError:
    _knowledge_quality_evaluator_available = False
    logger.warning("knowledge_quality_evaluator 模块加载失败")

def try_knowledge_quality_evaluator(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _knowledge_quality_evaluator_available:
        return None
    try:
        instance = KnowledgeQualityEvaluator()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "knowledge_quality_evaluator"}
    except Exception as e:
        logger.warning(f"knowledge_quality_evaluator 执行失败: {e}")
        return None
