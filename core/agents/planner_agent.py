"""
规划者Agent - 分析问题、制定计划、接收反馈后动态重规划
"""
from typing import Dict, List, Optional
from loguru import logger

from core.agents.base_agent import BaseAgent, AgentState, Plan, AgentMessage
from core.agents.agent_events import AgentEventTypes


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="planner", role="planner")
        self._active_plans: Dict[str, Plan] = {}
        self._max_replan_count = 2

    def create_plan(self, query: str, intent_type: str = "",
                    context: Dict = None) -> Plan:
        self.state = AgentState.PLANNING
        try:
            if not intent_type:
                intent_type = self._classify_intent(query)

            steps = self._generate_steps(query, intent_type, context)

            plan = Plan(
                plan_id="",
                query=query,
                intent_type=intent_type,
                steps=steps,
                context=context or {},
            )
            self._active_plans[plan.plan_id] = plan

            self.send_message(
                AgentEventTypes.PlanCreated,
                {
                    "plan_id": plan.plan_id,
                    "query": query,
                    "intent_type": intent_type,
                    "steps": steps,
                    "priority": plan.priority,
                },
                recipient="executor",
            )

            logger.info(f"PlannerAgent: 计划已创建 plan={plan.plan_id} intent={intent_type} steps={len(steps)}")
            self.state = AgentState.IDLE
            return plan

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"PlannerAgent: 创建计划失败: {e}")
            return Plan(plan_id="error", query=query, intent_type="error", steps=[])

    def handle_reflection_feedback(self, event_data: Dict):
        payload = event_data.get("payload", event_data)
        plan_id = payload.get("plan_id", "")
        needs_replan = payload.get("needs_replan", False)
        quality = payload.get("quality_score", 0)
        suggestions = payload.get("suggestions", [])

        plan = self._active_plans.get(plan_id)
        if not plan:
            return

        if needs_replan and plan.replan_count < self._max_replan_count:
            plan.replan_count += 1
            updated_steps = self._adjust_plan(plan, suggestions, quality)
            plan.steps = updated_steps

            self.send_message(
                AgentEventTypes.PlanUpdated,
                {
                    "plan_id": plan_id,
                    "query": plan.query,
                    "steps": updated_steps,
                    "replan_count": plan.replan_count,
                    "reason": f"quality={quality:.1f}, suggestions={suggestions[:2]}",
                },
                recipient="executor",
                correlation_id=plan_id,
            )
            logger.info(f"PlannerAgent: 重规划 plan={plan_id} replan={plan.replan_count}")
        else:
            logger.info(f"PlannerAgent: 计划完成 plan={plan_id} quality={quality:.1f}")

    def _classify_intent(self, query: str) -> str:
        try:
            from core.cognitive_dispatcher import CognitiveDispatcher
            dispatcher = CognitiveDispatcher()
            result = dispatcher.dispatch(user_query=query, context={})
            return result.get("intent_type", "complex_query")
        except Exception:
            if any(kw in query for kw in ["你好", "嗨", "hello", "hi"]):
                return "greeting"
            if any(kw in query for kw in ["是什么", "什么是", "如何", "怎么", "为什么"]):
                return "complex_query"
            return "simple_query"

    def _generate_steps(self, query: str, intent_type: str,
                        context: Dict = None) -> List[Dict]:
        steps = []

        if intent_type in ("greeting", "confirmation"):
            steps.append({"type": "direct_reply", "description": "直接回复"})
            return steps

        steps.append({
            "type": "knowledge_search",
            "description": "搜索知识库和经验池",
            "priority": 1,
        })

        if intent_type in ("complex_query", "learning_trigger"):
            steps.append({
                "type": "model_reasoning",
                "description": "模型推理",
                "priority": 2,
            })
            steps.append({
                "type": "external_search",
                "description": "外部搜索补充",
                "priority": 3,
            })

        if intent_type in ("code", "verification", "challenge"):
            steps.append({
                "type": "tool_execution",
                "description": "工具调用验证",
                "priority": 2,
            })

        steps.append({
            "type": "synthesis",
            "description": "综合所有结果",
            "priority": 10,
        })

        return steps

    def _adjust_plan(self, plan: Plan, suggestions: List[str],
                     quality: float) -> List[Dict]:
        new_steps = list(plan.steps)

        if quality < 30:
            new_steps.insert(0, {
                "type": "model_reasoning",
                "description": "深度模型推理（质量过低）",
                "priority": 0,
            })

        if "补充外部信息" in suggestions or "外部搜索" in str(suggestions):
            new_steps.append({
                "type": "external_search",
                "description": "补充外部搜索",
                "priority": 5,
            })

        if "交叉验证" in str(suggestions):
            new_steps.append({
                "type": "cross_verify",
                "description": "交叉验证结果",
                "priority": 8,
            })

        return new_steps


planner_agent = PlannerAgent()