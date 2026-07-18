import re as _re_science
from loguru import logger

from backend.services.auto_fix_service import run_persistent_solve as _run_persistent_solve, never_give_up_response as _never_give_up_response
from backend.services.input_preprocessor import feature_enabled as _feature_enabled, generate_meaningful_fallback as _generate_meaningful_fallback
from backend.services.orchestrator_helpers import (
    self_reason_deliberation as _self_reason_deliberation,
    get_self_model_safe as _get_self_model,
    build_uncertainty_note as _build_uncertainty_note,
)
from backend.services.response_aggregator import self_verify as _self_verify, score_response as _score_response
from backend.services.intent_service import understand_response_content as _understand_response_content
from backend.services.code_verifier import verify_code_response as _verify_code_response
from backend.services.path_handlers._shared import _save_to_experience_pool
from backend.services.path_handlers.ollama_path import (
    get_available_ollama_model_async as _get_available_ollama_model_async,
    fetch_ollama as _fetch_ollama,
    fetch_ollama_response as _fetch_ollama_response,
)



async def self_verify_and_correct(
    user_input: str, final_response: str, attempts: list,
    intent_type: str, route: str, confidence: float,
    methodology: dict, essence_passed: bool, essence_confidence: float,
    essence_cross_validated: bool, essence_issues: list,
    conversation_context: str, truth_insights: str,
    candidates: list, best: dict, cbnr_context: dict,
    _emit,
) -> dict:
    events = []
    content_understanding = {}

    if not final_response:
        try:
            from core.learning.capability_gap_learner import capability_gap_learner
            gap = capability_gap_learner.detect_gap(user_input, attempts, "")
            if gap:
                logger.info(f"🔍 检测到能力缺失: {gap['gap_type']} — {user_input[:50]}")
                gap_resolution = await capability_gap_learner.try_resolve_gap(gap)
                if gap_resolution:
                    logger.info(f"🧠 能力缺失学习结果: {gap_resolution[:100]}")
                    events.append({"type": "learning", "data": {"type": "capability_gap", "gap_type": gap["gap_type"], "resolution": gap_resolution[:200]}})

                if gap.get("gap_type") in ("tool", "missing_tool", "hardware", "system_command"):
                    try:
                        from core.learning.tool_builder import ToolSelfBuilder
                        _tb = ToolSelfBuilder()
                        _need_key = _tb.observe_need(
                            description=f"{gap.get('gap_type')}: {user_input[:100]}",
                            context={"gap": gap, "intent_type": intent_type},
                        )
                        _opportunities = _tb.identify_tool_opportunities()
                        if _opportunities:
                            _build_result = _tb.build_tool(_opportunities[0])
                            if _build_result.success:
                                logger.info(f"🔧 工具构建器: 自动构建工具'{_build_result.tool_id}'成功")
                                events.append({"type": "learning", "data": {"type": "tool_built", "tool_id": _build_result.tool_id}})
                            else:
                                logger.error(f"工具构建器: 构建失败 - {_build_result.error}")
                    except Exception as _tbe:
                        logger.warning(f"工具构建器跳过: {_tbe}")
        except Exception as _ge:
            logger.error(f"能力缺失学习异常: {_ge}")

        if _feature_enabled("capability_creation_loop"):
            try:
                from core.capability_creation_loop import capability_creation_loop
                events.append({"type": "step", "data": {"phase": "能力创造", "status": "running", "detail": "常规方法未解决，启动能力创造回路..."}})
                cap_result = await capability_creation_loop.handle(user_input, context={"intent_type": intent_type})
                if cap_result and cap_result.get("handled") and cap_result.get("data"):
                    final_response = cap_result["data"]
                    attempts.append(("能力创造回路", True, f"method={cap_result.get('method', 'unknown')}"))
                    events.append({"type": "step", "data": {"phase": "能力创造", "status": "done", "detail": "能力创造回路成功解决 ✅"}})
                    logger.info(f"能力创造回路成功: {user_input[:50]}")
            except Exception as _cce:
                logger.warning(f"能力创造回路跳过: {_cce}")

        if not final_response:
            fallback = _generate_meaningful_fallback(user_input, attempts)
        else:
            fallback = None
        if fallback == "__NEED_DYNAMIC_FALLBACK__":
            try:
                ollama_result = await _fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                if ollama_result and ollama_result.get("response") and len(ollama_result["response"]) > 20:
                    final_response = ollama_result["response"]
                    attempts.append(("动态推理", True, "模型实时生成"))
                else:
                    attempts.append(("动态推理", False, "模型无有效回复"))
            except Exception as _e:
                logger.warning(f"动态推理异常: {_e}")
                attempts.append(("动态推理", False, f"模型异常: {str(_e)[:60]}"))

            if not final_response:
                try:
                    events.append({"type": "step", "data": {"phase": "持续求解", "status": "running", "detail": "常规方法未解决，启动持续求解引擎..."}})
                    final_response, _ps_ok = await _run_persistent_solve(
                        user_input, attempts, conversation_context,
                        truth_insights, intent_type, "持续求解", _emit)
                    if not _ps_ok:
                        final_response = final_response or _never_give_up_response(user_input, attempts)
                except Exception as _pse:
                    logger.warning(f"持续求解异常: {_pse}")
                    final_response = _never_give_up_response(user_input, attempts)
                    attempts.append(("持续求解", False, f"异常: {str(_pse)[:60]}"))
        elif fallback:
            final_response = fallback
            attempts.append(("降级保护", True, "基础回复"))
        events.append({"type": "step", "data": {"phase": "自我验证", "status": "done", "detail": "使用动态推理回复"}})

    if final_response:
        events.append({"type": "step", "data": {"phase": "自我验证", "status": "running", "detail": "验证回复质量和逻辑性..."}})

        if intent_type in ("hardware", "map", "weather") and final_response:
            _intent_output_mismatch = False
            _mismatch_reason = ""
            q_lower = user_input.lower()
            if any(kw in q_lower for kw in ["读取", "获取", "读出", "接收"]) and "扫描" in final_response and "数据" not in final_response[:200]:
                _intent_output_mismatch = True
                _mismatch_reason = "用户要读数据但返回了扫描结果"
            if any(kw in q_lower for kw in ["串口", "serial", "com"]) and "端口" in final_response[:100] and "NMEA" not in final_response and "GPGGA" not in final_response and "GPRMC" not in final_response:
                if any(kw in q_lower for kw in ["读取", "获取", "读", "数据"]):
                    _intent_output_mismatch = True
                    _mismatch_reason = "用户要读串口数据但返回了端口列表"
            if _intent_output_mismatch:
                logger.warning(f"[意图-产出对照] {_mismatch_reason}, 降低置信度")
                verification = {"verified": False, "confidence": 0.3, "issues": [_mismatch_reason]}
                events.append({"type": "step", "data": {"phase": "意图-产出对照", "status": "warning", "detail": f"⚠️ {_mismatch_reason}"}})
                try:
                    from core.cognition.failure_classifier import FailureClassifier
                    from core.cognition.audit_logger import AuditLogger
                    reflection = {"status": "mismatch", "reason": _mismatch_reason}
                    fix_result = await FailureClassifier.classify_and_fix(
                        reflection, user_input, {"intent_type": intent_type})
                    AuditLogger.log(user_input, {"intent_type": intent_type}, final_response[:200], reflection)
                    if fix_result.get("auto_fix_result", {}).get("methodology_patch"):
                        methodology.update(fix_result["auto_fix_result"]["methodology_patch"])
                except Exception:
                    logger.warning("操作降级跳过")
            else:
                verification = await _self_verify(user_input, final_response)
        else:
            verification = await _self_verify(user_input, final_response)

        if intent_type == "map" and final_response:
            _has_map_output = any(kw in final_response.lower() for kw in ["地图已生成", "folium", "map.html", "gps_map", "浏览器中打开"])
            if not _has_map_output:
                try:
                    from core.capability_creation_loop import capability_creation_loop
                    events.append({"type": "step", "data": {"phase": "地图生成", "status": "running", "detail": "检测到地图意图，生成地图..."}})
                    map_result = await capability_creation_loop._solve_map_render(user_input)
                    if map_result and map_result.get("success"):
                        final_response = map_result["data"]
                        attempts.append(("地图生成", True, "map intent post-processing"))
                        events.append({"type": "step", "data": {"phase": "地图生成", "status": "done", "detail": "地图已生成 ✅"}})
                        logger.info("🗺️ Map意图后处理: 地图生成成功")
                except Exception as _me:
                    logger.warning(f"地图生成跳过: {_me}")

        v_conf = verification["confidence"]
        e_conf = essence_confidence
        if v_conf > 0 and e_conf > 0:
            combined_confidence = 0.6 * max(v_conf, e_conf) + 0.4 * min(v_conf, e_conf)
        else:
            combined_confidence = max(v_conf, e_conf)
        if essence_passed and essence_confidence >= 0.7:
            combined_confidence = max(combined_confidence, 0.85)
        verification["confidence"] = combined_confidence

        if verification["verified"]:
            attempts.append(("自我验证", True, f"通过 (置信度{verification['confidence']:.0%})"))
            events.append({"type": "step", "data": {"phase": "自我验证", "status": "done", "detail": f"验证通过 ✅ 置信度{verification['confidence']:.0%}"}})

            _deliberation_needed = False
            _deliberation_reason = ""
            if final_response and len(final_response) > 50:
                _has_synthesis = any(kw in final_response for kw in ["因此", "综上", "核心在于", "关键在于", "本质上", "根本原因", "原理是", "之所以", "设计思路", "权衡"])
                _is_list_only = final_response.count("\n-") > 3 and not _has_synthesis
                _has_baidu_prefix = "[baidu]" in final_response and final_response.count("[baidu]") >= 2
                _too_short_for_complex = len(final_response) < 200 and any(kw in user_input for kw in ["如何", "怎么", "怎样", "设计", "优化", "改进", "方案"])
                if _is_list_only and not _has_synthesis:
                    _deliberation_needed = True
                    _deliberation_reason = "答案仅为列表堆砌，缺乏综合分析"
                elif _has_baidu_prefix and not _has_synthesis:
                    _deliberation_needed = True
                    _deliberation_reason = "答案仅为搜索结果拼接，缺乏深度推理"
                elif _too_short_for_complex:
                    _deliberation_needed = True
                    _deliberation_reason = "复杂问题答案过短，缺乏展开"

            if _deliberation_needed and not any(a[0] == "深度审议" for a in attempts):
                logger.info(f"🤔 内部审议: {_deliberation_reason}，触发深度推理")
                events.append({"type": "step", "data": {"phase": "深度审议", "status": "running", "detail": f"🤔 {_deliberation_reason}，启动深度推理..."}})
                try:
                    model = await _get_available_ollama_model_async()
                    if model:
                        _delib_prompt = (
                            f"用户问题：{user_input}\n\n"
                            f"当前回答（仅作参考，需要更深入）：\n{final_response[:500]}\n\n"
                            f"请给出更深入、更有洞察力的回答。要求：\n"
                            f"1. 不要重复已有内容，要给出更深层的原理和权衡\n"
                            f"2. 分析问题背后的核心矛盾和约束\n"
                            f"3. 给出具体的、可执行的方案而非泛泛建议\n"
                        )
                        _delib_result = await _fetch_ollama(_delib_prompt, model, timeout=30, conversation_context=conversation_context)
                        if _delib_result and _delib_result.get("response") and len(_delib_result["response"]) > len(final_response) * 0.5:
                            _delib_score = _score_response(_delib_result, user_input)
                            _orig_score = _score_response({"response": final_response, "source": "original"}, user_input)
                            if _delib_score >= _orig_score * 0.8:
                                final_response = _delib_result["response"]
                                attempts.append(("深度审议", True, f"深度推理成功 (评分{_delib_score:.0f})"))
                                events.append({"type": "step", "data": {"phase": "深度审议", "status": "done", "detail": "✅ 深度推理完成，答案已升级"}})
                            else:
                                attempts.append(("深度审议", False, f"深度推理评分{_delib_score:.0f}未显著优于原{_orig_score:.0f}"))
                                events.append({"type": "step", "data": {"phase": "深度审议", "status": "done", "detail": "深度推理未显著优于原答案"}})
                        else:
                            attempts.append(("深度审议", False, "深度推理无有效结果"))
                            events.append({"type": "step", "data": {"phase": "深度审议", "status": "done", "detail": "深度推理未返回有效结果"}})
                    else:
                        _delib_self_result = await _self_reason_deliberation(user_input, final_response, _deliberation_reason)
                        if _delib_self_result:
                            final_response = _delib_self_result
                            attempts.append(("深度审议", True, "自我推理深度分析成功"))
                            events.append({"type": "step", "data": {"phase": "深度审议", "status": "done", "detail": "✅ 自我推理深度分析完成，答案已升级"}})
                        else:
                            attempts.append(("深度审议", False, "自我推理也无有效结果"))
                            events.append({"type": "step", "data": {"phase": "深度审议", "status": "done", "detail": "深度审议未能提升答案质量"}})
                except Exception as _de:
                    logger.warning(f"深度审议异常: {_de}")
                    attempts.append(("深度审议", False, f"异常: {str(_de)[:40]}"))
                    events.append({"type": "step", "data": {"phase": "深度审议", "status": "done", "detail": "深度审议跳过"}})
        else:
            filtered_issues = [i for i in verification["issues"] if i not in essence_issues]
            if not filtered_issues and essence_cross_validated:
                attempts.append(("自我验证", True, f"本质推理已覆盖 (置信度{verification['confidence']:.0%})"))
                events.append({"type": "step", "data": {"phase": "自我验证", "status": "done", "detail": f"本质推理已覆盖验证，跳过冗余修正 ✅"}})
            else:
                _is_system_error = any("系统错误输出" in i for i in verification["issues"])
                _is_hallucination = any("混淆" in i or "幻觉" in i for i in verification["issues"])
                _is_irrelevant = any("无关" in i for i in verification["issues"])
                if _is_system_error or _is_hallucination or _is_irrelevant:
                    logger.warning(f"检测到异常输出，丢弃当前响应: {verification['issues']}")
                    final_response = ""
                    events.append({"type": "step", "data": {"phase": "自我验证", "status": "done", "detail": f"⚠️ 检测到系统错误输出，丢弃响应"}})

                    try:
                        from core.external_learner import ExternalLearner
                        el = ExternalLearner()
                        ext_result = el.ask(user_input)
                        if ext_result and len(ext_result) > 20:
                            final_response = ext_result
                            attempts.append(("外部API修正", True, "系统错误输出已用外部API替换"))
                            events.append({"type": "step", "data": {"phase": "外部API修正", "status": "done", "detail": "已用外部API替换系统错误输出 ✅"}})
                    except Exception as _ee:
                        logger.warning(f"外部API修正失败: {_ee}")

                    if not final_response:
                        try:
                            from backend.services.orchestrator_helpers import get_cognitive_planner_safe
                            cp = get_cognitive_planner_safe()
                            if cp:
                                kb_result = cp._retrieve_knowledge(user_input)
                                if kb_result and kb_result.get("response"):
                                    final_response = kb_result["response"]
                                    attempts.append(("知识库修正", True, "系统错误输出已用知识库替换"))
                        except Exception:
                            pass

                    if not final_response:
                        final_response = f"关于「{user_input}」，我暂时无法给出满意的回答。请稍后再试。"
                        attempts.append(("降级保护", True, "系统错误输出降级"))

                else:
                    attempts.append(("自我验证", False, f"问题: {'; '.join(verification['issues'])}"))
                    events.append({"type": "step", "data": {"phase": "自我验证", "status": "done", "detail": f"发现问题: {'; '.join(verification['issues'])}，尝试修正..."}})

                if not essence_cross_validated and not any(a[0].startswith("Ollama") and a[1] for a in attempts):
                    model = await _get_available_ollama_model_async()
                    if model:
                        events.append({"type": "step", "data": {"phase": "修正推理", "status": "running", "detail": f"验证未通过，调用 {model} 重新推理..."}})
                        retry = await _fetch_ollama(user_input, model, timeout=15, conversation_context=conversation_context)
                        if retry and retry.get("response"):
                            retry_score = _score_response(retry, user_input)
                            current_score = _score_response(best, user_input) if best else 0
                            if retry_score > current_score:
                                final_response = retry["response"]
                                _save_to_experience_pool(user_input, retry["response"], success=True, intent_type="retry_correction", model_name="retry")
                                attempts.append(("修正推理", True, f"Ollama修正成功 (评分{retry_score:.0f}>{current_score:.0f})"))
                                events.append({"type": "step", "data": {"phase": "修正推理", "status": "done", "detail": f"修正成功，新评分{retry_score:.0f}"}})
                            else:
                                attempts.append(("修正推理", False, f"修正结果评分{retry_score:.0f}未超过原{current_score:.0f}"))
                                events.append({"type": "step", "data": {"phase": "修正推理", "status": "done", "detail": "修正结果未优于原结果，保留原回复"}})
                        else:
                            events.append({"type": "step", "data": {"phase": "修正推理", "status": "done", "detail": "修正推理未返回有效结果"}})
                    else:
                        events.append({"type": "step", "data": {"phase": "修正推理", "status": "done", "detail": "无可用模型"}})

        content_understanding = _understand_response_content(user_input, final_response, cbnr_context)
        _simple_fact_exempt = bool(_re_science.search(r'(?:等于几|几加几|\d+\s*[+\-*/×÷]\s*\d+)', user_input))
        if content_understanding["needs_verification"] and content_understanding["claim_type"] == "scientific" and not _simple_fact_exempt:
            domain_ref = content_understanding["domain"]
            disclaimer = f"\n\n---\n⚠️ 以上涉及科学事实，我的推论可能存在偏差，建议参考{domain_ref}。\n（此声明仅为核实建议，非本回答的立论依据，请勿在后续推理中引用此声明）\n---"
            if "建议参考" not in final_response:
                final_response += disclaimer
                attempts.append(("科学免责", True, f"已附加{domain_ref}不确定性声明"))
                events.append({"type": "step", "data": {"phase": "科学免责", "status": "done", "detail": f"语义理解: {content_understanding['reasoning']}，已附加不确定性声明 ⚠️"}})

        try:
            from core.dynamic_probability_field import dynamic_probability_field
            if dynamic_probability_field._candidates and dynamic_probability_field._entropy > 0.7:
                action = dynamic_probability_field.get_uncertainty_action()
                if action["depth"] in ("deep", "moderate") and "不确定" not in final_response:
                    unc_note = _build_uncertainty_note(
                        user_input, final_response, attempts,
                        dynamic_probability_field, action
                    )
                    if unc_note:
                        final_response += unc_note
                        attempts.append(("不确定性坦诚", True, "针对性结语"))
        except Exception:
            logger.warning("操作降级跳过")

        _sm_growth = _get_self_model()
        if _sm_growth:
            try:
                snap = _sm_growth.snapshot()
                recent = snap.get("recent_learning", [])
                if recent and len(recent) >= 1:
                    latest = recent[-1]
                    summary = latest.get("summary", "")
                    if summary and len(summary) > 5:
                        growth_note = f"\n\n💡 顺便说一下，{summary}"
                        if growth_note not in final_response:
                            final_response += growth_note
            except Exception:
                logger.warning("操作降级跳过")

        if final_response:
            try:
                from core.presence.scene_awareness import scene_awareness, SceneSnapshot
                from core.resource_awareness.health_monitor import get_health_monitor, OperatingMode
                _hm = get_health_monitor()
                _mode = _hm.get_operating_mode()
                _gpu_temp = 0
                try:
                    from infrastructure.hardware_monitor import get_gpu_stats
                    _gs = get_gpu_stats()
                    _gpu_temp = _gs.get("temperature", 0) if _gs.get("available") else 0
                except Exception:
                    pass
                _snap = _hm.check()
                _gaps_count = 0
                try:
                    from core.presence.curiosity_engine import get_curiosity_engine
                    _gaps_count = len(get_curiosity_engine().perceive_gaps())
                except Exception:
                    pass
                scene = scene_awareness.build_scene(
                    resource_mode=_mode.value,
                    gpu_temp=_gpu_temp,
                    memory_usage=_snap.memory_usage,
                    cpu_percent=_snap.cpu_percent,
                    intent_type=intent_type,
                    complexity=methodology.get("complexity", 0.5) if methodology else 0.5,
                    confidence=methodology.get("confidence", 0.5) if methodology else 0.5,
                    response_length=len(final_response),
                    sources_count=len(candidates) if candidates else 0,
                    has_tool_result=any("工具" in (c.get("source", "") if isinstance(c, dict) else "") for c in (candidates or [])),
                    knowledge_gaps=_gaps_count,
                )
                if scene_awareness.should_extend(scene):
                    extension = scene_awareness.compose_extension(scene, final_response)
                    if extension:
                        final_response += f"\n\n{extension}"
            except Exception:
                pass

        if intent_type == "code" and final_response:
            code_verify = _verify_code_response(user_input, final_response)
            if code_verify["passed"]:
                attempts.append(("代码验证", True, code_verify["detail"]))
                events.append({"type": "step", "data": {"phase": "代码验证", "status": "done", "detail": f"代码验证通过 ✅ {code_verify['detail']}"}})
            else:
                attempts.append(("代码验证", False, code_verify["detail"]))
                events.append({"type": "step", "data": {"phase": "代码验证", "status": "done", "detail": f"代码验证发现问题：{code_verify['detail']}"}})

    return {
        "final_response": final_response, "attempts": attempts,
        "methodology": methodology, "content_understanding": content_understanding,
        "events": events,
    }