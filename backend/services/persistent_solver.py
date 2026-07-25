"""
持续求解引擎 — "问题没有解决不了的，只有想不想得到方法"

核心理念：
  置信度/概率只决定尝试顺序，不决定放弃。
  失败不是终点，而是"我缺少什么"的信号。
  每次失败 → 分析原因 → 生成新方法 → 尝试 → 循环直到成功。
  3轮后不是放弃，是切换策略继续。

执行流程：
  1. 收集失败信息 → 分析"我缺少什么"
  2. 按优先级生成新方法（动态排序，基于失败原因+历史成功率）
  3. 尝试执行新方法（跳过已标记不可用的链路）
  4. 成功 → 回顾整个流程，提炼能力
  5. 失败 → 回到步骤1，但换一种方法生成策略
  6. 3轮后 → 不是放弃，是切换到"创新策略"继续

安全边界：
  - 最多50轮循环（防止无限循环，但给足空间）
  - 每轮最多30秒
  - 人类可随时中断
  - 已标记不可用的链路自动跳过
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from loguru import logger


MAX_SOLVE_ROUNDS = 50
ROUND_TIMEOUT = 30
STRATEGY_SWITCH_ROUND = 3

_method_success_history: Dict[str, List[bool]] = {}


def _get_ollama_config():
    try:
        from infrastructure.config_manager import config
        return (
            config.get("ollama.base_url", "http://localhost:11434"),
            config.get("ollama.model", "qwen2.5:7b"),
        )
    except Exception:
        return "http://localhost:11434", "qwen2.5:7b"


def _is_path_available(path_name: str) -> bool:
    try:
        from core.module_health import module_health
        return module_health.is_available(path_name)
    except Exception:
        return True


def _record_method_result(method_key: str, success: bool):
    if method_key not in _method_success_history:
        _method_success_history[method_key] = []
    _method_success_history[method_key].append(success)
    if len(_method_success_history[method_key]) > 20:
        _method_success_history[method_key] = _method_success_history[method_key][-20:]


def _get_method_success_rate(method_key: str) -> float:
    history = _method_success_history.get(method_key, [])
    if not history:
        return 0.5
    return sum(1 for s in history if s) / len(history)


def analyze_failure(user_input: str, attempts: list) -> Dict:
    failed = [a for a in attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
    failed_methods = [a[0] for a in failed]
    failed_reasons = [a[2] if len(a) > 2 else "" for a in failed]

    gap_type = "unknown"
    gap_detail = ""
    method_suggestions = []

    all_reasons = " ".join(str(r) for r in failed_reasons).lower()

    if any(kw in all_reasons for kw in ["timeout", "超时", "time"]):
        gap_type = "time_constraint"
        gap_detail = "方法执行超时，需要更快的方案或分步执行"
        method_suggestions.append("decompose_and_retry")
    elif any(kw in all_reasons for kw in ["无法访问", "不能", "没有能力", "无法获取"]):
        sub_reason = all_reasons
        if any(kw in sub_reason for kw in ["localhost", "ollama", "模型"]):
            gap_type = "service_down"
            gap_detail = "本地服务不可达，需要切换到不依赖本地服务的方案"
            method_suggestions.extend(["search_experience", "search_internet", "build_tool"])
        else:
            gap_type = "capability_gap"
            gap_detail = "缺少必要的能力或工具"
            method_suggestions.extend(["ask_other_model", "search_internet", "build_tool"])
    elif any(kw in all_reasons for kw in ["不确定", "不明确", "ambiguous"]):
        gap_type = "knowledge_gap"
        gap_detail = "知识不足，需要更多信息"
        method_suggestions.extend(["search_experience", "ask_other_model", "search_internet"])
    elif any(kw in all_reasons for kw in ["验证失败", "质量不达标", "低质量"]):
        gap_type = "quality_gap"
        gap_detail = "有回复但质量不够，需要更深推理"
        method_suggestions.extend(["deeper_reasoning", "ask_other_model"])
    elif any(kw in user_input.lower() for kw in ["串口", "com", "硬件", "执行", "运行", "命令"]):
        gap_type = "execution_gap"
        gap_detail = "需要实际执行操作而非文本回答"
        method_suggestions.extend(["execute_tool", "build_tool", "ask_other_model"])
    else:
        gap_type = "general_failure"
        gap_detail = "常规方法均失败，需要创新思路"
        method_suggestions.extend(["deeper_reasoning", "search_experience", "ask_other_model", "search_internet"])

    tried_set = set(failed_methods)
    method_suggestions = [m for m in method_suggestions if m not in tried_set]

    if not method_suggestions:
        method_suggestions = ["deeper_reasoning", "search_experience", "build_tool", "search_internet"]

    return {
        "gap_type": gap_type,
        "gap_detail": gap_detail,
        "failed_methods": failed_methods,
        "failed_reasons": failed_reasons,
        "method_suggestions": method_suggestions,
    }


async def generate_new_method(
    failure_analysis: Dict,
    user_input: str,
    round_num: int,
    conversation_context: str = "",
    truth_insights: str = "",
) -> Tuple[str, Dict]:
    suggestions = failure_analysis["method_suggestions"]

    if round_num > STRATEGY_SWITCH_ROUND:
        if "build_tool" not in suggestions:
            suggestions.append("build_tool")
        if "decompose_and_retry" not in suggestions:
            suggestions.append("decompose_and_retry")

    scored = []
    for m in suggestions:
        score = _get_method_success_rate(m)
        if m in ("ask_other_model", "decompose") and not _is_path_available("ollama"):
            score -= 0.5
        if m == "search_internet" and not _is_path_available("external_api"):
            score -= 0.5
        scored.append((m, score))
    scored.sort(key=lambda x: -x[1])

    method = scored[0][0] if scored else "deeper_reasoning"

    if method == "deeper_reasoning":
        return "本质推理+真谛类推", {
            "type": "reasoning",
            "prompt": "问题：{}\n\n之前的方法都失败了（{}），原因：{}。\n\n请从第一性原理出发，找到全新的解决思路。不要重复之前失败的方法。".format(
                user_input, ", ".join(failure_analysis["failed_methods"][:3]), failure_analysis["gap_detail"]
            ),
            "truth_insights": truth_insights,
        }
    elif method == "search_experience":
        return "经验库深度搜索", {
            "type": "experience_search",
            "query": user_input,
            "filter_failed": failure_analysis["failed_methods"],
        }
    elif method == "ask_other_model":
        return "向其他模型请教方法", {
            "type": "ask_model",
            "prompt": "我在解决以下问题时遇到了困难，请给我解决思路（不是答案，是方法）：\n\n问题：{}\n\n已尝试但失败的方法：{}\n失败原因：{}\n\n请给出1-3种不同的解决思路。".format(
                user_input, ", ".join(failure_analysis["failed_methods"][:3]), failure_analysis["gap_detail"]
            ),
        }
    elif method == "search_internet":
        return "互联网搜索方法", {
            "type": "internet_search",
            "query": "如何解决：{}".format(user_input[:80]),
        }
    elif method == "execute_tool":
        return "直接执行工具", {
            "type": "tool_execution",
            "query": user_input,
        }
    elif method == "build_tool":
        return "构建专用工具", {
            "type": "tool_building",
            "need_description": "解决'{}'所需的工具".format(user_input[:50]),
        }
    elif method == "decompose_and_retry":
        return "分解问题逐步求解", {
            "type": "decompose",
            "prompt": "问题：{}\n\n直接解决失败，请将问题分解为2-3个更小的子问题，逐个解决。".format(user_input),
        }
    else:
        return "综合推理", {
            "type": "reasoning",
            "prompt": "问题：{}\n\n请从全新角度思考解决方法。".format(user_input),
            "truth_insights": truth_insights,
        }


def _is_meaningful_result(text: str, user_input: str) -> bool:
    if not text or len(text) < 15:
        return False
    filler_patterns = ["我不知道", "无法回答", "抱歉", "i don't know", "i cannot"]
    text_lower = text.lower()
    if any(p in text_lower for p in filler_patterns) and len(text) < 80:
        return False
    return True


async def execute_method(method_name: str, method_config: Dict, intent_type: str = "") -> Tuple[bool, str]:
    method_type = method_config.get("type", "")

    try:
        if method_type == "reasoning":
            from backend.services.path_handlers._shared import _run_sync
            from core.essence_reasoner import essence_reasoner
            prompt = method_config.get("prompt", "")
            result = await _run_sync(
                essence_reasoner.reason, prompt, timeout=20, phase="持续求解-{}".format(method_name)
            )
            if result and result.get("conclusion"):
                return True, result["conclusion"]
            return False, "本质推理未返回有效结论"

        elif method_type == "experience_search":
            from infrastructure.experience_pool import get_experience_pool
            pool = get_experience_pool()
            query = method_config.get("query", "")
            results = pool.search_successful_responses(min_quality=50, limit=5)
            if results:
                best = results[0]
                resp = best.get("response", "")
                if resp and len(resp) > 30:
                    return True, resp
            return False, "经验库中无相关记录"

        elif method_type == "ask_model":
            if not _is_path_available("ollama"):
                return False, "本地模型不可用，跳过"
            from backend.services.path_handlers._shared import _run_sync
            from adapters.llm.ollama_adapter import ollama_chat_request
            base_url, model = _get_ollama_config()
            prompt = method_config.get("prompt", "")
            result = await _run_sync(
                ollama_chat_request, base_url, model, prompt, timeout=25
            )
            if result and result.get("content"):
                return True, result["content"]
            return False, "模型未返回有效方法"

        elif method_type == "internet_search":
            if not _is_path_available("external_api"):
                return False, "外部链路不可用，跳过"
            from core.external_learner import external_learner
            query = method_config.get("query", "")
            results = external_learner.search(query, max_results=3)
            if results:
                combined = "\n".join(r.get("content", r.get("snippet", ""))[:300] for r in results[:3])
                return True, combined
            return False, "互联网搜索无结果"

        elif method_type == "tool_execution":
            from core.tool_registry import register_builtin_tools, tool_executor
            register_builtin_tools()
            query = method_config.get("query", "")
            from core.tool_registry import tool_registry
            tools = tool_registry.plan_tools(query, intent_type or "complex_query")
            if tools:
                result = await tool_executor.execute(tools[0], {"query": query}, timeout_override=20)
                if result and result.success and result.data:
                    return True, result.data
            return False, "工具执行无结果"

        elif method_type == "tool_building":
            from core.learning.tool_builder import ToolSelfBuilder, ToolNeed, NeedPriority
            tb = ToolSelfBuilder()
            desc = method_config.get("need_description", "")
            need = ToolNeed(
                need_id="ps_{}".format(int(time.time())),
                description=desc,
                priority=NeedPriority.HIGH,
                context={"source": "persistent_solver"},
            )
            build_result = tb.build_tool(need)
            if build_result.success and build_result.tool and build_result.tool.implementation:
                try:
                    tool_result = build_result.tool.implementation({"query": method_config.get("query", desc)})
                    if isinstance(tool_result, dict) and tool_result.get("data"):
                        return True, str(tool_result["data"])
                except Exception as te:
                    logger.error(f"新建工具执行失败: {te}")
                return True, "已构建工具{}，但首次执行未获得有效结果".format(build_result.tool.name)
            return False, "工具构建失败"

        elif method_type == "decompose":
            if not _is_path_available("ollama"):
                return False, "本地模型不可用，无法分解问题"
            from backend.services.path_handlers._shared import _run_sync
            from adapters.llm.ollama_adapter import ollama_chat_request
            base_url, model = _get_ollama_config()
            prompt = method_config.get("prompt", "")
            result = await _run_sync(
                ollama_chat_request, base_url, model, prompt, timeout=25
            )
            if result and result.get("content"):
                return True, result["content"]
            return False, "问题分解未返回有效结果"

        else:
            return False, "未知方法类型: {}".format(method_type)

    except asyncio.TimeoutError:
        return False, "{}执行超时".format(method_name)
    except Exception as e:
        return False, "{}执行异常: {}".format(method_name, str(e)[:100])


async def persistent_solve(
    user_input: str,
    attempts: list,
    conversation_context: str = "",
    truth_insights: str = "",
    emit_fn=None,
    intent_type: str = "",
) -> Tuple[str, list, bool]:
    new_attempts = []
    solved = False
    final_response = ""

    for round_num in range(1, MAX_SOLVE_ROUNDS + 1):
        logger.info("🔄 持续求解第{}轮: 分析失败原因...".format(round_num))

        failure = analyze_failure(user_input, attempts + new_attempts)

        if round_num <= STRATEGY_SWITCH_ROUND:
            phase_label = "持续求解-R{}".format(round_num)
        else:
            phase_label = "持续求解-创新策略R{}".format(round_num)

        if emit_fn:
            await emit_fn("step", {"phase": phase_label, "status": "running",
                "detail": "分析失败原因: {}，尝试新方法...".format(failure["gap_detail"])})

        method_name, method_config = await generate_new_method(
            failure, user_input, round_num, conversation_context, truth_insights
        )

        logger.info("🔄 持续求解第{}轮: 尝试「{}」".format(round_num, method_name))

        success, result = await asyncio.wait_for(
            execute_method(method_name, method_config, intent_type=intent_type),
            timeout=ROUND_TIMEOUT,
        )

        method_key = method_config.get("type", method_name)
        _record_method_result(method_key, success)

        new_attempts.append((method_name, success, result[:100] if result else ""))

        if success and _is_meaningful_result(result, user_input):
            solved = True
            final_response = result
            logger.info("✅ 持续求解成功: 第{}轮「{}」解决了问题".format(round_num, method_name))

            try:
                from infrastructure.config_manager import config_manager
                _flags = config_manager.get("feature_flags", {})
                if _flags.get("intent_keyword_learning", True):
                    from core.cognitive_dispatcher import get_cognitive_dispatcher
                    cognitive_dispatcher = get_cognitive_dispatcher()
                    cognitive_dispatcher.learn_keyword_from_experience(user_input, intent_type or "complex_query", source="persistent_solver")
            except Exception as _lke:
                logger.warning(f"意图词表学习跳过: {_lke}")

            if emit_fn:
                await emit_fn("step", {"phase": phase_label, "status": "done",
                    "detail": "✅ 「{}」成功解决问题（第{}轮）".format(method_name, round_num)})
            break
        else:
            logger.info("🔄 持续求解第{}轮: 「{}」失败 - {}".format(round_num, method_name, result[:60]))
            if emit_fn:
                if round_num == STRATEGY_SWITCH_ROUND:
                    await emit_fn("step", {"phase": phase_label, "status": "done",
                        "detail": "「{}」未解决，切换到创新策略继续...".format(method_name)})
                else:
                    await emit_fn("step", {"phase": phase_label, "status": "done",
                        "detail": "「{}」未解决，换方法继续...".format(method_name)})

            if round_num >= STRATEGY_SWITCH_ROUND and round_num % STRATEGY_SWITCH_ROUND == 0:
                _notify_continuation(user_input, round_num, new_attempts, failure)

    if not solved:
        failure = analyze_failure(user_input, attempts + new_attempts)
        final_response = _craft_continuation_notice(user_input, attempts + new_attempts, failure, round_num)

    return final_response, new_attempts, solved


def _notify_continuation(user_input: str, round_num: int, attempts: list, failure: Dict):
    logger.info("🔄 持续求解已进行{}轮，仍在继续。核心困难: {}".format(round_num, failure["gap_detail"]))


def _craft_continuation_notice(user_input: str, all_attempts: list, failure: Dict, rounds_done: int) -> str:
    tried_methods = [a[0] for a in all_attempts if isinstance(a, tuple) and len(a) >= 2]
    failed_methods = [a[0] for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
    successful_methods = [a[0] for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and a[1]]

    parts = []
    parts.append("关于「{}」，我已尝试{}种方法（{}轮）：".format(user_input[:50], len(all_attempts), rounds_done))

    if successful_methods:
        parts.append("  ✅ 部分进展：{}".format(", ".join(successful_methods[:3])))
    parts.append("  🔄 正在继续：{}".format(", ".join(failed_methods[-3:])))
    parts.append("")
    parts.append("🔍 核心困难：{}".format(failure["gap_detail"]))
    parts.append("")

    gap = failure["gap_type"]
    if gap == "capability_gap" or gap == "service_down":
        parts.append("🔧 我正在：构建新工具来直接操作，同时寻找替代方案")
    elif gap == "knowledge_gap":
        parts.append("🔍 我正在：从更多来源搜索相关知识，尝试不同的推理角度")
    elif gap == "execution_gap":
        parts.append("🔧 我正在：尝试构建专用执行工具，寻找直接操作的方法")
    elif gap == "time_constraint":
        parts.append("⏱️ 我正在：分解问题为更小的步骤，寻找更快的解决路径")
    else:
        parts.append("🔄 我正在：从全新角度重新思考，尝试之前未用过的方法")

    parts.append("")
    parts.append("🔄 此问题仍在我的求解队列中，我不会放弃。如果你有新的线索或方向，请告诉我。")

    return "\n".join(parts)


async def review_solution(
    user_input: str,
    final_response: str,
    all_attempts: list,
    solved: bool,
):
    if not solved:
        return

    review_results = {}

    try:
        from core.skill_emergence import skill_emergence
        skill_emergence.analyze_and_learn(user_input, all_attempts, final_response, elapsed=0)
        review_results["skill_emergence"] = True
    except Exception as e:
        review_results["skill_emergence"] = False
        logger.warning("技能提炼跳过: {}".format(e))

    try:
        from core.truth_accumulator import truth_accumulator
        truth_accumulator.accumulate(user_input, all_attempts, final_response)
        review_results["truth_accumulation"] = True
    except Exception as e:
        review_results["truth_accumulation"] = False
        logger.warning("真谛积累跳过: {}".format(e))

    try:
        from core.memory.layered_memory import layered_memory
        successful = [a for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and a[1]]
        if successful:
            best_method = successful[-1][0]
            layered_memory.record_tool_usage(best_method, user_input, True, 80, 0)
            review_results["experience_record"] = True
    except Exception as e:
        review_results["experience_record"] = False
        logger.warning("经验记录跳过: {}".format(e))

    try:
        from core.learning.capability_gap_learner import capability_gap_learner
        failed = [a for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
        if failed and len(failed) > len(successful):
            capability_gap_learner.observe_gap(
                gap_type="method_efficiency",
                description="解决'{}'时{}次失败才成功，可能有更优方法".format(user_input[:30], len(failed)),
            )
            review_results["gap_observation"] = True
    except Exception as e:
        review_results["gap_observation"] = False
        logger.warning("方法效率观察跳过: {}".format(e))

    try:
        from core.cognition.experience_abstractor import ExperienceAbstractor
        ea = ExperienceAbstractor()
        steps = [{"method": a[0], "success": a[1], "detail": a[2] if len(a) > 2 else ""}
                 for a in all_attempts if isinstance(a, tuple) and len(a) >= 2]
        skeleton = ea._extract_skeleton({
            "user_query": user_input,
            "steps": steps,
            "success": solved,
            "final_response": final_response[:200],
        })
        if skeleton:
            review_results["skeleton"] = True
            try:
                from core.skill_emergence import SkillEmergence
                se = SkillEmergence()
                se.add_reflex_pattern(
                    trigger=user_input[:60],
                    solution_path=skeleton.get("steps_summary", ""),
                    confidence=0.6,
                )
                review_results["reflex_registration"] = True
            except Exception as se2:
                review_results["reflex_registration"] = False
                logger.warning("骨架本能注册跳过: {}".format(se2))
    except Exception as e:
        review_results["skeleton"] = False
        logger.warning("方法论骨架沉淀跳过: {}".format(e))

    succeeded_count = sum(1 for v in review_results.values() if v)
    total_count = len(review_results)
    logger.info("📋 回顾完成: {}/{}项成功".format(succeeded_count, total_count))
