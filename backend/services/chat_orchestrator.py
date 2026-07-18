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






async def chat_stream(user_input: str, context: dict, event_sink=None):

    def _emit_s(event_type: str, data: dict) -> str:
        return _emit(event_type, data, event_sink=event_sink)

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
        try:
            _it_state = inner_time_engine.get_state()
            if _it_state.tick_count >= 10:
                if _it_state.current_phase == "sleeping":
                    methodology["inner_time_conservative"] = True
                    logger.info(f"⏱️ 内在时间: SLEEPING阶段(density={_it_state.cognitive_density:.2f}), 走轻量路径")
                elif _it_state.current_phase == "resting":
                    methodology["inner_time_efficient"] = True
                    logger.info(f"⏱️ 内在时间: RESTING阶段(density={_it_state.cognitive_density:.2f}), 优先快速路径")
                elif _it_state.current_phase == "growing":
                    methodology["inner_time_learning"] = True
                    logger.info(f"⏱️ 内在时间: GROWING阶段(density={_it_state.cognitive_density:.2f}), 优先学习路径")
        except Exception:
            pass

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
        yield _emit_s("result", {"response": "请输入你的问题。", "attempts": [], "intent": "greeting"})
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
                    yield _emit_s("step", {"phase": "输入提炼", "status": "info", "detail": detail, "skeleton": processed.skeleton.to_dict(), "cognitive_strategy": processed.cognitive_strategy})
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
                yield _emit_s("step", {"phase": "资源保护", "status": "warning", "detail": f"{reason}，使用轻量响应"})
                try:
                    ollama_result = await _run_sync(_fetch_ollama_all, user_input, timeout=30, intent_type=intent_type)
                    if ollama_result and ollama_result.get("response"):
                        yield _emit_s("result", {"response": ollama_result["response"], "attempts": [{"source": "Ollama(轻量)", "success": True}], "intent": "simple", "confidence": 0.5, "route": "fast"})
                    else:
                        yield _emit_s("result", {"response": _never_give_up_response(user_input, attempts), "attempts": attempts, "intent": "simple", "confidence": 0.3, "route": "fast"})
                except Exception:
                    yield _emit_s("result", {"response": _never_give_up_response(user_input, attempts), "attempts": attempts, "intent": "simple", "confidence": 0.2, "route": "fast"})
                return
        except Exception:
            logger.warning("操作降级跳过")

    if methodology.get("inner_time_conservative"):
        try:
            _it_check = inner_time_engine.get_state()
            if _it_check.tick_count < 10:
                logger.info(f"⏱️ 内在时间tick不足({_it_check.tick_count})，跳过节律保护")
            else:
                yield _emit_s("step", {"phase": "认知节律保护", "status": "info", "detail": "内在时间处于SLEEPING阶段，走轻量响应"})
                _it_light_result = await _fetch_external_api(user_input, conversation_context="", truth_insights="")
                if _it_light_result and _it_light_result.get("response"):
                    yield _emit_s("result", {"response": _it_light_result["response"], "attempts": [{"source": "外部API(节律保护)", "success": True}], "intent": intent_type, "confidence": 0.6, "route": "fast"})
                    return
                ollama_result = await _run_sync(_fetch_ollama_all, user_input, timeout=30, intent_type=intent_type)
                if ollama_result and ollama_result.get("response"):
                    yield _emit_s("result", {"response": ollama_result["response"], "attempts": [{"source": "Ollama(节律保护)", "success": True}], "intent": intent_type, "confidence": 0.5, "route": "fast"})
                    return
        except Exception:
            logger.warning("认知节律保护路径降级")

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
        yield _emit_s(_ev["type"], _ev["data"])

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
        yield _emit_s(_ev["type"], _ev["data"])
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
        yield _emit_s(_ev["type"], _ev["data"])
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
        yield _emit_s(_ev["type"], _ev["data"])
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
        yield _emit_s(_ev["type"], _ev["data"])

    # ========== 阶段2.8：L2/L3认知学习提前消费（注入并行推理） ==========
    _cognitive_learning = {}
    _cognitive_integration = {}
    _bypass_result_l2l3 = None
    if _cognitive_bypass_future:
        try:
            _bypass_result_l2l3 = await asyncio.wait_for(_cognitive_bypass_future, timeout=6)
        except (asyncio.TimeoutError, Exception):
            pass
    if cp and _cognitive_perception:
        if _bypass_result_l2l3 and _bypass_result_l2l3.success:
            _cognitive_learning = _bypass_result_l2l3.learning or {}
            _cognitive_integration = _bypass_result_l2l3.integration or {}
            logger.debug("L2/L3: 使用认知旁路结果（提前消费）")
        else:
            try:
                _cognitive_learning = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: cp._learn(user_input, _cognitive_perception)
                )
            except Exception as e:
                logger.warning(f"L2认知学习跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L2_cognitive_learning_early")
            try:
                if _cognitive_learning:
                    _cognitive_integration = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: cp._integrate(_cognitive_learning)
                    )
            except Exception as e:
                logger.warning(f"L3认知整合跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L3_cognitive_integration_early")

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
            logger.info(f"L2知识提前注入推理上下文: {_cognitive_learning.get('knowledge_gained', 0)}项, 置信度{_l2_conf:.0%}")
        if _INNER_TIME_AVAILABLE:
            inner_time_engine.tick(CognitiveEventType.LEARN, intensity=0.7, description="cognitive_learning_early")

    # ========== 阶段3：多策略并行尝试 ==========
    if not final_response:
        yield _emit_s("thinking", {
            "phase": f"我正在用多种策略同时思考你的问题",
            "confidence": float(confidence) if 'confidence' in locals() else 0.5,
            "sources": ["经验池", "知识库", "本地模型", "外部API"],
        })
        from backend.services.parallel_router import execute_parallel_paths
        candidates = []
        async for event_or_candidates in execute_parallel_paths(
            user_input, intent_type, conversation_context, truth_insights, methodology, start_time,
            event_sink=event_sink
        ):
            if isinstance(event_or_candidates, list):
                candidates = event_or_candidates
            else:
                yield event_or_candidates

    # 闭环2检查点2：多策略并行后
    try:
        _af2 = await _auto_fix_checkpoint(attempts, methodology, user_input, intent_type, "多策略并行后")
        if _af2["fixes_applied"] > 0:
            yield _emit_s("step", {"phase": "自我修复", "status": "done", "detail": f"🔧 执行阶段修复{_af2['fixes_applied']}项，已调整策略"})
    except Exception:
        pass

    # ========== 阶段4：对比择优（提取到comparison_selector.py） ==========

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
        yield _emit_s("result", {
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

    from backend.services.comparison_selector import compare_and_select as _compare_and_select_phase
    _cs_result = await _compare_and_select_phase(
        candidates=candidates, user_input=user_input, intent_type=intent_type,
        confidence=confidence, cbnr_context=cbnr_context,
        truth_insights=truth_insights if 'truth_insights' in locals() else "",
        start_time=start_time, _compare_and_select=_compare_and_select,
        _dim_orch=_dim_orch if '_dim_orch' in locals() else None,
        event_sink=event_sink,
        response_style=methodology.get("response_style", ""),
    )
    best = _cs_result["best"]
    comparison = _cs_result["comparison"]
    if _cs_result["final_response"]:
        final_response = _cs_result["final_response"]
    attempts.extend(_cs_result["attempts"])
    path_percentages.update(_cs_result["path_percentages"])
    for _ev in _cs_result["events"]:
        yield _ev

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
                yield _emit_s("step", {"phase": "多智能体辩论", "status": "done",
                    "detail": f"🏟️ {len(_debate_result.positions)}方辩论完成, 共识={_debate_result.arbitration.consensus_level}, 置信度={confidence:.2f}"})
                if _debate_result.arbitration.key_insights:
                    for insight in _debate_result.arbitration.key_insights[:3]:
                        truth_insights = (truth_insights + "\n" + insight) if truth_insights else insight
        except Exception as e:
            logger.debug(f"多智能体辩论跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="debate_arena")

    # L2/L3 SSE展示 + SelfModel记录（知识已在阶段2.8提前注入推理上下文）
    if _cognitive_learning and _cognitive_learning.get("knowledge_gained", 0) > 0:
        yield _emit_s("step", {"phase": "L2认知学习", "status": "done",
            "detail": f"获得{_cognitive_learning.get('knowledge_gained', 0)}项知识, 置信度={_cognitive_learning.get('confidence', 0.7):.0%}"})
        yield _emit_s("learning", {
            "summary": f"我从这次交互中获得了{_cognitive_learning.get('knowledge_gained', 0)}项新认知",
            "confidence": float(_cognitive_learning.get("confidence", 0.5)),
            "sources": _cognitive_learning.get("sources", []),
        })
    if _cognitive_integration and _cognitive_integration.get("success"):
        core_know = _cognitive_integration.get("core_knowledge", [])
        if core_know:
            yield _emit_s("step", {"phase": "L3认知整合", "status": "done",
                "detail": f"整合{len(core_know)}项核心知识"})

    _sm = _get_self_model()
    if _sm and (_cognitive_learning or _cognitive_integration):
        _sm.record_cognitive_cycle(learning=_cognitive_learning, integration=_cognitive_integration)

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
        yield _emit_s(_ev["type"], _ev["data"])

    # ========== 阶段5：自我验证（提取到self_verifier.py） ==========
    from backend.services.self_verifier import self_verify_and_correct
    _sv_result = await self_verify_and_correct(
        user_input=user_input, final_response=final_response or "", attempts=attempts,
        intent_type=intent_type, route=route, confidence=confidence,
        methodology=methodology, essence_passed=essence_passed,
        essence_confidence=essence_confidence, essence_cross_validated=essence_cross_validated,
        essence_issues=essence_issues, conversation_context=conversation_context,
        truth_insights=truth_insights, candidates=candidates, best=best or {},
        cbnr_context=cbnr_context, _emit=_emit_s,
    )
    final_response = _sv_result["final_response"]
    attempts = _sv_result["attempts"]
    methodology = _sv_result["methodology"]
    content_understanding = _sv_result["content_understanding"]
    for _sv_ev in _sv_result["events"]:
        yield _emit_s(_sv_ev["type"], _sv_ev["data"])

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
        yield _emit_s(_ev["type"], _ev["data"])

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
        yield _emit_s(_ev["type"], _ev["data"])
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
        yield _emit_s(_ev["type"], _ev["data"])

    # ========== 阶段7.5：SelfModel同步聚合 ==========
    _sm = _get_self_model()
    if _sm:
        try:
            if cp:
                _sm.sync_from_cognitive_planner(cp)
            _sm.record_cognitive_cycle(
                perception=_cognitive_perception if '_cognitive_perception' in locals() else None,
                learning=_cognitive_learning if '_cognitive_learning' in locals() else None,
                integration=_cognitive_integration if '_cognitive_integration' in locals() else None,
                validation=_cognitive_validation if '_cognitive_validation' in locals() else None,
            )
            _sm.update("relationship", {
                "trust": min(0.5 + _sm._update_count * 0.01, 1.0),
                "phase": "established" if _sm._update_count > 10 else "initial",
            })
            if _sm._update_count % 20 == 0:
                _sm.persist_state()
        except Exception as e:
            logger.debug(f"SelfModel同步跳过: {e}")

    try:
        from core.presence.existence_layer import get_existence_layer as _gel
        _el = _gel()
        _el.receive_signal({
            "signal": "interaction_completed",
            "intent_type": intent_type,
            "confidence": confidence if 'confidence' in locals() else 0.5,
            "route": route if 'route' in locals() else "unknown",
            "response_length": len(final_response) if final_response else 0,
        })
    except Exception:
        pass

    try:
        from infrastructure.database_manager import DatabaseManager as _DB2
        from infrastructure.rule_matcher import RuleMatcher as _RM2
        _rule_ctx = {"intent_type": intent_type, "raw_input": user_input}
        _rule_db = _DB2.get("data/learning_rules.db")
        _rule_rows = _rule_db.query("SELECT id, condition, action, status FROM learning_rules WHERE status IN ('active','trial') ORDER BY priority ASC, confidence DESC LIMIT 20")
        _matcher2 = _RM2()
        for _rr in _rule_rows:
            try:
                if _matcher2.evaluate_condition(_rr["condition"], _rule_ctx):
                    _rule_db.execute("UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?", (time.time(), _rr["id"]), commit=True)
                    if _rr["status"] == "trial":
                        _success = confidence > 0.5 and final_response and len(final_response) > 50
                        _rule_db.execute("UPDATE learning_rules SET trial_count=trial_count+1, trial_success=trial_success+? WHERE id=?", (1 if _success else 0, _rr["id"]), commit=True)
                        _tc_row = _rule_db.query_one("SELECT trial_count, trial_success FROM learning_rules WHERE id=?", (_rr["id"],))
                        if _tc_row and _tc_row[0] >= 5:
                            _sr = _tc_row[1] / _tc_row[0]
                            if _sr >= 0.6:
                                _rule_db.execute("UPDATE learning_rules SET status='active' WHERE id=?", (_rr["id"],), commit=True)
                                logger.info(f"✅ 试用期规则 #{_rr['id']} 激活 (成功率: {_sr:.1%})")
            except Exception:
                pass
    except Exception:
        pass

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
        _emit=_emit_s,
    )
    final_response = _ra_result["final_response"]
    attempts = _ra_result["attempts"]
    for _ra_ev in _ra_result["events"]:
        yield _emit_s(_ra_ev["type"], _ra_ev["data"])

    yield _emit_s("result", _ra_result["result_payload"])
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
        confidence=confidence, start_time=start_time, _emit=_emit_s,
    )
    for _bg_ev in _bg_result["events"]:
        yield _emit_s(_bg_ev["type"], _bg_ev["data"])

    return


async def cognitive_process(user_input: str, context: dict = None, event_sink=None) -> dict:
    """
    认知处理 — 纯逻辑入口，脱离SSE载体独立运行

    与 chat_stream() 的区别：
    - chat_stream() 是 async generator，yield SSE格式字符串
    - cognitive_process() 是普通 async 函数，返回结果字典

    参数：
    - user_input: 用户输入
    - context: 上下文字典（可选）
    - event_sink: EventSink实现（默认NullEventSink，静默运行）

    返回：
    - {"response": str, "confidence": float, "intent": str, "route": str, ...}
    """
    from core.ports import NullEventSink, BufferedEventSink

    if event_sink is None:
        event_sink = NullEventSink()

    buffered = BufferedEventSink() if isinstance(event_sink, NullEventSink) else None

    result_payload = None
    async for chunk in chat_stream(user_input, context or {}, event_sink=event_sink):
        if buffered is not None and chunk:
            pass
        if '"type": "result"' in chunk:
            try:
                import json
                data_str = chunk.replace("data: ", "").strip()
                result_payload = json.loads(data_str)
            except Exception:
                pass

    if result_payload is None:
        result_payload = {"response": "", "confidence": 0.0, "intent": "unknown", "route": "unknown"}

    return result_payload


