
# AUTO-GENERATED HOOK for core\agents\planner_agent.py
# 生成时间: 2026-07-24T02:51:22.893452
# 人工审核后移动到合适位置

try:
    from core.agents.planner_agent import PlannerAgent
    _planner_agent_available = True
except ImportError:
    _planner_agent_available = False
    logger.warning("planner_agent 模块加载失败")

def try_planner_agent(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _planner_agent_available:
        return None
    try:
        instance = PlannerAgent()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "planner_agent"}
    except Exception as e:
        logger.warning(f"planner_agent 执行失败: {e}")
        return None
