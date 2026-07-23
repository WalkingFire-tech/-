
# AUTO-GENERATED HOOK for core\decision_chain.py
# 生成时间: 2026-07-24T02:51:22.931616
# 人工审核后移动到合适位置

try:
    from core.decision_chain import DecisionChain
    _decision_chain_available = True
except ImportError:
    _decision_chain_available = False
    logger.warning("decision_chain 模块加载失败")

def try_decision_chain(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _decision_chain_available:
        return None
    try:
        instance = DecisionChain()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "decision_chain"}
    except Exception as e:
        logger.warning(f"decision_chain 执行失败: {e}")
        return None
