"""
闭环调度器 (Closed-Loop Orchestrator)

核心理念：六个模块串联成可迭代的闭环流程
- 不是线性推进，而是评估不通过时自动回退迭代
- 不是写死的模板，而是动态调用模型生成
- 每次迭代都在学习，每次闭环都在进化

六模块：
1. 元认知启动器 → 意图/复杂度/置信度
2. 问题拆解与任务调度 → 任务树/执行顺序
3. 工具调用与执行引擎 → 执行结果
4. 评估与置信度模块 → 质量/置信度/迭代决策
5. 执行监控与保护机制 → 深度/时间/循环检测
6. 数据积累与自动微调 → 经验/技能/基因
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LoopState(Enum):
    INIT = "init"
    METACOGNITION = "metacognition"
    DECOMPOSITION = "decomposition"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    PROTECTION = "protection"
    ACCUMULATION = "accumulation"
    DONE = "done"
    FAILED = "failed"


@dataclass
class LoopContext:
    query: str
    conversation_context: str = ""
    intent_type: str = "chat"
    complexity: float = 0.5
    confidence: float = 0.0
    route: str = "fast"
    iteration: int = 0
    max_iterations: int = 3
    max_depth: int = 5
    max_time_seconds: float = 60.0
    start_time: float = field(default_factory=time.time)
    state: LoopState = LoopState.INIT
    candidates: List[Dict] = field(default_factory=list)
    best: Optional[Dict] = None
    final_response: str = ""
    attempts: List[Tuple] = field(default_factory=list)
    evaluation_passed: bool = False
    evaluation_issues: List[str] = field(default_factory=list)
    tasks: List[Dict] = field(default_factory=list)
    execution_results: List[Dict] = field(default_factory=list)
    fitness_score: Any = None
    iteration_history: List[Dict] = field(default_factory=list)



class ClosedLoopOrchestrator:
    """闭环调度器"""

    def __init__(self):
        self.confidence_threshold = 0.6
        self.quality_threshold = 50.0
        self.ollama_timeout = 30.0
        logger.info("🔄 闭环调度器已初始化")

    async def orchestrate(
        self,
        query: str,
        conversation_context: str = "",
        emit_func=None,
    ) -> LoopContext:
        """
        执行完整的闭环流程
        
        Args:
            query: 用户问题
            conversation_context: 对话上下文
            emit_func: SSE事件发射函数
        
        Returns:
            LoopContext: 完整的闭环上下文
        """
        ctx = LoopContext(
            query=query,
            conversation_context=conversation_context,
        )

        while ctx.state not in (LoopState.DONE, LoopState.FAILED):
            if self._check_protection(ctx):
                break

            try:
                if ctx.state == LoopState.INIT:
                    await self._phase_metacognition(ctx, emit_func)
                elif ctx.state == LoopState.METACOGNITION:
                    await self._phase_decomposition(ctx, emit_func)
                elif ctx.state == LoopState.DECOMPOSITION:
                    await self._phase_execution(ctx, emit_func)
                elif ctx.state == LoopState.EXECUTION:
                    await self._phase_evaluation(ctx, emit_func)
                elif ctx.state == LoopState.EVALUATION:
                    if ctx.evaluation_passed:
                        await self._phase_accumulation(ctx, emit_func)
                    else:
                        await self._phase_reiterate(ctx, emit_func)
                elif ctx.state == LoopState.ACCUMULATION:
                    ctx.state = LoopState.DONE
                elif ctx.state == LoopState.PROTECTION:
                    if ctx.best and ctx.best.get("response"):
                        ctx.final_response = ctx.best["response"]
                        ctx.state = LoopState.DONE
                    else:
                        ctx.final_response = await self._dynamic_fallback(ctx)
                        ctx.state = LoopState.DONE
            except Exception as e:
                logger.error(f"闭环调度异常: {e}")
                ctx.final_response = await self._dynamic_fallback(ctx)
                ctx.state = LoopState.DONE

        return ctx

    async def orchestrate_from_context(self, ctx: LoopContext) -> LoopContext:
        """从已有上下文继续迭代（chat_stream已执行了部分流程）"""
        while ctx.state not in (LoopState.DONE, LoopState.FAILED):
            if self._check_protection(ctx):
                break

            try:
                if ctx.state == LoopState.EXECUTION:
                    ctx.iteration += 1
                    await self._phase_execution(ctx, None)
                elif ctx.state == LoopState.EVALUATION:
                    if ctx.evaluation_passed:
                        await self._phase_accumulation(ctx, None)
                    else:
                        await self._phase_reiterate(ctx, None)
                elif ctx.state == LoopState.ACCUMULATION:
                    ctx.state = LoopState.DONE
                elif ctx.state == LoopState.PROTECTION:
                    ctx.state = LoopState.DONE
                else:
                    ctx.state = LoopState.DONE
            except Exception as e:
                logger.error(f"闭环迭代异常: {e}")
                ctx.state = LoopState.DONE

        return ctx

    async def _phase_metacognition(self, ctx: LoopContext, emit_func):
        """模块1：元认知启动器"""
        ctx.state = LoopState.METACOGNITION
        if emit_func:
            emit_func("step", {"phase": "元认知启动", "status": "running", "detail": "判断问题类型、复杂度、自身认知状态..."})

        try:
            from core.cognitive_dispatcher import get_cognitive_dispatcher
            dispatcher = get_cognitive_dispatcher()
            result = dispatcher.dispatch(ctx.query, ctx.conversation_context)

            ctx.intent_type = result.get("intent_type", "chat")
            ctx.complexity = result.get("complexity", 0.5)
            ctx.confidence = result.get("confidence", 0.5)
            ctx.route = result.get("route", "fast")


            if emit_func:
                emit_func("step", {"phase": "元认知启动", "status": "done",
                    "detail": f"意图:{ctx.intent_type} 复杂度:{ctx.complexity:.0%} 置信度:{ctx.confidence:.0%} 路由:{ctx.route}"})
        except Exception as e:
            logger.debug(f"元认知启动异常: {e}")
            if emit_func:
                emit_func("step", {"phase": "元认知启动", "status": "done", "detail": f"降级: {str(e)[:50]}"})
            ctx.state = LoopState.METACOGNITION


    async def _phase_decomposition(self, ctx: LoopContext, emit_func):
        """模块2：问题拆解与任务调度"""
        ctx.state = LoopState.DECOMPOSITION
        if emit_func:
            emit_func("step", {"phase": "问题拆解", "status": "running", "detail": "将问题分解为可执行原子任务..."})

        ctx.tasks = []

        if ctx.route == "fast" or ctx.complexity < 0.3:
            ctx.tasks.append({"id": "T1", "type": "direct_reply", "description": ctx.query})
        else:
            if ctx.intent_type in ["question", "factual", "verification"]:
                ctx.tasks.append({"id": "T1", "type": "knowledge_search", "description": f"检索关于「{ctx.query[:30]}」的知识"})
                ctx.tasks.append({"id": "T2", "type": "fact_check", "depends_on": ["T1"], "description": "事实验证与交叉比对"})
                ctx.tasks.append({"id": "T3", "type": "reasoning", "depends_on": ["T2"], "description": "基于验证结果进行推理"})
            elif ctx.intent_type in ["complex_query", "challenge"]:
                ctx.tasks.append({"id": "T1", "type": "decompose", "description": f"拆解「{ctx.query[:30]}」的核心维度"})
                ctx.tasks.append({"id": "T2", "type": "multi_source", "depends_on": ["T1"], "description": "多源并行检索与推理"})
                ctx.tasks.append({"id": "T3", "type": "synthesize", "depends_on": ["T2"], "description": "综合分析并生成回答"})
            else:
                ctx.tasks.append({"id": "T1", "type": "direct_reply", "description": ctx.query})

        if emit_func:
            emit_func("step", {"phase": "问题拆解", "status": "done",
                "detail": f"{len(ctx.tasks)}个任务: {' → '.join(t['id'] for t in ctx.tasks)}"})


    async def _phase_execution(self, ctx: LoopContext, emit_func):
        """模块3：工具调用与执行引擎"""
        ctx.state = LoopState.EXECUTION
        if emit_func:
            emit_func("step", {"phase": "闭环执行", "status": "running",
                "detail": f"迭代{ctx.iteration + 1}/{ctx.max_iterations}: 执行任务..."})

        ctx.execution_results = []
        ctx.candidates = []

        for task in ctx.tasks:
            result = await self._execute_task(ctx, task, emit_func)
            if result:
                ctx.execution_results.append(result)
                if result.get("response"):
                    ctx.candidates.append(result)

        if ctx.candidates:
            best = max(ctx.candidates, key=lambda c: c.get("quality", 0))
            ctx.best = best
            ctx.final_response = best.get("response", "")
            ctx.confidence = best.get("quality", 50) / 100.0

        if emit_func:
            emit_func("step", {"phase": "闭环执行", "status": "done",
                "detail": f"获取{len(ctx.candidates)}个候选结果"})


    async def _execute_task(self, ctx: LoopContext, task: Dict, emit_func) -> Optional[Dict]:
        """执行单个任务"""
        task_type = task.get("type", "direct_reply")

        try:
            if task_type == "direct_reply":
                return await self._execute_direct_reply(ctx, emit_func)
            elif task_type in ("knowledge_search", "fact_check", "multi_source"):
                return await self._execute_knowledge_search(ctx, emit_func)
            elif task_type in ("reasoning", "synthesize", "decompose"):
                return await self._execute_reasoning(ctx, emit_func)
        except Exception as e:
            logger.debug(f"任务执行异常 {task['id']}: {e}")
            return None

    async def _execute_direct_reply(self, ctx: LoopContext, emit_func) -> Optional[Dict]:
        """直接回复：调用Ollama模型"""
        try:
            from backend.chat_stream import _fetch_ollama_response
            result = await _fetch_ollama_response(
                ctx.query, conversation_context=ctx.conversation_context, truth_insights=""
            )
            if result and result.get("response"):
                return {
                    "source": result.get("source", "Ollama"),
                    "response": result["response"],
                    "quality": 70,
                }
        except Exception:
            pass

        return await self._execute_reasoning(ctx, emit_func)

    async def _execute_knowledge_search(self, ctx: LoopContext, emit_func) -> Optional[Dict]:
        """知识检索：经验池+知识库+向量检索+事实锚点"""
        responses = []

        try:
            from backend.chat_stream import _fetch_experience
            exp = await _fetch_experience(ctx.query)
            if exp and exp.get("response"):
                responses.append({"source": "经验池", "response": exp["response"], "quality": 65})
        except Exception:
            pass

        try:
            from backend.chat_stream import _fetch_knowledge
            know = await _fetch_knowledge(ctx.query)
            if know and know.get("response"):
                responses.append({"source": "知识库", "response": know["response"], "quality": 70})
        except Exception:
            pass

        try:
            from infrastructure.fact_store import fact_store
            facts = fact_store.search_by_keywords(ctx.query, limit=5)
            if facts:
                fact_text = "\n".join(f"- {f['subject']} {f['predicate']} {f['object']}" for f in facts)
                responses.append({"source": "事实锚点", "response": fact_text, "quality": 75})
        except Exception:
            pass

        if responses:
            return max(responses, key=lambda r: r["quality"])
        return None

    async def _execute_reasoning(self, ctx: LoopContext, emit_func) -> Optional[Dict]:
        """推理：调用Ollama模型进行推理"""
        try:
            from backend.chat_stream import _fetch_ollama_response
            prompt = ctx.query
            if ctx.candidates:
                prior_knowledge = "\n".join(
                    c.get("response", "")[:300] for c in ctx.candidates if c.get("response")
                )
                if prior_knowledge:
                    prompt = f"基于以下信息：\n{prior_knowledge}\n\n请回答：{ctx.query}"

            result = await _fetch_ollama_response(
                prompt, conversation_context=ctx.conversation_context, truth_insights=""
            )
            if result and result.get("response"):
                return {
                    "source": result.get("source", "Ollama推理"),
                    "response": result["response"],
                    "quality": 75,
                }
        except Exception:
            pass
        return None

    async def _phase_evaluation(self, ctx: LoopContext, emit_func):
        """模块4：评估与置信度模块"""
        ctx.state = LoopState.EVALUATION
        if emit_func:
            emit_func("step", {"phase": "闭环评估", "status": "running",
                "detail": f"迭代{ctx.iteration + 1}: 评估结果质量..."})

        ctx.evaluation_passed = False
        ctx.evaluation_issues = []

        if not ctx.final_response or len(ctx.final_response) < 20:
            ctx.evaluation_issues.append("回复过短或为空")
        else:
            try:
                from infrastructure.fitness_evaluator import fitness_evaluator
                ctx.fitness_score = fitness_evaluator.evaluate(
                    question=ctx.query,
                    response=ctx.final_response,
                    user_feedback=0,
                    intent_type=ctx.intent_type,
                )
                if ctx.fitness_score.final_score >= self.quality_threshold:
                    ctx.evaluation_passed = True
                else:
                    ctx.evaluation_issues.append(f"适应度分数{ctx.fitness_score.final_score:.0f}低于阈值{self.quality_threshold}")
            except Exception:
                if ctx.confidence >= self.confidence_threshold:
                    ctx.evaluation_passed = True
                else:
                    ctx.evaluation_issues.append(f"置信度{ctx.confidence:.0%}低于阈值{self.confidence_threshold:.0%}")

        if not ctx.evaluation_issues and ctx.final_response:
            ctx.evaluation_passed = True

        ctx.iteration_history.append({
            "iteration": ctx.iteration + 1,
            "passed": ctx.evaluation_passed,
            "issues": ctx.evaluation_issues,
            "confidence": ctx.confidence,
        })

        if emit_func:
            if ctx.evaluation_passed:
                emit_func("step", {"phase": "闭环评估", "status": "done", "detail": f"✅ 评估通过 (迭代{ctx.iteration + 1})"})
            else:
                emit_func("step", {"phase": "闭环评估", "status": "done",
                    "detail": f"⚠️ 评估未通过: {'; '.join(ctx.evaluation_issues[:2])}"})


    async def _phase_reiterate(self, ctx: LoopContext, emit_func):
        """评估未通过→回退迭代"""
        ctx.iteration += 1

        if ctx.iteration >= ctx.max_iterations:
            if emit_func:
                emit_func("step", {"phase": "闭环迭代", "status": "done",
                    "detail": f"已达最大迭代次数{ctx.max_iterations}，输出当前最佳结果"})
            if ctx.final_response:
                ctx.state = LoopState.ACCUMULATION
            else:
                ctx.state = LoopState.PROTECTION
            return

        if emit_func:
            emit_func("step", {"phase": "闭环迭代", "status": "running",
                "detail": f"迭代{ctx.iteration + 1}: 针对问题重新执行 ({'; '.join(ctx.evaluation_issues[:2])})"})

        ctx.evaluation_issues = []
        ctx.evaluation_passed = False

        ctx.state = LoopState.EXECUTION

    async def _phase_accumulation(self, ctx: LoopContext, emit_func):
        """模块6：数据积累与自动微调"""
        ctx.state = LoopState.ACCUMULATION
        if emit_func:
            emit_func("step", {"phase": "闭环沉淀", "status": "running", "detail": "积累经验、固化技能..."})

        try:
            from infrastructure.database_manager import DatabaseManager
            from datetime import datetime
            db = DatabaseManager.get("data/experience_pool.db")
            db.execute("""
                INSERT INTO experiences (raw_input, raw_output, intent_type, success, quality_score, timestamp, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ctx.query[:500], ctx.final_response[:2000], ctx.intent_type,
                  1 if ctx.evaluation_passed else 0,
                  int(ctx.fitness_score.final_score) if ctx.fitness_score else 50,
                  datetime.now().isoformat(),
                  int((time.time() - ctx.start_time) * 1000)),
            commit=True)
        except Exception as e:
            logger.debug(f"闭环沉淀异常: {e}")

        try:
            from infrastructure.fact_store import fact_store
            if ctx.evaluation_passed and ctx.final_response and len(ctx.final_response) > 50:
                fact_store.extract_and_store(ctx.query, ctx.final_response, source="closed_loop")
        except Exception:
            pass

        if emit_func:
            emit_func("step", {"phase": "闭环沉淀", "status": "done",
                "detail": f"迭代{ctx.iteration + 1}次, 评估{'通过' if ctx.evaluation_passed else '未通过'}"})

        ctx.state = LoopState.DONE

    def _check_protection(self, ctx: LoopContext) -> bool:
        """模块5：执行监控与保护机制"""
        elapsed = time.time() - ctx.start_time
        if elapsed > ctx.max_time_seconds:
            logger.warning(f"闭环超时: {elapsed:.1f}s > {ctx.max_time_seconds}s")
            ctx.state = LoopState.PROTECTION
            return True

        if ctx.iteration >= ctx.max_iterations:
            if ctx.final_response:
                ctx.state = LoopState.ACCUMULATION
            else:
                ctx.state = LoopState.PROTECTION
            return True

        return False

    async def _dynamic_fallback(self, ctx: LoopContext) -> str:
        """动态fallback：不使用写死模板，而是调用模型实时生成"""
        try:
            from backend.chat_stream import _fetch_ollama_response
            result = await _fetch_ollama_response(
                ctx.query, conversation_context=ctx.conversation_context, truth_insights=""
            )
            if result and result.get("response") and len(result["response"]) > 20:
                return result["response"]
        except Exception:
            pass

        try:
            from backend.chat_stream import _fetch_experience
            exp = await _fetch_experience(ctx.query)
            if exp and exp.get("response"):
                return exp["response"]
        except Exception:
            pass

        try:
            from backend.chat_stream import _fetch_knowledge
            know = await _fetch_knowledge(ctx.query)
            if know and know.get("response"):
                return know["response"]
        except Exception:
            pass

        return f"关于「{ctx.query}」，我暂时无法给出满意的回答。请尝试换个方式描述你的问题，或者提供更多背景信息。"


closed_loop_orchestrator = ClosedLoopOrchestrator()