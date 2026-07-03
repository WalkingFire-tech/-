"""
Agent协调器 - 管理三角色协作闭环
"""
import asyncio
import time
from typing import Dict, Optional
from loguru import logger

from core.agents.base_agent import Plan, ExecutionResult, ReflectionFeedback
from core.agents.planner_agent import planner_agent
from core.agents.executor_agent import executor_agent
from core.agents.reflector_agent import reflector_agent
from core.agents.agent_events import AgentEventTypes


class AgentCoordinator:
    MAX_ITERATIONS = 3
    QUALITY_THRESHOLD = 50

    def __init__(self):
        self._iteration_count = 0
        planner_agent.receive_message(AgentEventTypes.ReflectionFeedback, planner_agent.handle_reflection_feedback)

    async def collaborate(self, query: str, chat_stream_func=None,
                          context: Dict = None) -> Dict:
        start = time.time()
        self._iteration_count = 0

        plan = planner_agent.create_plan(query, context=context or {})

        if plan.intent_type in ("greeting", "confirmation"):
            quick_responses = {
                "greeting": "嘿，我在。有什么想聊的？我们一起看看。",
                "confirmation": "好的，我明白了。",
            }
            return {
                "response": quick_responses.get(plan.intent_type, ""),
                "source": "planner_direct",
                "quality": 90,
                "success": True,
                "iterations": 0,
                "duration_ms": (time.time() - start) * 1000,
            }

        best_result = None
        for iteration in range(self.MAX_ITERATIONS):
            self._iteration_count = iteration + 1

            exec_result = await self._delegate_to_chat_handler(query, context)

            if not best_result or exec_result.quality > best_result.quality:
                best_result = exec_result

            if exec_result.quality >= self.QUALITY_THRESHOLD:
                break

            feedback = reflector_agent.evaluate(
                plan.plan_id, exec_result, query=query,
            )

            if not feedback.needs_replan:
                break

        if best_result is None:
            best_result = ExecutionResult(
                plan_id=plan.plan_id, success=False,
                response="抱歉，我暂时无法回答这个问题，请稍后再试。",
                source="coordinator_fallback", quality=0,
            )

        duration = (time.time() - start) * 1000
        logger.info(f"AgentCoordinator: 协作完成 query={query[:30]} "
                     f"iterations={self._iteration_count} "
                     f"quality={best_result.quality:.1f} "
                     f"duration={duration:.0f}ms")

        return {
            "response": best_result.response,
            "source": best_result.source,
            "quality": best_result.quality,
            "success": best_result.success,
            "iterations": self._iteration_count,
            "plan_id": best_result.plan_id,
            "duration_ms": duration,
        }

    async def _delegate_to_chat_handler(self, query: str, context: Dict = None) -> ExecutionResult:
        try:
            from backend.chat_handler import chat_never_giveup
            result = await asyncio.wait_for(
                chat_never_giveup(query, context or {}),
                timeout=60,
            )
            return ExecutionResult(
                plan_id="delegated",
                success=True,
                response=result.get("response", ""),
                source=result.get("route", "chat_handler"),
                quality=result.get("confidence", 50) * 100,
                attempts=result.get("attempts", []),
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                plan_id="delegated", success=False,
                response="处理超时", source="timeout", quality=0,
            )
        except Exception as e:
            return ExecutionResult(
                plan_id="delegated", success=False,
                response=str(e), source="error", quality=0,
            )

    def get_status(self) -> Dict:
        return {
            "coordinator": {
                "iteration_count": self._iteration_count,
                "max_iterations": self.MAX_ITERATIONS,
                "quality_threshold": self.QUALITY_THRESHOLD,
            },
            "planner": planner_agent.get_stats(),
            "executor": executor_agent.get_stats(),
            "reflector": reflector_agent.get_stats(),
        }


agent_coordinator = AgentCoordinator()