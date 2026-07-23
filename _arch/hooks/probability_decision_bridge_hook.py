
# AUTO-GENERATED HOOK for core\presence\probability_decision_bridge.py
# 生成时间: 2026-07-24T02:51:23.015055
# 人工审核后移动到合适位置

try:
    from core.presence.probability_decision_bridge import ProbabilityDecisionBridge
    _probability_decision_bridge_available = True
except ImportError:
    _probability_decision_bridge_available = False
    logger.warning("probability_decision_bridge 模块加载失败")

def try_probability_decision_bridge(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _probability_decision_bridge_available:
        return None
    try:
        instance = ProbabilityDecisionBridge()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "probability_decision_bridge"}
    except Exception as e:
        logger.warning(f"probability_decision_bridge 执行失败: {e}")
        return None
