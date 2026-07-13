"""
持续求解引擎 — "问题没有解决不了的，只有想不想得到方法"

核心理念：
  置信度/概率只决定尝试顺序，不决定放弃。
  失败不是终点，而是"我缺少什么"的信号。
  每次失败 → 分析原因 → 生成新方法 → 尝试 → 循环直到成功。

执行流程：
  1. 收集失败信息 → 分析"我缺少什么"
  2. 按优先级生成新方法：
     a. 自我推理（本质推理+真谛类推）
     b. 搜索经验库（相似问题的解决记录）
     c. 问其他模型（Ollama/外部API，但只取方法思路）
     d. 上网搜索（外部学习器）
     e. 构建工具（ToolSelfBuilder）
  3. 尝试执行新方法
  4. 成功 → 回顾整个流程，提炼能力
  5. 失败 → 回到步骤1，但换一种方法生成策略

安全边界：
  - 最多3轮循环（防止无限循环）
  - 每轮最多30秒
  - 人类可随时中断
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from loguru import logger


MAX_SOLVE_ROUNDS = 3
ROUND_TIMEOUT = 30


def analyze_failure(user_input: str, attempts: list) -> Dict:
    """分析失败原因：我缺少什么？"""
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
    """根据失败分析，生成新的解决方法。返回 (method_name, method_config)"""

    suggestions = failure_analysis["method_suggestions"]
    idx = min(round_num - 1, len(suggestions) - 1) if suggestions else 0
    method = suggestions[idx] if suggestions else "ask_other_model"

    if method == "deeper_reasoning":
        return "本质推理+真谛类推", {
            "type": "reasoning",
            "prompt": f"问题：{user_input}\n\n之前的方法都失败了（{', '.join(failure_analysis['failed_methods'][:3])}），原因：{failure_analysis['gap_detail']}。\n\n请从第一性原理出发，找到全新的解决思路。不要重复之前失败的方法。",
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
            "prompt": f"我在解决以下问题时遇到了困难，请给我解决思路（不是答案，是方法）：\n\n问题：{user_input}\n\n已尝试但失败的方法：{', '.join(failure_analysis['failed_methods'][:3])}\n失败原因：{failure_analysis['gap_detail']}\n\n请给出1-3种不同的解决思路。",
        }
    elif method == "search_internet":
        return "互联网搜索方法", {
            "type": "internet_search",
            "query": f"如何解决：{user_input[:80]}",
        }
    elif method == "execute_tool":
        return "直接执行工具", {
            "type": "tool_execution",
            "query": user_input,
        }
    elif method == "build_tool":
        return "构建专用工具", {
            "type": "tool_building",
            "need_description": f"解决'{user_input[:50]}'所需的工具",
        }
    elif method == "decompose_and_retry":
        return "分解问题逐步求解", {
            "type": "decompose",
            "prompt": f"问题：{user_input}\n\n直接解决失败，请将问题分解为2-3个更小的子问题，逐个解决。",
        }
    else:
        return "综合推理", {
            "type": "reasoning",
            "prompt": f"问题：{user_input}\n\n请从全新角度思考解决方法。",
            "truth_insights": truth_insights,
        }


async def execute_method(method_name: str, method_config: Dict, intent_type: str = "") -> Tuple[bool, str]:
    """执行一个解决方法，返回 (success, result_text)"""
    method_type = method_config.get("type", "")

    try:
        if method_type == "reasoning":
            from backend.services.path_handlers._shared import _run_sync
            from core.essence_reasoner import essence_reasoner
            prompt = method_config.get("prompt", "")
            insights = method_config.get("truth_insights", "")
            result = await _run_sync(
                essence_reasoner.reason, prompt, timeout=20, phase=f"持续求解-{method_name}"
            )
            if result and result.get("conclusion"):
                return True, result["conclusion"]
            return False, "本质推理未返回有效结论"

        elif method_type == "experience_search":
            from core.memory.layered_memory import layered_memory
            query = method_config.get("query", "")
            results = layered_memory.search_strategic(query, limit=5)
            if results:
                best = results[0]
                return True, best.get("content", best.get("response", str(best)))
            return False, "经验库中无相关记录"

        elif method_type == "ask_model":
            from backend.services.path_handlers._shared import _run_sync
            from adapters.llm.ollama_adapter import ollama_chat_request
            prompt = method_config.get("prompt", "")
            result = await _run_sync(
                ollama_chat_request, prompt, model_name="gemma-4-12B", timeout=25, phase=f"持续求解-{method_name}"
            )
            if result and result.get("response"):
                return True, result["response"]
            return False, "模型未返回有效方法"

        elif method_type == "internet_search":
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
            from core.learning.tool_builder import ToolSelfBuilder
            tb = ToolSelfBuilder()
            desc = method_config.get("need_description", "")
            tb.observe_need(description=desc)
            opportunities = tb.identify_tool_opportunities()
            if opportunities:
                build_result = tb.build_tool(opportunities[0])
                if build_result.success and build_result.tool and build_result.tool.implementation:
                    try:
                        tool_result = build_result.tool.implementation({"query": user_input})
                        if isinstance(tool_result, dict) and tool_result.get("success") and tool_result.get("data"):
                            return True, tool_result["data"]
                        elif isinstance(tool_result, dict) and tool_result.get("data"):
                            return True, str(tool_result["data"])
                    except Exception as te:
                        logger.error(f"新建工具执行失败: {te}")
                    return True, f"已构建工具{build_result.tool.name}，但首次执行未获得有效结果"
            return False, "工具构建失败"

        elif method_type == "decompose":
            from backend.services.path_handlers._shared import _run_sync
            from adapters.llm.ollama_adapter import ollama_chat_request
            prompt = method_config.get("prompt", "")
            result = await _run_sync(
                ollama_chat_request, prompt, model_name="gemma-4-12B", timeout=25, phase=f"持续求解-分解"
            )
            if result and result.get("response"):
                return True, result["response"]
            return False, "问题分解未返回有效结果"

        else:
            return False, f"未知方法类型: {method_type}"

    except asyncio.TimeoutError:
        return False, f"{method_name}执行超时"
    except Exception as e:
        return False, f"{method_name}执行异常: {str(e)[:100]}"


async def persistent_solve(
    user_input: str,
    attempts: list,
    conversation_context: str = "",
    truth_insights: str = "",
    emit_fn=None,
    intent_type: str = "",
) -> Tuple[str, list, bool]:
    """
    持续求解引擎：失败→分析→生成新方法→执行→回顾

    返回: (final_response, new_attempts, solved)
    """
    new_attempts = []
    solved = False
    final_response = ""

    for round_num in range(1, MAX_SOLVE_ROUNDS + 1):
        logger.info(f"🔄 持续求解第{round_num}轮: 分析失败原因...")

        failure = analyze_failure(user_input, attempts + new_attempts)

        if emit_fn:
            await emit_fn("step", {"phase": f"持续求解-R{round_num}", "status": "running",
                "detail": f"分析失败原因: {failure['gap_detail']}，尝试新方法..."})

        method_name, method_config = await generate_new_method(
            failure, user_input, round_num, conversation_context, truth_insights
        )

        logger.info(f"🔄 持续求解第{round_num}轮: 尝试「{method_name}」")

        success, result = await asyncio.wait_for(
            execute_method(method_name, method_config, intent_type=intent_type),
            timeout=ROUND_TIMEOUT,
        )

        new_attempts.append((method_name, success, result[:100] if result else ""))

        if success and result and len(result) > 20:
            solved = True
            final_response = result
            logger.info(f"✅ 持续求解成功: 第{round_num}轮「{method_name}」解决了问题")
            
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
                await emit_fn("step", {"phase": f"持续求解-R{round_num}", "status": "done",
                    "detail": f"✅ 「{method_name}」成功解决问题"})
            break
        else:
            logger.info(f"🔄 持续求解第{round_num}轮: 「{method_name}」失败 - {result[:60]}")
            if emit_fn:
                await emit_fn("step", {"phase": f"持续求解-R{round_num}", "status": "done",
                    "detail": f"「{method_name}」未解决，换方法继续..."})

    if not solved:
        logger.info(f"🔄 持续求解{MAX_SOLVE_ROUNDS}轮后仍未解决，生成有方向的回复")
        failure = analyze_failure(user_input, attempts + new_attempts)
        final_response = _craft_persistent_failure_response(user_input, attempts + new_attempts, failure)

    return final_response, new_attempts, solved


def _craft_persistent_failure_response(user_input: str, all_attempts: list, failure: Dict) -> str:
    """持续求解失败后，生成有方向的回复（不是放弃，是"我还需要什么"）"""
    tried_methods = [a[0] for a in all_attempts if isinstance(a, tuple) and len(a) >= 2]
    failed_methods = [a[0] for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
    successful_methods = [a[0] for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and a[1]]

    parts = []
    parts.append(f"关于「{user_input[:50]}」，我尝试了{len(all_attempts)}种方法：")

    if successful_methods:
        parts.append(f"  ✅ 部分成功：{', '.join(successful_methods[:3])}")
    parts.append(f"  ❌ 未完全解决：{', '.join(failed_methods[:4])}")
    parts.append("")
    parts.append(f"🔍 核心困难：{failure['gap_detail']}")
    parts.append("")
    parts.append("💡 我需要：")

    gap = failure["gap_type"]
    if gap == "capability_gap":
        parts.append("  • 新的工具或能力来直接操作（我会尝试构建）")
        parts.append("  • 你可以告诉我具体用什么工具/命令能达到目的")
    elif gap == "knowledge_gap":
        parts.append("  • 更多背景信息或领域知识")
        parts.append("  • 你可以提供相关文档或参考资料")
    elif gap == "execution_gap":
        parts.append("  • 直接在本地执行操作（我正在学习如何做到）")
        parts.append("  • 你可以告诉我具体的执行步骤")
    elif gap == "time_constraint":
        parts.append("  • 更简洁的解决路径")
        parts.append("  • 你可以简化问题或分步提问")
    else:
        parts.append("  • 换个角度描述问题")
        parts.append("  • 提供更多上下文信息")

    parts.append("")
    parts.append("🔄 此问题已记入学习清单，我会持续寻找解决方法。")

    return "\n".join(parts)


async def review_solution(
    user_input: str,
    final_response: str,
    all_attempts: list,
    solved: bool,
):
    """
    成功后回顾：提炼能力+固化经验+评估是否有更优方法
    """
    if not solved:
        return

    try:
        from core.skill_emergence import skill_emergence
        skill_emergence.analyze_and_learn(user_input, all_attempts, final_response, elapsed=0)
        logger.info("📋 回顾: 技能已提炼")
    except Exception as e:
        logger.warning(f"技能提炼跳过: {e}")

    try:
        from core.truth_accumulator import truth_accumulator
        truth_accumulator.accumulate(user_input, all_attempts, final_response)
        logger.info("📋 回顾: 真谛已积累")
    except Exception as e:
        logger.warning(f"真谛积累跳过: {e}")

    try:
        from core.memory.layered_memory import layered_memory
        successful = [a for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and a[1]]
        if successful:
            best_method = successful[-1][0]
            layered_memory.record_tool_usage(
                best_method, user_input, True, 80, 0
            )
            logger.info(f"📋 回顾: 最优方法「{best_method}」已记录")
    except Exception as e:
        logger.warning(f"经验记录跳过: {e}")

    try:
        from core.learning.capability_gap_learner import capability_gap_learner
        failed = [a for a in all_attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
        if failed and len(failed) > len(successful):
            capability_gap_learner.observe_gap(
                gap_type="method_efficiency",
                description=f"解决'{user_input[:30]}'时{len(failed)}次失败才成功，可能有更优方法",
            )
            logger.info("📋 回顾: 方法效率观察已记录")
    except Exception as e:
        logger.warning(f"方法效率观察跳过: {e}")

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
            logger.info(f"📋 回顾: 方法论骨架已沉淀(skeleton_id={skeleton.get('skeleton_id', '?')})")
            try:
                from core.skill_emergence import SkillEmergence
                se = SkillEmergence()
                se.add_reflex_pattern(
                    trigger=user_input[:60],
                    solution_path=skeleton.get("steps_summary", ""),
                    confidence=0.6,
                )
                logger.info("📋 回顾: 骨架已注册为本能模式(置信度0.6)")
            except Exception as se2:
                logger.warning(f"骨架本能注册跳过: {se2}")
    except Exception as e:
        logger.warning(f"方法论骨架沉淀跳过: {e}")