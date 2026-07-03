"""
Agent事件类型定义 - 扩展EventBus
"""

class AgentEventTypes:
    PlanCreated = "agent_plan_created"
    PlanUpdated = "agent_plan_updated"
    ExecutionStarted = "agent_execution_started"
    ExecutionResult = "agent_execution_result"
    ReflectionFeedback = "agent_reflection_feedback"
    ReplanRequest = "agent_replan_request"
    AgentError = "agent_error"