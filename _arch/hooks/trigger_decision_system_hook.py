
# AUTO-GENERATED HOOK for core\trigger_decision_system.py
# 生成时间: 2026-07-24T02:51:23.071807
# 人工审核后移动到合适位置

try:
    from core.trigger_decision_system import TriggerDecisionSystem
    _trigger_decision_system_available = True
except ImportError:
    _trigger_decision_system_available = False
    logger.warning("trigger_decision_system 模块加载失败")

def try_trigger_decision_system(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _trigger_decision_system_available:
        return None
    try:
        instance = TriggerDecisionSystem()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "trigger_decision_system"}
    except Exception as e:
        logger.warning(f"trigger_decision_system 执行失败: {e}")
        return None
