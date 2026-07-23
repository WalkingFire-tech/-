"""
执行者Agent - 接收计划、按步骤执行、发布执行结果
"""
import asyncio
import time
from typing import Dict, List, Optional
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request

from core.agents.base_agent import BaseAgent, AgentState, ExecutionResult
from core.agents.agent_events import AgentEventTypes


class ExecutorAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="executor", role="executor")
        self._execution_count = 0

    async def execute_plan(self, plan, chat_stream_func=None,
                           user_input: str = "", context: Dict = None) -> ExecutionResult:
        self.state = AgentState.EXECUTING
        self._execution_count += 1
        start = time.time()

        self.send_message(
            AgentEventTypes.ExecutionStarted,
            {"plan_id": plan.plan_id, "query": plan.query},
            recipient="reflector",
        )

        try:
            if chat_stream_func and user_input:
                result = await self._execute_via_chat_stream(
                    plan, chat_stream_func, user_input, context
                )
            else:
                result = await self._execute_steps_async(plan, context)

            duration = (time.time() - start) * 1000
            exec_result = ExecutionResult(
                plan_id=plan.plan_id,
                success=result.get("success", True),
                response=result.get("response", ""),
                source=result.get("source", "executor"),
                quality=result.get("quality", 50),
                attempts=result.get("attempts", []),
                duration_ms=duration,
            )

            self.send_message(
                AgentEventTypes.ExecutionResult,
                {
                    "plan_id": plan.plan_id,
                    "success": exec_result.success,
                    "response": exec_result.response[:200],
                    "source": exec_result.source,
                    "quality": exec_result.quality,
                    "duration_ms": duration,
                },
                recipient="reflector",
                correlation_id=plan.plan_id,
            )

            logger.info(f"ExecutorAgent: 执行完成 plan={plan.plan_id} "
                         f"success={exec_result.success} quality={exec_result.quality:.1f} "
                         f"duration={duration:.0f}ms")
            self.state = AgentState.IDLE
            return exec_result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"ExecutorAgent: 执行失败: {e}")
            return ExecutionResult(
                plan_id=plan.plan_id,
                success=False,
                response=f"执行失败: {e}",
                source="executor_error",
                quality=0,
                duration_ms=(time.time() - start) * 1000,
            )

    async def _execute_via_chat_stream(self, plan, chat_stream_func,
                                        user_input: str, context: Dict) -> Dict:
        best_result = {"response": "", "source": "", "quality": 0, "success": False, "attempts": []}

        try:
            async for event_type, data in chat_stream_func(user_input, context or {}):
                if event_type == "result":
                    resp = data.get("response", "")
                    if resp and len(resp) > len(best_result["response"]):
                        best_result = {
                            "response": resp,
                            "source": data.get("source", "chat_stream"),
                            "quality": data.get("fitness_score", 50),
                            "success": True,
                            "attempts": data.get("attempts", []),
                        }
        except Exception as e:
            logger.error(f"ExecutorAgent: chat_stream执行异常: {e}")

        return best_result

    async def _execute_steps_async(self, plan, context: Dict = None) -> Dict:
        import concurrent.futures
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="exec_step")
        loop = asyncio.get_event_loop()

        results = []
        for step in plan.steps:
            step_type = step.get("type", "")
            try:
                if step_type == "knowledge_search":
                    r = await loop.run_in_executor(pool, self._step_knowledge_search, plan.query)
                    results.append(r)
                elif step_type == "model_reasoning":
                    r = await loop.run_in_executor(pool, self._step_model_reasoning, plan.query)
                    results.append(r)
                elif step_type == "external_search":
                    r = await loop.run_in_executor(pool, self._step_external_search, plan.query)
                    results.append(r)
                elif step_type == "tool_execution":
                    r = await loop.run_in_executor(pool, self._step_tool_execution, plan.query)
                    results.append(r)
                elif step_type == "synthesis":
                    results.append({"response": "", "source": "synthesis", "quality": 0, "success": True})
            except Exception as e:
                results.append({"response": "", "source": step_type, "quality": 0, "success": False})

        best = max(results, key=lambda r: r.get("quality", 0), default={"response": "", "source": "none", "quality": 0, "success": False})
        return best

    def _step_knowledge_search(self, query: str) -> Dict:
        try:
            from infrastructure.smart_experience_pool import smart_experience_pool
            results = smart_experience_pool.search(query, top_k=3)
            if results:
                best = results[0]
                return {"response": best.get("response", ""), "source": "experience_pool", "quality": 60, "success": True}
        except Exception:
            logger.warning("操作降级跳过")
        return {"response": "", "source": "knowledge_search", "quality": 0, "success": False}

    def _step_model_reasoning(self, query: str) -> Dict:
        try:
            from core.cognitive_dispatcher import get_cognitive_dispatcher
            dispatcher = get_cognitive_dispatcher()
            result = dispatcher.dispatch(user_query=query, context={})
            model = result.get("recommended_model", "qwen2.5-coder:7b")
            resp = ollama_chat_request(
                base_url="http://localhost:11434",
                model=model,
                prompt=query,
                timeout=60,
            )
            text = resp.get("content", "")
            if text:
                return {"response": text, "source": f"ollama_{model}", "quality": 55, "success": True}
        except Exception:
            logger.warning("操作降级跳过")
        return {"response": "", "source": "model_reasoning", "quality": 0, "success": False}

    def _step_external_search(self, query: str) -> Dict:
        try:
            from infrastructure.stealth_search import stealth_search
            results = stealth_search.search(query, max_results=3)
            if results:
                text = "\n".join(r.get("snippet", "") for r in results[:3])
                return {"response": text, "source": "external_search", "quality": 45, "success": True}
        except Exception:
            logger.warning("操作降级跳过")
        return {"response": "", "source": "external_search", "quality": 0, "success": False}

    def _step_tool_execution(self, query: str) -> Dict:
        try:
            from core.tool_registry import tool_executor
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(
                        asyncio.run,
                        tool_executor.execute("calculator", {"expression": query})
                    ).result(timeout=10)
            else:
                result = asyncio.run(
                    tool_executor.execute("calculator", {"expression": query})
                )
            if result.success:
                return {"response": result.data, "source": "tool", "quality": 70, "success": True}
        except Exception:
            logger.warning("操作降级跳过")
        return {"response": "", "source": "tool_execution", "quality": 0, "success": False}


executor_agent = ExecutorAgent()