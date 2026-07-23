from loguru import logger

from backend.services.orchestrator_helpers import r4_self_check as _r4_self_check
from backend.services.path_handlers._shared import _run_sync


async def discover_methodology(
    user_input: str, intent_type: str, methodology: dict,
    _continuity_signal: dict, _rule_actions: list,
    attempts: list, final_response: str,
) -> dict:
    events = []
    essence_gate_result = None
    truth_insights = ""
    capability_gap = None
    intent_type_override = None
    should_return = False
    return_events = []

    try:
        from core.essence_reasoner import essence_reasoner
        essence_gate_result = essence_reasoner.essence_gate(user_input)
        events.append({"type": "step", "data": {"phase": "本质闸门", "status": "done",
            "detail": f"本质单元：{essence_gate_result['essence_unit'][:40]} | 策略：{essence_gate_result['dispatch_strategy']}"}})
        if essence_gate_result["is_paradox"]:
            attempts.append(("本质闸门", True, f"悖论识别→{essence_gate_result['dispatch_strategy']}"))
        else:
            attempts.append(("本质闸门", True, essence_gate_result['essence_unit'][:40]))
    except ImportError:
        events.append({"type": "step", "data": {"phase": "本质闸门", "status": "done", "detail": "本质闸门未安装，使用默认策略"}})

    from backend.services.intent_service import discover_methodology as _discover_methodology
    _discovered_methodology = _discover_methodology(user_input, intent_type)
    methodology.update(_discovered_methodology)
    if essence_gate_result:
        methodology["strategy"] = essence_gate_result["dispatch_strategy"]
        if essence_gate_result["is_paradox"]:
            methodology["need_essence_reasoning"] = True

    if _continuity_signal:
        if _continuity_signal.get("topic_drift"):
            methodology["topic_drift"] = True
            methodology["drift_direction"] = _continuity_signal.get("drift_direction", "")
        if _continuity_signal.get("reference_needs_resolution"):
            methodology["reference_resolution"] = _continuity_signal.get("reference_text", "")
        if _continuity_signal.get("continuity_hint"):
            methodology["continuity_hint"] = _continuity_signal["continuity_hint"]

    try:
        from core.truth_accumulator import truth_accumulator
        domain = essence_gate_result.get("domain", "通用") if essence_gate_result else "通用"
        truth_insights = truth_accumulator.get_applicable_insights(user_input, domain)
        if truth_insights:
            applicable = truth_accumulator.analogize(user_input, domain)
            insight_names = [a["name"] for a in applicable[:3]]
            events.append({"type": "step", "data": {"phase": "真谛类推", "status": "done", "detail": f"类推适用：{', '.join(insight_names)}"}})
            attempts.append(("真谛类推", True, f"{len(applicable)}条洞察"))
    except Exception:
        logger.warning("操作降级跳过")

    _field_prefer_reflex = methodology.get("field_prefer_reflex", False)
    _field_need_analogous = methodology.get("need_analogous_match", False)

    instinct_hit = None
    if _field_prefer_reflex:
        try:
            from core.skill_emergence import skill_emergence
            instinct_hit = skill_emergence.reflex_query(user_input)
            if instinct_hit:
                events.append({"type": "step", "data": {"phase": "本能查询", "status": "done",
                    "detail": f"⚡ 场域加速-本能触发: {instinct_hit['skill_name']} (置信度{instinct_hit['confidence']:.2f})"}})
                methodology["instinct_path"] = instinct_hit["solution_path"]
                methodology["instinct_skeleton"] = instinct_hit.get("skeleton", "")
        except Exception:
            logger.warning("操作降级跳过")
    else:
        try:
            from core.skill_emergence import skill_emergence
            instinct_hit = skill_emergence.reflex_query(user_input)
            if instinct_hit:
                events.append({"type": "step", "data": {"phase": "本能查询", "status": "done",
                    "detail": f"⚡ 本能触发: {instinct_hit['skill_name']} (置信度{instinct_hit['confidence']:.2f})"}})
                methodology["instinct_path"] = instinct_hit["solution_path"]
                methodology["instinct_skeleton"] = instinct_hit.get("skeleton", "")
        except Exception:
            logger.warning("操作降级跳过")

    if not instinct_hit:
        try:
            from core.cognition.experience_abstractor import ExperienceAbstractor
            _analogous_threshold = 0.4 if _field_need_analogous else 0.6
            skeleton_analogy = ExperienceAbstractor.find_analogous(user_input, threshold=_analogous_threshold)
            if skeleton_analogy:
                _boost_label = " (场域加速)" if _field_need_analogous else ""
                events.append({"type": "step", "data": {"phase": "骨架联想", "status": "done",
                    "detail": f"🧠 类比迁移{_boost_label}: {skeleton_analogy['skill_name']} (相似度{skeleton_analogy['similarity']:.2f})"}})
                methodology["analogous_skeleton"] = skeleton_analogy["skeleton"]
                methodology["analogous_path"] = skeleton_analogy["solution_path"]
        except Exception:
            logger.warning("操作降级跳过")

    try:
        from core.tool_registry import tool_registry
        applicable_tools = tool_registry.plan_tools(user_input, intent_type, methodology=methodology)
        if not applicable_tools and intent_type not in ("greeting", "confirmation", "simple_query"):
            capability_gap = f"解决'{user_input[:40]}'所需的工具"
            events.append({"type": "step", "data": {"phase": "能力评估", "status": "done",
                "detail": "⚠️ 检测到能力缺口: 无适用工具"}})
            methodology["capability_gap"] = capability_gap
    except Exception:
        logger.warning("操作降级跳过")

    _r4_result = _r4_self_check(user_input, intent_type, methodology, capability_gap)
    if _r4_result.get("warnings"):
        for _w in _r4_result["warnings"]:
            events.append({"type": "step", "data": {"phase": "三思后行", "status": "warning", "detail": _w}})
    if _r4_result.get("blocked"):
        final_response = _r4_result["block_reason"]
        events.append({"type": "step", "data": {"phase": "三思后行", "status": "done", "detail": f"🛑 行动被阻断: {_r4_result['block_reason']}"}})
        events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type}})
        should_return = True
        return {
            "methodology": methodology, "essence_gate_result": essence_gate_result,
            "truth_insights": truth_insights, "capability_gap": capability_gap,
            "intent_type_override": intent_type_override, "final_response": final_response,
            "should_return": should_return, "events": events,
        }
    if _r4_result.get("adjustments"):
        for _adj_key, _adj_val in _r4_result["adjustments"].items():
            methodology[_adj_key] = _adj_val

    try:
        from infrastructure.fact_store import fact_store
        fact_assertions = await _run_sync(fact_store.search_by_keywords, user_input, limit=5, timeout=5)
        if fact_assertions:
            fact_parts = []
            for fa in fact_assertions:
                fact_parts.append(f"- {fa['subject']} {fa['predicate']} {fa['object']} (置信度{fa['confidence']:.0%}, 来源:{fa['source']})")
            fact_context = "【事实锚点-客观验证】\n" + "\n".join(fact_parts)
            events.append({"type": "step", "data": {"phase": "事实锚点", "status": "done", "detail": f"检索到{len(fact_assertions)}条相关事实"}})
            attempts.append(("事实锚点", True, f"{len(fact_assertions)}条"))
        else:
            fact_context = ""
            events.append({"type": "step", "data": {"phase": "事实锚点", "status": "done", "detail": "无相关事实锚点"}})
    except Exception as e:
        logger.warning(f"事实锚点查询跳过: {e}")
        fact_context = ""

    if fact_context and not truth_insights:
        truth_insights = fact_context
    elif fact_context:
        truth_insights = fact_context + "\n" + truth_insights

    try:
        from core.memory.layered_memory import layered_memory
        lm_context = layered_memory.get_context_for_query(user_input)
        if lm_context["context"]:
            if truth_insights:
                truth_insights = lm_context["context"] + "\n" + truth_insights
            else:
                truth_insights = lm_context["context"]
            events.append({"type": "step", "data": {"phase": "分层记忆", "status": "done",
                "detail": f"战略{lm_context['strategic_count']}/程序{lm_context['procedural_count']}/工具{lm_context['tool_count']}"}})
    except Exception as e:
        logger.warning(f"分层记忆查询跳过: {e}")

    events.append({"type": "step", "data": {"phase": "方法论发现", "status": "done",
        "detail": f"解决策略：{methodology['strategy']} | 来源优先级：{' → '.join(methodology['source_priority'][:3])}"}})

    if _rule_actions:
        for _ra in _rule_actions[:3]:
            try:
                if _ra.startswith("prefer_model:"):
                    _preferred = _ra.split(":", 1)[1]
                    if _preferred not in methodology.get("source_priority", []):
                        methodology.setdefault("source_priority", []).insert(0, _preferred)
                elif _ra.startswith("reroute:"):
                    _alt = _ra.split(":", 1)[1]
                    methodology["strategy"] = _alt
                elif _ra.startswith("trigger_reflection"):
                    methodology.setdefault("force_reflection", True)
                elif _ra.startswith("set_intent:"):
                    _new_intent = _ra.split(":", 1)[1]
                    intent_type_override = _new_intent
            except Exception:
                logger.warning("操作降级跳过")

    try:
        from core.learning.capability_gap_learner import capability_gap_learner
        _capability_assessment = capability_gap_learner.assess_capability(user_input, intent_type, methodology)
        if _capability_assessment and _capability_assessment.get("gap_detected"):
            gap_type = _capability_assessment["gap_type"]
            events.append({"type": "thinking", "data": {
                "phase": f"我发现这个问题需要「{_capability_assessment['needed_capability']}」的能力，我正在想办法获得它",
                "gap_type": gap_type,
                "resolution_plan": _capability_assessment.get("resolution_plan", ""),
            }})
            events.append({"type": "step", "data": {"phase": "能力评估", "status": "running",
                "detail": f"检测到能力缺失: {gap_type}，正在获取能力..."}})

            _acquired = await capability_gap_learner.acquire_capability(_capability_assessment)
            if _acquired:
                events.append({"type": "step", "data": {"phase": "能力评估", "status": "done",
                    "detail": f"已获得能力: {_acquired}"}})
                methodology = capability_gap_learner.update_methodology(methodology, _capability_assessment)
            else:
                events.append({"type": "step", "data": {"phase": "能力评估", "status": "done",
                    "detail": f"能力获取进行中: {_capability_assessment.get('resolution_plan', '探索中')}"}})
        else:
            events.append({"type": "step", "data": {"phase": "能力评估", "status": "done", "detail": "能力充足，开始执行"}})
    except Exception as _ce:
        logger.warning(f"能力评估跳过: {_ce}")

    return {
        "methodology": methodology, "essence_gate_result": essence_gate_result,
        "truth_insights": truth_insights, "capability_gap": capability_gap,
        "intent_type_override": intent_type_override, "final_response": final_response,
        "should_return": should_return, "events": events,
    }