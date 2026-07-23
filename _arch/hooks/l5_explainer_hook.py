
# AUTO-GENERATED HOOK for core\explainability\l5_explainer.py
# 生成时间: 2026-07-24T02:51:22.946989
# 人工审核后移动到合适位置

try:
    from core.explainability.l5_explainer import L5Explainer
    _l5_explainer_available = True
except ImportError:
    _l5_explainer_available = False
    logger.warning("l5_explainer 模块加载失败")

def try_l5_explainer(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _l5_explainer_available:
        return None
    try:
        instance = L5Explainer()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "l5_explainer"}
    except Exception as e:
        logger.warning(f"l5_explainer 执行失败: {e}")
        return None
