"""
ReAct推理引擎 (P0-3)

实现 Reason→Act→Observe→Reflect 迭代循环
当首次8路径并行结果适应度不足时，启动ReAct循环进行迭代优化

核心流程：
1. Reason: 分析当前状态，决定下一步行动策略
2. Act: 执行选定策略（调用工具/切换路径/组合推理）
3. Observe: 收集执行结果，评估质量
4. Reflect: 综合评估，决定是否继续迭代

与chat_stream.py的关系：
- 在阶段5.5适应度评估后触发（适应度<50）
- 每次迭代yield step事件给前端
- 迭代结果回注到candidates和final_response
"""

import asyncio
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Doubt:
    description: str
    severity: str
    source: str


@dataclass
class SelfDoubtResult:
    doubts: List[Doubt] = field(default_factory=list)
    penalty: float = 0.0
    most_likely_error: str = ""
    weak_dimensions: List[str] = field(default_factory=list)
    recommended_strategy_hint: str = ""


@dataclass
class ReActIteration:
    iter_num: int
    thought: str
    action: str
    action_input: Dict
    observation: str
    quality: float
    duration_ms: float
    improved: bool = False


@dataclass
class ReActResult:
    iterations: List[ReActIteration] = field(default_factory=list)
    total_iterations: int = 0
    final_response: str = ""
    final_quality: float = 0.0
    improved: bool = False
    strategies_used: List[str] = field(default_factory=list)
    total_duration_ms: float = 0.0


class ReActEngine:
    MAX_ITERATIONS = 2
    FITNESS_THRESHOLD = 60.0
    MIN_IMPROVEMENT = 3.0
    MAX_TOTAL_SECONDS = 20.0

    STRATEGY_ORDER = [
        "model_switch",
        "cross_verify",
        "tool_first",
        "deep_reason",
    ]

    STRATEGY_DESCRIPTIONS = {
        "tool_first": "优先调用工具获取精确信息",
        "model_switch": "切换到不同模型/路径重新推理",
        "cross_verify": "多源交叉验证消除偏差",
        "deep_reason": "深度自我推理+本质分析",
    }

    FALLBACK_MAP = {
        "外部模型": ["model_switch", "cross_verify"],
        "Ollama": ["model_switch", "cross_verify"],
        "知识库": ["tool_first", "cross_verify"],
        "经验池": ["cross_verify", "deep_reason"],
        "外部学习": ["tool_first", "model_switch"],
        "事实锚点": ["cross_verify", "deep_reason"],
        "自我推理": ["model_switch", "tool_first"],
        "工具调用": ["model_switch", "deep_reason"],
    }

    def __init__(self):
        self._iteration_count = 0

    def _self_doubt(
        self,
        response: str,
        candidates: List[Dict],
        fitness_score: Any = None,
        query: str = "",
    ) -> SelfDoubtResult:
        result = SelfDoubtResult()
        penalty = 0.0

        if len(response) < 20:
            result.doubts.append(Doubt("回答内容过短，可能不完整", "major", "completeness"))
            penalty += 0.2
            result.weak_dimensions.append("completeness")

        uncertainty_words = ['可能', '也许', '大概', '似乎', '猜测', '不太确定', 'maybe', 'perhaps', 'might']
        uncertainty_count = sum(1 for w in uncertainty_words if w in response.lower())
        if uncertainty_count > 2:
            result.doubts.append(Doubt(f"包含{uncertainty_count}个不确定性词汇", "minor", "uncertainty"))
            penalty += 0.05 * uncertainty_count
            result.weak_dimensions.append("certainty")

        sources = [c.get("source", "") for c in candidates if c.get("response")]
        unique_sources = set(sources)
        if len(unique_sources) == 1 and sources:
            result.doubts.append(Doubt(f"仅依赖单一来源({sources[0]})", "major", "source_diversity"))
            penalty += 0.15
            result.weak_dimensions.append("cross_validation")

        unreliable = ['blog', 'forum', 'unknown', 'external_search']
        unreliable_count = sum(1 for s in sources if any(u in s.lower() for u in unreliable))
        if unreliable_count > 0 and len(sources) > 0:
            ratio = unreliable_count / len(sources)
            if ratio > 0.5:
                result.doubts.append(Doubt(f"{ratio:.0%}来源不可靠({unreliable_count}/{len(sources)})", "major", "source_reliability"))
                penalty += 0.15 * ratio
                result.weak_dimensions.append("reliability")

        if fitness_score:
            obj = getattr(fitness_score, 'objective_score', 0)
            subj = getattr(fitness_score, 'subjective_score', 0)
            if obj < 50:
                result.doubts.append(Doubt("客观分低(事实可能不准)", "major", "objectivity"))
                penalty += 0.2
                result.weak_dimensions.append("objectivity")
            if subj < 50:
                result.doubts.append(Doubt("主观分低(回答不够完整)", "minor", "subjectivity"))
                penalty += 0.1
                result.weak_dimensions.append("subjectivity")

        possible_errors = []
        numbers = re.findall(r'\b\d+\.?\d*\b', response)
        if len(numbers) > 3:
            possible_errors.append("包含多个具体数值，可能存在计算或引用错误")
        if any(w in response for w in ['绝对', '一定', '肯定', '必须']):
            possible_errors.append("包含绝对化表述，可能过于武断")
        if len(response) > 500:
            possible_errors.append("内容较长，可能存在逻辑遗漏或前后不一致")
        if possible_errors:
            result.most_likely_error = possible_errors[0]
            result.doubts.append(Doubt(f"最可能的错误: {possible_errors[0]}", "critical", "reverse_reasoning"))
            penalty += 0.3

        result.penalty = min(penalty, 1.0)

        if "cross_validation" in result.weak_dimensions or "reliability" in result.weak_dimensions:
            result.recommended_strategy_hint = "cross_verify"
        elif "objectivity" in result.weak_dimensions:
            result.recommended_strategy_hint = "tool_first"
        elif "certainty" in result.weak_dimensions or "subjectivity" in result.weak_dimensions:
            result.recommended_strategy_hint = "deep_reason"
        elif "completeness" in result.weak_dimensions:
            result.recommended_strategy_hint = "model_switch"

        return result

    async def run(
        self,
        query: str,
        initial_response: str,
        initial_quality: float,
        candidates: List[Dict],
        fitness_score: Any = None,
        intent_type: str = "",
        conversation_context: str = "",
        truth_insights: str = "",
        emit_fn: Optional[Callable] = None,
        fetch_ollama_fn: Optional[Callable] = None,
        fetch_external_fn: Optional[Callable] = None,
        fetch_knowledge_fn: Optional[Callable] = None,
        fetch_experience_fn: Optional[Callable] = None,
        self_reason_fn: Optional[Callable] = None,
        compare_fn: Optional[Callable] = None,
        fitness_fn: Optional[Callable] = None,
    ) -> ReActResult:
        result = ReActResult()
        result.final_response = initial_response
        result.final_quality = initial_quality
        start_time = time.time()

        used_strategies = set()
        current_quality = initial_quality
        doubt_hint = ""

        for i in range(self.MAX_ITERATIONS):
            if time.time() - start_time > self.MAX_TOTAL_SECONDS:
                logger.info(f"ReAct: 总耗时超{self.MAX_TOTAL_SECONDS:.0f}s，停止迭代")
                break
            if current_quality >= self.FITNESS_THRESHOLD:
                logger.info(f"ReAct: 适应度{current_quality:.0f}已达标，停止迭代")
                break

            doubt_result = self._self_doubt(
                result.final_response, candidates, fitness_score, query
            )
            if doubt_result.doubts:
                doubt_hint = doubt_result.recommended_strategy_hint
                doubt_summary = "; ".join(f"{d.severity}:{d.description[:30]}" for d in doubt_result.doubts[:3])
                logger.info(f"ReAct: 自我质疑发现{len(doubt_result.doubts)}个疑点(penalty={doubt_result.penalty:.2f}): {doubt_summary}")
                if emit_fn:
                    emit_fn("step", {
                        "phase": f"自我质疑",
                        "status": "reflecting",
                        "detail": f"发现{len(doubt_result.doubts)}个疑点: {doubt_summary}"
                    })

            available = [s for s in self.STRATEGY_ORDER if s not in used_strategies]
            if not available:
                logger.info("ReAct: 无更多可用策略，停止迭代")
                break

            strategy = self._select_strategy(available, candidates, used_strategies, doubt_hint)
            used_strategies.add(strategy)

            iter_start = time.time()

            if emit_fn:
                emit_fn("step", {
                    "phase": f"ReAct迭代{i+1}",
                    "status": "running",
                    "detail": f"Reason: 适应度{current_quality:.0f}不足 → 策略: {self.STRATEGY_DESCRIPTIONS[strategy]}"
                })

            thought = self._reason(query, current_quality, strategy, candidates, fitness_score)

            remaining_time = max(5.0, self.MAX_TOTAL_SECONDS - (time.time() - start_time))
            try:
                action_result = await asyncio.wait_for(
                    self._act(
                        strategy=strategy,
                        query=query,
                        candidates=candidates,
                        intent_type=intent_type,
                        conversation_context=conversation_context,
                        truth_insights=truth_insights,
                        fetch_ollama_fn=fetch_ollama_fn,
                        fetch_external_fn=fetch_external_fn,
                        fetch_knowledge_fn=fetch_knowledge_fn,
                        fetch_experience_fn=fetch_experience_fn,
                        self_reason_fn=self_reason_fn,
                    ),
                    timeout=remaining_time,
                )
            except asyncio.TimeoutError:
                logger.warning(f"ReAct: _act超时({remaining_time:.0f}s)，跳过此策略")
                break

            new_candidates = action_result.get("candidates", [])
            new_response = action_result.get("response", "")
            new_quality_raw = action_result.get("quality", 0)

            observed_quality = new_quality_raw
            if new_response and fitness_fn:
                try:
                    fit = await fitness_fn(query, new_response)
                    if fit:
                        observed_quality = fit.final_score
                except Exception:
                    pass

            improved = observed_quality > current_quality + self.MIN_IMPROVEMENT

            iter_duration = (time.time() - iter_start) * 1000

            iteration = ReActIteration(
                iter_num=i + 1,
                thought=thought,
                action=strategy,
                action_input={"strategy": strategy, "query": query[:100]},
                observation=f"获得{len(new_candidates)}个新候选, 质量从{current_quality:.0f}→{observed_quality:.0f}",
                quality=observed_quality,
                duration_ms=iter_duration,
                improved=improved,
            )
            result.iterations.append(iteration)

            if improved and new_response:
                result.final_response = new_response
                result.final_quality = observed_quality
                current_quality = observed_quality
                if new_candidates:
                    candidates.extend(new_candidates)

            if emit_fn:
                status = "改善 ✅" if improved else "未显著改善"
                emit_fn("step", {
                    "phase": f"ReAct迭代{i+1}",
                    "status": "done",
                    "detail": f"策略:{self.STRATEGY_DESCRIPTIONS[strategy]} | {status} | 适应度{current_quality:.0f}"
                })

        result.total_iterations = len(result.iterations)
        result.improved = result.final_quality > initial_quality
        result.strategies_used = list(used_strategies)
        result.total_duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"ReAct完成: {result.total_iterations}次迭代, "
            f"质量{initial_quality:.0f}→{result.final_quality:.0f}, "
            f"改善={result.improved}, 策略={result.strategies_used}"
        )

        self._record_to_trajectory(query, result, intent_type, initial_quality)

        return result

    def _select_strategy(
        self,
        available: List[str],
        candidates: List[Dict],
        used_strategies: set,
        doubt_hint: str = "",
    ) -> str:
        failed_sources = set()
        for c in candidates:
            src = c.get("source", "")
            q = c.get("quality", 0)
            if q < 40 and src:
                failed_sources.add(src)

        if doubt_hint and doubt_hint in available and doubt_hint not in used_strategies:
            logger.info(f"ReAct: 自我质疑推荐策略: {doubt_hint}")
            return doubt_hint

        if not failed_sources:
            return available[0]

        strategy_scores = {}
        for strat in available:
            score = 0
            for fsrc in failed_sources:
                fallbacks = self.FALLBACK_MAP.get(fsrc, [])
                if strat in fallbacks:
                    idx = fallbacks.index(strat)
                    score += (len(fallbacks) - idx) * 10
            strategy_scores[strat] = score

        best_strat = max(strategy_scores, key=strategy_scores.get)
        if strategy_scores[best_strat] > 0:
            logger.info(f"ReAct: 动态策略选择: {best_strat} (失败源:{failed_sources}, 得分:{strategy_scores})")
            return best_strat

        return available[0]

    def _reason(
        self,
        query: str,
        current_quality: float,
        strategy: str,
        candidates: List[Dict],
        fitness_score: Any,
    ) -> str:
        sources = set(c.get("source", "") for c in candidates if c.get("response"))
        failed_sources = set()
        for c in candidates:
            src = c.get("source", "")
            q = c.get("quality", 0)
            if q < 40 and src:
                failed_sources.add(src)

        missing = []
        if not any("Ollama" in s or "模型" in s for s in sources):
            missing.append("本地模型")
        if not any("外部" in s or "DeepSeek" in s for s in sources):
            missing.append("外部模型")
        if not any("知识" in s for s in sources):
            missing.append("知识库")
        if not any("经验" in s for s in sources):
            missing.append("经验池")

        issues = []
        if fitness_score:
            if hasattr(fitness_score, 'objective_score') and fitness_score.objective_score < 50:
                issues.append("客观分低(事实可能不准)")
            if hasattr(fitness_score, 'subjective_score') and fitness_score.subjective_score < 50:
                issues.append("主观分低(回答不够完整)")

        fallback_reason = ""
        for fsrc in failed_sources:
            if fsrc in self.FALLBACK_MAP:
                fallbacks = self.FALLBACK_MAP[fsrc]
                if strategy in fallbacks:
                    fallback_reason = f"失败源:{fsrc}→降级策略:{strategy}"
                    break

        thought = (
            f"当前适应度{current_quality:.0f}不足60, "
            f"已尝试来源:{'+'.join(sources) if sources else '无'}, "
            f"失败来源:{'+'.join(failed_sources) if failed_sources else '无'}, "
            f"缺失来源:{'+'.join(missing) if missing else '无'}, "
            f"问题:{'+'.join(issues) if issues else '综合不足'}, "
            f"选择策略:{self.STRATEGY_DESCRIPTIONS[strategy]}"
            f"{', 降级原因:' + fallback_reason if fallback_reason else ''}"
        )
        return thought

    async def _act(
        self,
        strategy: str,
        query: str,
        candidates: List[Dict],
        intent_type: str = "",
        conversation_context: str = "",
        truth_insights: str = "",
        fetch_ollama_fn: Optional[Callable] = None,
        fetch_external_fn: Optional[Callable] = None,
        fetch_knowledge_fn: Optional[Callable] = None,
        fetch_experience_fn: Optional[Callable] = None,
        self_reason_fn: Optional[Callable] = None,
    ) -> Dict:
        new_candidates = []
        best_response = ""
        best_quality = 0

        if strategy == "tool_first":
            result = await self._strategy_tool_first(query, intent_type)
            if result:
                new_candidates.extend(result.get("candidates", []))
                if result.get("quality", 0) > best_quality:
                    best_response = result.get("response", "")
                    best_quality = result.get("quality", 0)

        elif strategy == "model_switch":
            result = await self._strategy_model_switch(
                query, candidates, conversation_context, truth_insights,
                fetch_ollama_fn, fetch_external_fn,
            )
            if result:
                new_candidates.extend(result.get("candidates", []))
                if result.get("quality", 0) > best_quality:
                    best_response = result.get("response", "")
                    best_quality = result.get("quality", 0)

        elif strategy == "cross_verify":
            result = await self._strategy_cross_verify(
                query, candidates, conversation_context, truth_insights,
                fetch_knowledge_fn, fetch_experience_fn, fetch_external_fn,
            )
            if result:
                new_candidates.extend(result.get("candidates", []))
                if result.get("quality", 0) > best_quality:
                    best_response = result.get("response", "")
                    best_quality = result.get("quality", 0)

        elif strategy == "deep_reason":
            result = await self._strategy_deep_reason(
                query, candidates, conversation_context, truth_insights,
                self_reason_fn,
            )
            if result:
                new_candidates.extend(result.get("candidates", []))
                if result.get("quality", 0) > best_quality:
                    best_response = result.get("response", "")
                    best_quality = result.get("quality", 0)

        return {
            "candidates": new_candidates,
            "response": best_response,
            "quality": best_quality,
        }

    async def _strategy_tool_first(self, query: str, intent_type: str = "") -> Optional[Dict]:
        try:
            from core.tool_registry import tool_registry, tool_executor

            plan = tool_registry.plan_tools(query, intent_type)
            if not plan:
                # 能力创造回路：无工具匹配时，尝试用行动解决问题
                logger.info(f"无工具匹配查询，启动能力创造回路: {query[:60]}")
                try:
                    from core.capability_creation_loop import capability_creation_loop
                    result = await capability_creation_loop.handle(
                        query, {"intent_type": intent_type, "strategy": "tool_first"}
                    )
                    if result.get("handled") and result.get("data"):
                        logger.info(f"能力创造回路成功: {str(result['data'])[:80]}")
                        return {
                            "candidates": [{
                                "source": "capability_creation",
                                "response": str(result["data"]),
                                "quality": 60,
                            }],
                            "response": str(result["data"]),
                            "quality": 60,
                        }
                except Exception as e:
                    logger.debug(f"能力创造回路执行失败: {e}")

                return None

            used = set()
            for c in getattr(self, '_prev_tool_results', []):
                used.add(c.get("source", ""))

            remaining = [t for t in plan if t not in used]
            if not remaining:
                remaining = plan[:3]

            results = await tool_executor.execute_parallel(
                remaining[:3],
                {"query": query, "intent_type": intent_type}
            )

            candidates = []
            best_resp = ""
            best_q = 0
            for tr in results:
                c = tr.to_candidate()
                if c:
                    candidates.append(c)
                    if c.get("quality", 0) > best_q:
                        best_resp = c.get("response", "")
                        best_q = c.get("quality", 0)

            self._prev_tool_results = candidates
            return {"candidates": candidates, "response": best_resp, "quality": best_q}

        except Exception as e:
            logger.debug(f"ReAct tool_first策略失败: {e}")
            return None

    async def _strategy_model_switch(
        self,
        query: str,
        candidates: List[Dict],
        conversation_context: str = "",
        truth_insights: str = "",
        fetch_ollama_fn: Optional[Callable] = None,
        fetch_external_fn: Optional[Callable] = None,
    ) -> Optional[Dict]:
        new_candidates = []
        best_resp = ""
        best_q = 0

        sources_tried = set(c.get("source", "") for c in candidates)

        if fetch_external_fn and not any("外部" in s or "DeepSeek" in s for s in sources_tried):
            try:
                ext = await fetch_external_fn(query, conversation_context=conversation_context, truth_insights=truth_insights)
                if ext and ext.get("response"):
                    new_candidates.append(ext)
                    if ext.get("quality", 0) > best_q:
                        best_resp = ext["response"]
                        best_q = ext.get("quality", 0)
            except Exception as e:
                logger.debug(f"ReAct 外部模型切换失败: {e}")

        if fetch_ollama_fn and not any("Ollama" in s for s in sources_tried):
            try:
                oll = await fetch_ollama_fn(query, conversation_context=conversation_context, truth_insights=truth_insights)
                if oll:
                    if isinstance(oll, list):
                        for item in oll:
                            if isinstance(item, dict) and item.get("response"):
                                new_candidates.append(item)
                                if item.get("quality", 0) > best_q:
                                    best_resp = item["response"]
                                    best_q = item.get("quality", 0)
                    elif isinstance(oll, dict) and oll.get("response"):
                        new_candidates.append(oll)
                        if oll.get("quality", 0) > best_q:
                            best_resp = oll["response"]
                            best_q = oll.get("quality", 0)
            except Exception as e:
                logger.debug(f"ReAct 本地模型切换失败: {e}")

        if not new_candidates:
            if fetch_ollama_fn:
                try:
                    oll = await fetch_ollama_fn(query, conversation_context=conversation_context, truth_insights=truth_insights)
                    if oll:
                        if isinstance(oll, list):
                            for item in oll:
                                if isinstance(item, dict) and item.get("response"):
                                    new_candidates.append(item)
                                    if item.get("quality", 0) > best_q:
                                        best_resp = item["response"]
                                        best_q = item.get("quality", 0)
                        elif isinstance(oll, dict) and oll.get("response"):
                            new_candidates.append(oll)
                            if oll.get("quality", 0) > best_q:
                                best_resp = oll["response"]
                                best_q = oll.get("quality", 0)
                except Exception:
                    pass

        if new_candidates:
            return {"candidates": new_candidates, "response": best_resp, "quality": best_q}
        return None

    async def _strategy_cross_verify(
        self,
        query: str,
        candidates: List[Dict],
        conversation_context: str = "",
        truth_insights: str = "",
        fetch_knowledge_fn: Optional[Callable] = None,
        fetch_experience_fn: Optional[Callable] = None,
        fetch_external_fn: Optional[Callable] = None,
    ) -> Optional[Dict]:
        new_candidates = []
        best_resp = ""
        best_q = 0

        verify_tasks = []

        if fetch_knowledge_fn:
            verify_tasks.append(("知识库", fetch_knowledge_fn(query)))
        if fetch_experience_fn:
            verify_tasks.append(("经验池", fetch_experience_fn(query)))
        if fetch_external_fn:
            verify_tasks.append(("外部模型", fetch_external_fn(query, conversation_context=conversation_context, truth_insights=truth_insights)))

        for name, task in verify_tasks:
            try:
                result = await task
                if isinstance(result, dict) and result.get("response"):
                    new_candidates.append(result)
                    if result.get("quality", 0) > best_q:
                        best_resp = result["response"]
                        best_q = result.get("quality", 0)
            except Exception as e:
                logger.debug(f"ReAct 交叉验证-{name}失败: {e}")

        if len(new_candidates) >= 2 and best_resp:
            responses = [c.get("response", "") for c in new_candidates if c.get("response")]
            if len(responses) >= 2:
                merged = self._simple_merge(query, responses)
                if merged:
                    best_resp = merged
                    best_q = min(best_q + 10, 100)

        if new_candidates:
            return {"candidates": new_candidates, "response": best_resp, "quality": best_q}
        return None

    async def _strategy_deep_reason(
        self,
        query: str,
        candidates: List[Dict],
        conversation_context: str = "",
        truth_insights: str = "",
        self_reason_fn: Optional[Callable] = None,
    ) -> Optional[Dict]:
        if not self_reason_fn:
            return None

        try:
            enhanced_context = conversation_context
            if truth_insights:
                enhanced_context = f"{conversation_context}\n[真谛洞察]{truth_insights}" if conversation_context else truth_insights

            existing_responses = [c.get("response", "") for c in candidates if c.get("response") and len(c.get("response", "")) > 50]
            if existing_responses:
                top_resp = existing_responses[0][:500]
                enhanced_context = f"{enhanced_context}\n[已有参考回答]{top_resp}" if enhanced_context else f"[已有参考回答]{top_resp}"

            result = await self_reason_fn(query, enhanced_context, truth_insights)
            if result and result.get("response"):
                quality = result.get("quality", 50)
                if len(result["response"]) > 100:
                    quality = min(quality + 5, 100)
                return {
                    "candidates": [result],
                    "response": result["response"],
                    "quality": quality,
                }
        except Exception as e:
            logger.debug(f"ReAct 深度推理失败: {e}")

        return None

    def _simple_merge(self, query: str, responses: List[str]) -> Optional[str]:
        if len(responses) < 2:
            return None

        sentences = set()
        for resp in responses:
            for s in resp.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n"):
                s = s.strip()
                if len(s) > 10:
                    sentences.add(s)

        if not sentences:
            return None

        common = []
        for s in sentences:
            count = sum(1 for r in responses if s[:20] in r)
            if count >= 2:
                common.append(s)

        if common:
            return "。".join(common[:5]) + "。"

        sorted_s = sorted(sentences, key=len, reverse=True)
        return "。".join(sorted_s[:5]) + "。"

    def _record_to_trajectory(
        self,
        query: str,
        result: ReActResult,
        intent_type: str,
        initial_quality: float,
    ):
        try:
            from core.trajectory_evolution import TrajectoryStore
            store = TrajectoryStore()

            steps = []
            decisions = []
            for it in result.iterations:
                steps.append({
                    "phase": f"ReAct-{it.action}",
                    "success": it.improved,
                    "detail": it.observation,
                    "duration_ms": int(it.duration_ms),
                    "source_path": it.action,
                })
                decisions.append({
                    "strategy": it.action,
                    "reason": it.thought[:200],
                    "quality_before": initial_quality if it.iter_num == 1 else result.iterations[it.iter_num - 2].quality if it.iter_num > 1 else initial_quality,
                    "quality_after": it.quality,
                    "improved": it.improved,
                })

            outcome = {
                "initial_quality": initial_quality,
                "final_quality": result.final_quality,
                "improved": result.improved,
                "total_iterations": result.total_iterations,
                "strategies_used": result.strategies_used,
            }

            store.store_trajectory(
                query=query,
                steps=steps,
                decisions=decisions,
                outcome=outcome,
                intent_type=intent_type or "unknown",
                route="react",
                fitness_score=result.final_quality,
                duration=result.total_duration_ms / 1000.0,
                generation=1,
                source="react_engine",
            )
            logger.debug(f"ReAct轨迹已记录: {result.total_iterations}次迭代, 改善={result.improved}")
        except Exception as e:
            logger.debug(f"ReAct轨迹记录跳过: {e}")


react_engine = ReActEngine()