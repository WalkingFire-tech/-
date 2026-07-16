"""
流式聊天处理 - 多路并行、无固定超时、结果对比择优

核心改进：
- 多路并行获取结果（经验池 + 知识库 + Ollama + 规则），不串行等待
- 不设固定超时，外部调用等它自然返回或异常
- 结果到齐后对比择优，自我验证
- 持久化任务队列：后台任务存SQLite，服务重启不丢失，失败自动重试
- 模型分级仲裁：评估用快模型，推理用强模型
- 基因库固化：高质量回复自动升级为永久知识
"""
import asyncio
import time
from loguru import logger

from backend.services.input_preprocessor import (
    get_intent_domain_keywords as _get_intent_domain_keywords,
    compute_relevance as _compute_relevance,
    feature_enabled as _feature_enabled,
)
from backend.services.auto_fix_service import (
    auto_fix_checkpoint as _auto_fix_checkpoint,
    never_give_up_response as _never_give_up_response,
)

from backend.services.path_handlers._shared import (
    _RESOURCE_AWARE, _INPUT_PROCESSOR_AVAILABLE,
    SPIRIT_CORE_AVAILABLE,
    _run_sync,
)

try:
    from core.resource_awareness.health_monitor import get_health_monitor
except ImportError:
    get_health_monitor = None
from backend.services.path_handlers.experience_path import (
    fetch_experience as _fetch_experience,
)
from backend.services.path_handlers.knowledge_path import fetch_knowledge as _fetch_knowledge
from backend.services.path_handlers.ollama_path import (
    fetch_ollama as _fetch_ollama,
    fetch_ollama_all as _fetch_ollama_all,
)
from backend.services.path_handlers.external_api_path import (
    fetch_external_api as _fetch_external_api,
)
from backend.services.orchestrator_helpers import (
    get_self_model_safe as _get_self_model,
    emit as _emit,
    build_conversation_context as _build_conversation_context,
    self_reason as _self_reason,
    alchemize_error as _alchemize_error,
)

try:
    from core.presence.inner_time import inner_time_engine, CognitiveEventType
    _INNER_TIME_AVAILABLE = True
except ImportError:
    _INNER_TIME_AVAILABLE = False

try:
    from core.cognition.dimension_orchestrator import get_dimension_orchestrator, CognitiveDimension
    _DIMENSION_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    _DIMENSION_ORCHESTRATOR_AVAILABLE = False
from backend.services.response_aggregator import (
    compare_and_select as _compare_and_select,
)
from backend.services.auto_fix_service import (
    run_persistent_solve as _run_persistent_solve,
    auto_fix_checkpoint as _auto_fix_checkpoint,
    never_give_up_response as _never_give_up_response,
)

from backend.services.path_handlers._shared import (
    _slow_executor, _fast_executor,
    _ollama_last_inference_time,
    _INFERENCE_COOLDOWN_SECONDS, _MAX_RESPONSE_CHARS,
    _RESOURCE_AWARE, _INPUT_PROCESSOR_AVAILABLE,
    SPIRIT_CORE_AVAILABLE, _VECTOR_AVAILABLE,
    _check_vector_available, _run_sync, _run_slow,
    _save_to_experience_pool,
)

try:
    from core.resource_awareness.health_monitor import get_health_monitor
except ImportError:
    get_health_monitor = None
from backend.services.path_handlers.experience_path import (
    fetch_experience as _fetch_experience,
    get_experience_context as _get_experience_context,
    get_last_response as _get_last_response,
)
from backend.services.path_handlers.knowledge_path import fetch_knowledge as _fetch_knowledge
from backend.services.path_handlers.ollama_path import (
    get_available_ollama_models_async as _get_available_ollama_models_async,
    get_available_ollama_model_async as _get_available_ollama_model_async,
    ollama_background_save as _ollama_background_save,
    fetch_ollama as _fetch_ollama,
    fetch_ollama_all as _fetch_ollama_all,
    fetch_ollama_response as _fetch_ollama_response,
    diagnose_ollama_status as _diagnose_ollama_status,
)
from backend.services.path_handlers.external_api_path import (
    fetch_external_api as _fetch_external_api,
    fetch_external_learning as _fetch_external_learning,
)
from backend.services.path_handlers.rule_path import (
    fetch_rule as _fetch_rule,
    generate_smart_reply as _generate_smart_reply,
)
from backend.services.path_handlers.fact_path import fetch_fact_assertions as _fetch_fact_assertions
from backend.services.path_handlers.tool_path import (
    fetch_tool_results as _fetch_tool_results,
    query_needs_tools as _query_needs_tools,
    extract_tool_params as _extract_tool_params,
)
from backend.services.intent_service import (
    understand_response_content as _understand_response_content,
    discover_methodology as _discover_methodology,
)
from backend.services.code_verifier import verify_code_response as _verify_code_response
from backend.services.reflection_service import (
    reflect_and_learn as _reflect_and_learn,
    try_solidify_to_gene_pool as _try_solidify_to_gene_pool,
)
from backend.services.orchestrator_helpers import (
    get_cognitive_planner_safe as _get_cognitive_planner,
    get_self_model_safe as _get_self_model,
    emit as _emit,
    build_uncertainty_note as _build_uncertainty_note,
    build_conversation_context as _build_conversation_context,
    get_stereo_memory_context as _get_stereo_memory_context,
    self_reason as _self_reason,
    background_collect as _background_collect,
    alchemize_error as _alchemize_error,
    self_reason_deliberation as _self_reason_deliberation,
    is_goal_achieved as _is_goal_achieved,
    perceive_continuity as _perceive_continuity,
    r4_self_check as _r4_self_check,
)
from backend.services.response_aggregator import (
    score_response as _score_response,
    compare_and_select as _compare_and_select,
    self_verify as _self_verify,
    cross_source_merge as _cross_source_merge,
    list_divergences as _list_divergences,
)






async def chat_stream(user_input: str, context: dict):

    start_time = time.time()
    attempts = []
    failed_steps = []
    final_response = None
    intent_type = "unknown"
    route = "slow"
    confidence = 0.5
    _rule_actions = []
    model = "unknown"
    logger.info(f"⏱️ [T+0s] chat_stream开始: {user_input[:50]}")

    methodology = {}

    _dim_orch = None
    if _DIMENSION_ORCHESTRATOR_AVAILABLE:
        try:
            _dim_orch = get_dimension_orchestrator()
        except Exception:
            pass

    if _INNER_TIME_AVAILABLE:
        inner_time_engine.tick(CognitiveEventType.PERCEIVE, intensity=1.0, description="user_query")

    _rhythm_snapshot = None
    try:
        from core.learning.rhythm_controller import CognitiveRhythmController
        _rhythm_ctrl = CognitiveRhythmController()
        _rhythm_snapshot = _rhythm_ctrl.tick()
        if _rhythm_snapshot.energy_level < 0.3:
            logger.info(f"🧠 认知节律: 能量低({_rhythm_snapshot.energy_level:.1%}), 状态={_rhythm_snapshot.state.value}, 走轻量路径")
            methodology["rhythm_conservative"] = True
        elif _rhythm_snapshot.phase.value == "innovation":
            logger.info(f"🧠 认知节律: 创新阶段, 能量={_rhythm_snapshot.energy_level:.1%}")
            methodology["rhythm_innovative"] = True
    except Exception:
        pass

    _spirit_resonances = []
    if SPIRIT_CORE_AVAILABLE:
        try:
            from core.spirit_core import spirit_core
            _spirit_resonances = spirit_core.resonate(user_input, context_type="query")
            if _spirit_resonances:
                top = _spirit_resonances[0]
                logger.info(f"🎻 精神共振: {top['principle']} (强度={top['strength']}) → {top['drive_direction']}")
                methodology["spirit_drive"] = top["drive_direction"]
        except Exception:
            pass

    _curiosity_frontier = None
    try:
        from core.presence.curiosity_engine import CuriosityEngine
        _ce = CuriosityEngine()
        _curiosity_frontier = _ce.perceive_frontier()
        if _curiosity_frontier and _curiosity_frontier.get("curiosity_strength", 0) > 0.5:
            logger.info(f"🔍 好奇心前沿: 强度={_curiosity_frontier['curiosity_strength']:.2f}, 方向={_curiosity_frontier.get('exploration_direction', 'N/A')}")
    except Exception:
        pass

    _chat_session_id = None
    try:
        from infrastructure.chat_history import get_chat_history
        _ch = get_chat_history()
        _chat_session_id = context.get("session_id", "") if context else ""
        if not _chat_session_id:
            _chat_session_id = _ch.create_session()
    except Exception as e:
        logger.warning(f"对话历史初始化跳过: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="chat_history_init")

    user_input = user_input.strip().rstrip("/\\|").strip()
    if not user_input:
        yield _emit("result", {"response": "请输入你的问题。", "attempts": [], "intent": "greeting"})
        return

    if _chat_session_id:
        try:
            from infrastructure.chat_history import get_chat_history
            get_chat_history().add_message(_chat_session_id, "user", user_input)
        except Exception as e:
            logger.warning(f"对话历史写入user跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="chat_history_write")

    # CBNR L1: 认知规范化 — 在处理前进行认知复位
    cbnr_context = {}
    _l1_normalized = {"user_input": user_input, "intent": intent_type}
    try:
        from core.cbnr.hub import get_cbnr_hub
        _cbnr_hub = get_cbnr_hub()
        _resource_mode = "normal"
        if _RESOURCE_AWARE:
            try:
                monitor = get_health_monitor()
                snap = monitor.check()
                from core.resource_awareness.health_monitor import OperatingMode
                if hasattr(snap, 'operating_mode'):
                    _resource_mode = snap.operating_mode.value if hasattr(snap.operating_mode, 'value') else str(snap.operating_mode)
            except Exception:
                logger.warning("操作降级跳过")
        _l1_result = _cbnr_hub.process_l1(
            {"user_input": user_input, "intent": intent_type},
            {"resource_mode": _resource_mode}
        )
        _l1_normalized = _l1_result.normalized_input
        cbnr_context["l1_uncertainty"] = _l1_result.uncertainty
        cbnr_context["l1_strength"] = _l1_result.normalization_strength
        cbnr_context["l1_biases"] = _l1_result.bias_cleared
        cbnr_context["l1_principles"] = _l1_result.principles_anchored
        _attn = _l1_normalized.get("_attention_weights", {})
        cbnr_context["l1_prediction_error"] = _attn.get("avg_prediction_error", 0.5)
        cbnr_context["l1_high_surprise"] = _attn.get("high_surprise", False)
        cbnr_context["l1_focus_boost"] = _attn.get("focus_boost", 1.0)
        if _l1_result.bias_cleared:
            logger.warning(f"CBNR L1: 清除偏差{_l1_result.bias_cleared}, 不确定性={_l1_result.uncertainty:.2f}")
        if _attn.get("high_surprise"):
            logger.info(f"CBNR L1: 高预测误差({cbnr_context['l1_prediction_error']:.2f}), 增强深度推理权重")
    except Exception as e:
        logger.warning(f"CBNR L1跳过: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="CBNR_L1")
    MAX_INPUT_LENGTH = 4000
    if len(user_input) > MAX_INPUT_LENGTH:
        if _INPUT_PROCESSOR_AVAILABLE:
            try:
                processor = get_input_processor()
                mem_usage = 0.5
                mode = "normal"
                if _RESOURCE_AWARE:
                    try:
                        monitor = get_health_monitor()
                        snap = monitor.check()
                        mem_usage = snap.memory_usage
                        from core.resource_awareness.health_monitor import OperatingMode
                        if hasattr(snap, 'operating_mode'):
                            mode = snap.operating_mode.value if hasattr(snap.operating_mode, 'value') else str(snap.operating_mode)
                    except Exception:
                        logger.warning("操作降级跳过")

                processed = processor.process(user_input, memory_usage=mem_usage, mode=mode)
                if processed.was_distilled:
                    logger.info(f"长输入动态提炼: {processed.original_length}→{processed.distilled_length}字符 (压缩率{processed.compression_ratio:.1%}, 模式={processed.mode}, 策略={processed.cognitive_strategy})")
                    detail = f"长输入已提炼({processed.original_length}→{processed.distilled_length}字符)"
                    if processed.cognitive_strategy == "learning":
                        detail += "，学习模式：真谛和本质推理优先保留"
                    elif processed.cognitive_strategy == "immediate":
                        detail += "，即时模式：核心问题和上下文优先保留"
                    if processed.deferred_for_learning:
                        detail += "（已标记待深度处理）"
                    yield _emit("step", {"phase": "输入提炼", "status": "info", "detail": detail, "skeleton": processed.skeleton.to_dict(), "cognitive_strategy": processed.cognitive_strategy})
                user_input = processed.distilled
            except Exception as e:
                logger.warning(f"动态提炼失败，回退截断: {e}")
                _alchemize_error(e, context={"input_len": len(user_input)}, phase="input_distill")
                user_input = user_input[:MAX_INPUT_LENGTH]
        else:
            logger.warning(f"输入过长({len(user_input)}字符)，截断至{MAX_INPUT_LENGTH}")
            user_input = user_input[:MAX_INPUT_LENGTH]

    if _RESOURCE_AWARE:
        try:
            monitor = get_health_monitor()
            snap = monitor.check()
            _sm_health = 1.0
            _sm_obj = _get_self_model()
            if _sm_obj:
                try:
                    _sm_snap = _sm_obj.snapshot()
                    _sm_health = _sm_snap.get("health", {}).get("score", 1.0)
                except Exception:
                    logger.warning("操作降级跳过")
            if snap.memory_usage > 0.85 or _sm_health < 0.3:
                reason = f"内存{snap.memory_usage:.1%}" if snap.memory_usage > 0.85 else f"系统健康度低({_sm_health:.1%})"
                logger.warning(f"资源保护触发: {reason}，走轻量响应")
                yield _emit("step", {"phase": "资源保护", "status": "warning", "detail": f"{reason}，使用轻量响应"})
                try:
                    ollama_result = await _run_sync(_fetch_ollama_all, user_input, timeout=30)
                    if ollama_result and ollama_result.get("response"):
                        yield _emit("result", {"response": ollama_result["response"], "attempts": [{"source": "Ollama(轻量)", "success": True}], "intent": "simple", "confidence": 0.5, "route": "fast"})
                    else:
                        yield _emit("result", {"response": _never_give_up_response(user_input, attempts), "attempts": attempts, "intent": "simple", "confidence": 0.3, "route": "fast"})
                except Exception:
                    yield _emit("result", {"response": _never_give_up_response(user_input, attempts), "attempts": attempts, "intent": "simple", "confidence": 0.2, "route": "fast"})
                return
        except Exception:
            logger.warning("操作降级跳过")


    history = context.get("history", []) if context else []
    conversation_context = _build_conversation_context(history)
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 对话上下文构建完成")

    # ========== 阶段B：上下文构建（提取到context_builder.py） ==========
    from backend.services.context_builder import build_context
    _ctx_result = await build_context(
        user_input=user_input, history=history, conversation_context=conversation_context,
        cbnr_context=cbnr_context, methodology=methodology, _l1_normalized=_l1_normalized,
        route=route, start_time=start_time,
    )
    conversation_context = _ctx_result["conversation_context"]
    cbnr_context = _ctx_result["cbnr_context"]
    methodology = _ctx_result["methodology"]
    _continuity_signal = _ctx_result["continuity_signal"]
    _presence_state = _ctx_result["presence_state"]
    _query_registered = _ctx_result["query_registered"]
    for _ev in _ctx_result["events"]:
        yield _emit(_ev["type"], _ev["data"])

    # ========== 阶段1-1.5：意图识别+L1认知感知+规则匹配（提取到intent_dispatcher.py） ==========
    from backend.services.intent_dispatcher import dispatch_intent as _dispatch_intent
    _id_result = await _dispatch_intent(
        user_input=user_input, context=context, history=history,
        attempts=attempts, model=model,
    )
    intent_type = _id_result["intent_type"]
    route = _id_result["route"]
    confidence = _id_result["confidence"]
    methodology = _id_result["methodology"]
    dispatch_result = _id_result["dispatch_result"]
    _cognitive_perception = _id_result["cognitive_perception"]
    cp = _id_result["cp"]
    _cognitive_bypass_future = _id_result["cognitive_bypass_future"]
    _rule_actions = _id_result["rule_actions"]
    if _id_result["final_response"]:
        final_response = _id_result["final_response"]
    for _ev in _id_result["events"]:
        yield _emit(_ev["type"], _ev["data"])
    if _id_result["should_return"]:
        return

    if _INNER_TIME_AVAILABLE:
        inner_time_engine.tick(CognitiveEventType.REASON, intensity=0.8, description="intent_dispatched")

    if _dim_orch:
        try:
            _dim_orch.update_dimension(CognitiveDimension.DIALOGUE, confidence, f"intent={intent_type}")
            _dim_orch.update_dimension(CognitiveDimension.SEMANTIC, confidence * 0.9, f"route={route}")
        except Exception:
            pass

    # ========== 阶段2：简单意图直接回复（提取到fast_path_handler.py） ==========
    from backend.services.fast_path_handler import handle_fast_path
    _fp_result = await handle_fast_path(
        intent_type=intent_type, user_input=user_input, attempts=attempts,
        conversation_context=conversation_context, model=model,
    )
    for _ev in _fp_result["events"]:
        yield _emit(_ev["type"], _ev["data"])
    if _fp_result["handled"]:
        return
    if _fp_result["new_intent_type"] != intent_type:
        intent_type = _fp_result["new_intent_type"]

    # ========== 阶段2.5-2.7：方法论发现+能力评估（提取到methodology_discoverer.py） ==========
    from backend.services.methodology_discoverer import discover_methodology as _md_discover
    _md_result = await _md_discover(
        user_input=user_input, intent_type=intent_type, methodology=methodology,
        _continuity_signal=_continuity_signal, _rule_actions=_rule_actions,
        attempts=attempts, final_response=final_response or "",
    )
    methodology = _md_result["methodology"]
    essence_gate_result = _md_result["essence_gate_result"]
    truth_insights = _md_result["truth_insights"]
    capability_gap = _md_result.get("capability_gap")
    if _md_result["intent_type_override"]:
        intent_type = _md_result["intent_type_override"]
    if _md_result["final_response"]:
        final_response = _md_result["final_response"]
    for _ev in _md_result["events"]:
        yield _emit(_ev["type"], _ev["data"])
    if _md_result["should_return"]:
        return

    # ========== 阶段2.5：map/weather意图快速路径（提取到fast_path_handler.py） ==========
    from backend.services.fast_path_handler import handle_map_weather_fast_path
    _mw_result = await handle_map_weather_fast_path(
        intent_type=intent_type, user_input=user_input, attempts=attempts,
        final_response=final_response or "",
    )
    if _mw_result["final_response"]:
        final_response = _mw_result["final_response"]
    if _mw_result["confidence"] is not None:
        confidence = _mw_result["confidence"]
    for _ev in _mw_result["events"]:
        yield _emit(_ev["type"], _ev["data"])

    # ========== 阶段3：多策略并行尝试 ==========
    if not final_response:
        yield _emit("thinking", {
            "phase": f"我正在用多种策略同时思考你的问题",
            "confidence": float(confidence) if 'confidence' in locals() else 0.5,
            "sources": ["经验池", "知识库", "本地模型", "外部API"],
        })
        from backend.services.parallel_router import execute_parallel_paths
        candidates = []
        async for event_or_candidates in execute_parallel_paths(
            user_input, intent_type, conversation_context, truth_insights, methodology, start_time
        ):
            if isinstance(event_or_candidates, list):
                candidates = event_or_candidates
            else:
                yield event_or_candidates

    # 闭环2检查点2：多策略并行后
    try:
        _af2 = await _auto_fix_checkpoint(attempts, methodology, user_input, intent_type, "多策略并行后")
        if _af2["fixes_applied"] > 0:
            yield _emit("step", {"phase": "自我修复", "status": "done", "detail": f"🔧 执行阶段修复{_af2['fixes_applied']}项，已调整策略"})
    except Exception:
        pass

    # ========== 阶段4：对比择优 ==========

    try:
        candidates
    except NameError:
        candidates = []
    comparison = []
    path_percentages = {}
    token_summary = {}
    
    if final_response:
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 快速路径已完成，跳过阶段4-7")
        elapsed = time.time() - start_time
        yield _emit("result", {
            "response": final_response,
            "attempts": attempts,
            "intent": intent_type,
            "confidence": confidence,
            "route": route,
            "elapsed": round(elapsed, 1),
            "spirit_compliant": SPIRIT_CORE_AVAILABLE,
            "candidates": [],
            "path_contributions": {},
            "token_usage": {},
            "cbnr": {},
            "session_id": "",
            "companion_layers": {},
            "cognitive_layers": {},
        })
        logger.info(f"✅ 快速路径响应已发送({elapsed:.1f}秒)")
        return
    
    # ---- relevance filter ----
    _domain_keywords = _get_intent_domain_keywords(intent_type, user_input)
    for c in candidates:
        c["_relevance"] = _compute_relevance(c.get("response", ""), _domain_keywords)
    _before_cnt = len(candidates)
    candidates = [c for c in candidates if c["_relevance"] > 0.12]
    if len(candidates) < 1:
        candidates = candidates  # keep all if none pass
    for c in candidates:
        c["quality"] = int(c.get("quality", 30) * 0.6 + c["_relevance"] * 40)
    # ---- end relevance filter ----

    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 进入阶段4: 对比择优, {len(candidates)}个候选")
    for i, c in enumerate(candidates):
        logger.warning(f"[ORCH_DIAG] 候选{i}: source={c.get('source')}, quality={c.get('quality')}, resp_len={len(c.get('response',''))}, resp_preview={c.get('response','')[:80]}")
    yield _emit("step", {"phase": "对比择优", "status": "running", "detail": f"对{len(candidates)}个结果评分对比..."})

    best, comparison = _compare_and_select(candidates, user_input, cbnr_ctx=cbnr_context)

    if best:
        final_response = best["response"]
        for c in comparison:
            src = c["source"]
            sc = c["score"]
            attempts.append((src, sc >= 60, f"评分{sc:.0f}"))
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": f"最优来源: {best['source']} (评分{comparison[0]['score']:.0f})，共{len(comparison)}个候选"})

        # S-1: 成功路径→ToolBuilder观察学习
        try:
            from core.learning.tool_builder import ToolSelfBuilder
            tb = ToolSelfBuilder()
            for c in comparison:
                if c.get("score", 0) >= 60:
                    tb.record_success(c["source"], user_input, c.get("response", "")[:200])
        except Exception as e:
            logger.warning(f"ToolBuilder观察跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="tool_builder_observe")

        # 贡献度归因（SHAP风格）+ 路径权重更新（AdaBoost风格，不确定性感知）
        if _feature_enabled("path_weight_matrix"):
            try:
                from core.contrib_attributor import contrib_attributor
                from core.path_weight_manager import path_weight_manager
                attrib = contrib_attributor.compute_contributions(
                    candidates, final_response, best["source"], user_input
                )
                for src, score in attrib.get("contributions", {}).items():
                    unc_info = (attrib.get("retrieval_uncertainties") or {}).get(src)
                    uncertainty = unc_info.get("retrieval_entropy") if unc_info else None
                    path_weight_manager.update_weight(src, True, score, uncertainty=uncertainty,
                                                        resource_pressure=path_weight_manager.compute_resource_pressure())
                if attrib.get("contributions"):
                    contrib_str = " | ".join(f"{k}:{float(v):.0%}" for k, v in list(attrib["contributions"].items())[:5] if v is not None)
                    unc_str = ""
                    if attrib.get("retrieval_uncertainties"):
                        unc_dims = len(attrib["retrieval_uncertainties"])
                        unc_str = f" | 不确定性维度:{unc_dims}"
                    yield _emit("step", {"phase": "贡献归因", "status": "done", "detail": f"贡献度: {contrib_str}{unc_str}"})
            except Exception as e:
                logger.warning(f"贡献归因跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="contrib_attribution")

        # 动态概率场初始化（异步概率计算核心）+ 不确定性驱动路由
        if _feature_enabled("path_weight_matrix"):
            try:
                from core.dynamic_probability_field import dynamic_probability_field
                from core.path_weight_manager import path_weight_manager
                prob_dist = dynamic_probability_field.initialize(candidates, path_weight_manager.get_weights())
                if prob_dist.get("top"):
                    action = dynamic_probability_field.get_uncertainty_action()
                    action_hint = ""
                    if action["depth"] == "deep":
                        action_hint = " | 建议深度探索"
                    elif action["depth"] == "moderate":
                        action_hint = f" | {action.get('uncertainty_label', '')}"
                    yield _emit("step", {"phase": "概率场", "status": "done",
                        "detail": f"概率分布: top={prob_dist['top']['source']}({float(prob_dist['top']['probability']):.0%}) 熵={prob_dist['entropy']:.2f}{action_hint}"})
            except Exception as e:
                logger.warning(f"概率场初始化跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="probability_field")

        # 世界模型反事实推理 + 验证闭环
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            if best and len(candidates) >= 2:
                actual_source = best.get("source", "")
                alt_source = ""
                for c in candidates:
                    src = c.get("source", "")
                    if src != actual_source:
                        alt_source = src
                        break
                if alt_source:
                    cf = wm.counterfactual(
                        {"intent": intent_type, "query": user_input[:50]},
                        actual_source, alt_source, intent_type
                    )
                    if cf.get("would_have_been_better"):
                        logger.info(f"世界模型反事实: 选择'{actual_source}'不如'{alt_source}'，差异={cf['advantage']:.3f}")
                    wm.save_counterfactual(
                        intent_type, actual_source, alt_source,
                        cf["actual"]["score"], cf["counterfactual"]["score"],
                        cf["would_have_been_better"], cf["lesson"]
                    )
            if best:
                wm.auto_verify(
                    wm._hash_state({"intent": intent_type, "query": user_input[:50]}, intent_type),
                    {"outcome": "success" if best.get("score", 0) >= 60 else "failure", "source": best.get("source", "")}
                )
        except Exception as e:
            logger.warning(f"世界模型反事实推理跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="world_model_counterfactual")
    else:
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": "无有效候选结果"})

    if _dim_orch:
        try:
            _dim_orch.update_dimension(CognitiveDimension.CAUSAL, confidence, f"best_source={best.get('source','') if best else 'none'}")
            if _debate_result:
                _dim_orch.update_dimension(CognitiveDimension.METACOGNITIVE, _debate_result.arbitration.confidence, "debate_completed")
        except Exception:
            pass

    # ========== 阶段4.2：多智能体辩论（低置信度/高分歧时触发） ==========
    _debate_result = None
    if candidates and len(candidates) >= 2 and confidence < 0.7:
        try:
            from core.debate.arena import debate_arena
            _debate_result = await debate_arena.debate(
                query=user_input,
                context=conversation_context[:500] if conversation_context else "",
                candidates=candidates,
                spirit_resonances=_spirit_resonances if '_spirit_resonances' in locals() else [],
                max_rounds=1,
            )
            if _debate_result.arbitration.confidence > confidence:
                confidence = _debate_result.arbitration.confidence
                yield _emit("step", {"phase": "多智能体辩论", "status": "done",
                    "detail": f"🏟️ {len(_debate_result.positions)}方辩论完成, 共识={_debate_result.arbitration.consensus_level}, 置信度={confidence:.2f}"})
                if _debate_result.arbitration.key_insights:
                    for insight in _debate_result.arbitration.key_insights[:3]:
                        truth_insights = (truth_insights + "\n" + insight) if truth_insights else insight
        except Exception as e:
            logger.debug(f"多智能体辩论跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="debate_arena")

    # L2学习层 + L3整合层：通过CognitivePlanner从交互中学习并整合知识
    _cognitive_learning = {}
    _cognitive_integration = {}
    _bypass_result_l2l3 = None
    if _cognitive_bypass_future:
        try:
            _bypass_result_l2l3 = await asyncio.wait_for(_cognitive_bypass_future, timeout=8)
        except (asyncio.TimeoutError, Exception):
            pass
    if cp and _cognitive_perception:
        if _bypass_result_l2l3 and _bypass_result_l2l3.success:
            _cognitive_learning = _bypass_result_l2l3.learning or {}
            _cognitive_integration = _bypass_result_l2l3.integration or {}
            logger.debug("L2/L3: 使用认知旁路结果")
        else:
            try:
                _cognitive_learning = cp._learn(user_input, _cognitive_perception)
            except Exception as e:
                logger.warning(f"L2认知学习跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L2_cognitive_learning")
            try:
                _cognitive_integration = cp._integrate(_cognitive_learning)
            except Exception as e:
                logger.warning(f"L3认知整合跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L3_cognitive_integration")
        knowledge_gained = _cognitive_learning.get("knowledge_gained", 0)
        if knowledge_gained > 0:
            yield _emit("step", {"phase": "L2认知学习", "status": "done",
                "detail": f"获得{knowledge_gained}项知识, 置信度={_cognitive_learning.get('confidence', 0.7):.0%}"})
        if _cognitive_integration.get("success"):
            core_know = _cognitive_integration.get("core_knowledge", [])
            if core_know:
                yield _emit("step", {"phase": "L3认知整合", "status": "done",
                    "detail": f"整合{len(core_know)}项核心知识"})

    _sm = _get_self_model()
    if _sm and (_cognitive_learning or _cognitive_integration):
        _sm.record_cognitive_cycle(learning=_cognitive_learning, integration=_cognitive_integration)
    if _cognitive_learning and _cognitive_learning.get("knowledge_gained"):
        if _INNER_TIME_AVAILABLE:
            inner_time_engine.tick(CognitiveEventType.LEARN, intensity=0.7, description="cognitive_learning")
        yield _emit("learning", {
            "summary": f"我从这次交互中获得了{_cognitive_learning.get('knowledge_gained', 0)}项新认知",
            "confidence": float(_cognitive_learning.get("confidence", 0.5)),
            "sources": _cognitive_learning.get("sources", []),
        })

    # 【墙上的画→引擎】L2学到的知识注入推理上下文
    # 之前：knowledge_gained仅用于SSE展示和SelfModel记录，不参与实际推理
    # 现在：将L2/L3产出的知识注入truth_insights和conversation_context，让后续本质推理、
    #       自我验证、修正推理都能利用这些新获得的知识
    _l2_knowledge_context = ""
    if _cognitive_learning and _cognitive_learning.get("knowledge_gained", 0) > 0:
        _l2_sources = _cognitive_learning.get("sources", [])
        _l2_conf = _cognitive_learning.get("confidence", 0.5)
        _l2_knowledge_context = f"\n【L2认知学习-新获得知识】(置信度{_l2_conf:.0%}, 来源:{','.join(str(s) for s in _l2_sources[:3])})"
        if _cognitive_integration and _cognitive_integration.get("core_knowledge"):
            for _ck in _cognitive_integration["core_knowledge"][:3]:
                _ck_content = _ck.get("content", "")
                if _ck_content:
                    _l2_knowledge_context += f"\n- {_ck_content[:200]}"
        if _l2_knowledge_context.strip():
            truth_insights = (truth_insights + _l2_knowledge_context) if truth_insights else _l2_knowledge_context
            logger.info(f"L2知识已注入推理上下文: {_cognitive_learning.get('knowledge_gained', 0)}项, 置信度{_l2_conf:.0%}")

    # ========== 阶段4.5：本质推理与自洽验证（提取到essence_verifier.py） ==========
    from backend.services.essence_verifier import verify_essence
    _ev_result = await verify_essence(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        conversation_context=conversation_context, truth_insights=truth_insights,
        best=best or {}, fact_context=fact_context if 'fact_context' in locals() else "",
    )
    final_response = _ev_result["final_response"]
    essence_passed = _ev_result["essence_passed"]
    essence_confidence = _ev_result["essence_confidence"]
    essence_issues = _ev_result["essence_issues"]
    essence_cross_validated = _ev_result["essence_cross_validated"]
    for _ev in _ev_result["events"]:
        yield _emit(_ev["type"], _ev["data"])

    # ========== 阶段5：自我验证（提取到self_verifier.py） ==========
    from backend.services.self_verifier import self_verify_and_correct
    _sv_result = await self_verify_and_correct(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        intent_type=intent_type, route=route, confidence=confidence,
        methodology=methodology, essence_passed=essence_passed,
        essence_confidence=essence_confidence, essence_cross_validated=essence_cross_validated,
        essence_issues=essence_issues, conversation_context=conversation_context,
        truth_insights=truth_insights, candidates=candidates, best=best or {},
        cbnr_context=cbnr_context, _emit=_emit,
    )
    final_response = _sv_result["final_response"]
    attempts = _sv_result["attempts"]
    methodology = _sv_result["methodology"]
    content_understanding = _sv_result["content_understanding"]
    for _sv_ev in _sv_result["events"]:
        yield _emit(_sv_ev["type"], _sv_ev["data"])

    # ========== 阶段5.5-5.6：适应度评估+ReAct+闭环迭代（提取到fitness_optimizer.py） ==========
    from backend.services.fitness_optimizer import optimize_fitness
    _fo_result = await optimize_fitness(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        intent_type=intent_type, route=route, confidence=confidence,
        methodology=methodology, fitness_score=fitness_score if 'fitness_score' in locals() else None,
        candidates=candidates, best=best or {},
        conversation_context=conversation_context, truth_insights=truth_insights,
        complexity=complexity if 'complexity' in locals() else 0.5,
        fetch_ollama_fn=_fetch_ollama_all, fetch_external_fn=_fetch_external_api,
        fetch_knowledge_fn=_fetch_knowledge, fetch_experience_fn=_fetch_experience,
        self_reason_fn=_self_reason,
    )
    final_response = _fo_result["final_response"]
    fitness_score = _fo_result["fitness_score"]
    attempts = _fo_result["attempts"]
    for _ev in _fo_result["events"]:
        yield _emit(_ev["type"], _ev["data"])

    # ========== 阶段6：精神内核验证 + L4认知校验（提取到spirit_validator.py） ==========
    from backend.services.spirit_validator import validate_spirit_and_cognition
    _sv_result = await validate_spirit_and_cognition(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        essence_issues=essence_issues, essence_passed=essence_passed,
        essence_confidence=essence_confidence, essence_cross_validated=essence_cross_validated,
        best=best or {}, cp=cp, _cognitive_integration=_cognitive_integration,
        _cognitive_perception=_cognitive_perception if '_cognitive_perception' in locals() else None,
        _bypass_result_l2l3=_bypass_result_l2l3 if '_bypass_result_l2l3' in locals() else None,
        SPIRIT_CORE_AVAILABLE=SPIRIT_CORE_AVAILABLE,
        conversation_context=conversation_context, truth_insights=truth_insights,
    )
    final_response = _sv_result["final_response"]
    essence_issues = _sv_result["essence_issues"]
    essence_passed = _sv_result["essence_passed"]
    essence_confidence = _sv_result["essence_confidence"]
    _cognitive_validation = _sv_result["cognitive_validation"]
    _l4_doubts = _sv_result["l4_doubts"]
    _l4_should_correct = _sv_result["l4_should_correct"]
    for _ev in _sv_result["events"]:
        yield _emit(_ev["type"], _ev["data"])
    _sm = _get_self_model()
    if _sm and _cognitive_validation:
        _sm.record_cognitive_cycle(validation=_cognitive_validation)

    # ========== 阶段7：反思学习 + 基因微调 ==========
    from backend.services.reflection_learner import run_reflection_learning
    _rl_result = await run_reflection_learning(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        failed_steps=failed_steps, intent_type=intent_type, start_time=start_time,
        candidates=candidates, comparison=comparison, best=best or {},
        fitness_score=fitness_score, confidence=confidence,
        cp=cp if 'cp' in locals() else None,
        cognitive_perception=_cognitive_perception if '_cognitive_perception' in locals() else None,
        cognitive_validation=_cognitive_validation if '_cognitive_validation' in locals() else None,
        bypass_result_l2l3=_bypass_result_l2l3 if '_bypass_result_l2l3' in locals() else None,
        essence_gate_result=essence_gate_result if 'essence_gate_result' in locals() else None,
        tool_calls_log=tool_calls_log if 'tool_calls_log' in locals() else [],
    )
    reflection = _rl_result["reflection"]
    _learning_outcomes = _rl_result["learning_outcomes"]
    if _rl_result.get("final_response_override"):
        final_response = _rl_result["final_response_override"]
    for _ev in _rl_result["events"]:
        yield _emit(_ev["type"], _ev["data"])

    # ========== 阶段R：最终响应组装（提取到response_assembler.py） ==========
    from backend.services.response_assembler import assemble_and_emit as _assemble_and_emit
    _ra_result = await _assemble_and_emit(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        intent_type=intent_type, route=route, confidence=confidence,
        methodology=methodology, fitness_score=fitness_score if 'fitness_score' in locals() else None,
        candidates=candidates, comparison=comparison if 'comparison' in locals() else [],
        best=best or {}, path_percentages=path_percentages if 'path_percentages' in locals() else {},
        cbnr_context=cbnr_context, _l1_normalized=_l1_normalized if '_l1_normalized' in locals() else {},
        content_understanding=content_understanding if 'content_understanding' in locals() else {},
        companion_layers=companion_layers if 'companion_layers' in locals() else {},
        conversation_context=conversation_context, truth_insights=truth_insights if 'truth_insights' in locals() else "",
        start_time=start_time, _chat_session_id=_chat_session_id if '_chat_session_id' in locals() else "",
        cp=cp if 'cp' in locals() else None,
        _cognitive_perception=_cognitive_perception if '_cognitive_perception' in locals() else {},
        _cognitive_learning=_cognitive_learning if '_cognitive_learning' in locals() else {},
        _cognitive_integration=_cognitive_integration if '_cognitive_integration' in locals() else {},
        _cognitive_validation=_cognitive_validation if '_cognitive_validation' in locals() else {},
        _cognitive_introspection=_cognitive_introspection if '_cognitive_introspection' in locals() else None,
        _emit=_emit,
    )
    final_response = _ra_result["final_response"]
    attempts = _ra_result["attempts"]
    for _ra_ev in _ra_result["events"]:
        yield _emit(_ra_ev["type"], _ra_ev["data"])

    yield _emit("result", _ra_result["result_payload"])
    if _INNER_TIME_AVAILABLE:
        inner_time_engine.tick(CognitiveEventType.OUTPUT, intensity=1.0, description="response_sent")

    if _dim_orch:
        try:
            _dim_orch.update_dimension(CognitiveDimension.SYMBOLIC, confidence, f"route={route}")
            _alignment = _dim_orch.decide_primary_dimension(user_input[:50])
            logger.debug(f"维度编排: 主={_alignment.primary_dimension.value}, 平衡={_alignment.wisdom_truth_vector:.2f}")
        except Exception:
            pass
    logger.info(f"✅ 响应已发送({_ra_result['elapsed']:.1f}秒)，后续后台学习继续...")

    try:
        from core.metacognition.agent import metacognitive_agent
        best_source = best.get("source", "unknown") if best else "unknown"
        metacognitive_agent.record_reasoning_fingerprint(intent_type, route, best_source, confidence)
        stag = metacognitive_agent.detect_stagnation()
        if stag.get("stagnation_detected"):
            pert = stag.get("perturbation", {})
            logger.info(f"🔄 自厌信号: {pert.get('action')} — {pert.get('reason')}")
    except Exception:
        pass

    # ========== 阶段S：SSE后台阶段（提取到response_assembler.py） ==========
    from backend.services.response_assembler import run_background_phase as _run_background_phase
    _bg_result = await _run_background_phase(
        user_input=user_input, final_response=final_response or "",
        confidence=confidence, start_time=start_time, _emit=_emit,
    )
    for _bg_ev in _bg_result["events"]:
        yield _emit(_bg_ev["type"], _bg_ev["data"])

    return







