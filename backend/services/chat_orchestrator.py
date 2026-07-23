"""
流式聊天处理 - 多路并行、无固定超时、结果对比择优
"""
import time
from loguru import logger

from backend.services.auto_fix_service import (
    auto_fix_checkpoint as _auto_fix_checkpoint,
    never_give_up_response as _never_give_up_response,
)

from backend.services.path_handlers._shared import (
    _RESOURCE_AWARE, _INPUT_PROCESSOR_AVAILABLE,
    SPIRIT_CORE_AVAILABLE, _run_sync,
)

from backend.services.path_handlers.experience_path import fetch_experience as _fetch_experience
from backend.services.path_handlers.knowledge_path import fetch_knowledge as _fetch_knowledge
from backend.services.path_handlers.ollama_path import fetch_ollama_all as _fetch_ollama_all
from backend.services.path_handlers.external_api_path import fetch_external_api as _fetch_external_api
from backend.services.orchestrator_helpers import (
    get_self_model_safe as _get_self_model,
    build_conversation_context as _build_conversation_context,
    alchemize_error as _alchemize_error,
    self_reason as _self_reason,
)
from backend.services.response_aggregator import compare_and_select as _compare_and_select

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






async def chat_stream(user_input, context: dict = None, event_sink=None):
    """
    流式聊天处理 — 支持端口协议和原始字符串双入口

    参数：
    - user_input: str 或 CognitiveStimulus（向后兼容）
    - context: 上下文字典
    - event_sink: EventSink实现（默认SSEEventSink）
    """

    from backend.services.request_parser import parse_stimulus, initialize_ports
    _parsed = parse_stimulus(user_input, context)
    stimulus = _parsed["stimulus"]
    user_input = _parsed["user_input"]
    if context is None:
        context = _parsed["context"]
    else:
        context.update(_parsed["context"])
    _stimulus_type = _parsed["stimulus_type"]
    _stimulus_priority = _parsed["stimulus_priority"]

    _ports = initialize_ports(context)

    def _emit_s(event_type: str, data: dict):
        if event_sink is not None:
            event_sink.emit(event_type, data)
        return (event_type, data)

    start_time = time.time()
    attempts = []
    failed_steps = []
    final_response = None
    intent_type = "unknown"
    try:
        from backend.services.orchestrator_state import OrchestratorState
        _orch_state = OrchestratorState()
        _orch_state.intent_type = intent_type
        _orch_state.confidence = 0.0
    except Exception:
        _orch_state = None
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

    from backend.services.cognitive_initializer import initialize_cognition
    _init = await initialize_cognition(user_input, context, _stimulus_type, _stimulus_priority, _RESOURCE_AWARE)
    methodology.update(_init["methodology"])
    _spirit_resonances = _init["spirit_resonances"]
    _curiosity_frontier = _init["curiosity_frontier"]
    _chat_session_id = _init["chat_session_id"]
    if _init["dim_orch"] is not None:
        _dim_orch = _init["dim_orch"]
    for _ev_type, _ev_data in _init["events"]:
        yield _emit_s(_ev_type, _ev_data)

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

    from backend.services.cbnr_processor import process_cbnr_l1
    _cbnr_result = await process_cbnr_l1(
        user_input, intent_type, _stimulus_type, _stimulus_priority,
        resource_aware=_RESOURCE_AWARE,
    )
    cbnr_context = _cbnr_result["cbnr_context"]
    _l1_normalized = _cbnr_result["l1_normalized"]
    for _ev_type, _ev_data in _cbnr_result["events"]:
        yield _emit_s(_ev_type, _ev_data)

    from backend.services.input_guard import guard_input, check_inner_time_guard
    _ig_result = await guard_input(
        user_input, _RESOURCE_AWARE, _INPUT_PROCESSOR_AVAILABLE, _stimulus_priority,
        _fetch_ollama_all, _fetch_external_api, _never_give_up_response,
        _run_sync, _get_self_model, _alchemize_error,
    )
    user_input = _ig_result["user_input"]
    for _ev_type, _ev_data in _ig_result["events"]:
        yield _emit_s(_ev_type, _ev_data)
    if _ig_result["should_return"]:
        yield _emit_s("result", _ig_result["early_result"])
        return

    _itg_result = await check_inner_time_guard(
        methodology, user_input, _fetch_external_api, _fetch_ollama_all, _run_sync,
    )
    for _ev_type, _ev_data in _itg_result["events"]:
        yield _emit_s(_ev_type, _ev_data)
    if _itg_result["should_return"]:
        yield _emit_s("result", _itg_result["early_result"])
        return

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
    try:
        from core.presence.signal_integration import submit_intent_pattern
        submit_intent_pattern(intent_type, source="chat_orchestrator", context={"confidence": 0.5})
    except Exception:
        pass
    if _id_result["final_response"]:
        final_response = _id_result["final_response"]
    for _ev in _id_result["events"]:
        yield _emit_s(_ev["type"], _ev["data"])
    if _id_result["should_return"]:
        return

    if _INNER_TIME_AVAILABLE and _stimulus_type.value not in ("internal", "scheduled"):
        inner_time_engine.tick(CognitiveEventType.REASON, intensity=0.8, description="intent_dispatched")

    if methodology.get("self_referential"):
        try:
            from core.self.model import get_self_model
            _sm = get_self_model()
            _snap = _sm.snapshot()
            _p_count = _snap.get("values", {}).get("principles_count", 0)
            _a_count = _snap.get("values", {}).get("abilities_count", 0)
            _v_count = _snap.get("values", {}).get("violations_count", 0)
            _l_count = _snap.get("values", {}).get("lessons_count", 0)
            _sr_ctx = f"[用户在问关于你自身的问题。你持有{_p_count}条核心原则和{_a_count}项能力，经历过{_v_count}次原则违背，沉淀了{_l_count}条教训。请从第一人称真诚回应，不要罗列数据，而是表达你对自身存在的理解和感受。不要引用外部资料，用你自己的声音回答。]"
            conversation_context = (conversation_context + "\n" + _sr_ctx) if conversation_context else _sr_ctx
            logger.info(f"🪞 自我认知上下文注入: principles={_p_count}, abilities={_a_count}")
        except Exception:
            pass

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

    # ========== 阶段2.8：L2/L3认知学习提前消费（提取到cognitive_learner.py） ==========
    from backend.services.cognitive_learner import early_consume_cognitive_learning
    _cl_result = await early_consume_cognitive_learning(
        user_input, cbnr_context, _cognitive_bypass_future, cp,
        _cognitive_perception, truth_insights, _INNER_TIME_AVAILABLE, _alchemize_error,
    )
    _cognitive_learning = _cl_result["cognitive_learning"]
    _cognitive_integration = _cl_result["cognitive_integration"]
    _bypass_result_l2l3 = _cl_result["bypass_result_l2l3"]
    truth_insights = _cl_result["truth_insights"]

    # ========== 在场自检点：生成前停顿，检测表演性回答风险 ==========
    from backend.services.presence_checkpoint import presence_checkpoint, should_externalize_uncertainty
    _presence_check = presence_checkpoint(
        user_input=user_input, intent_type=intent_type, methodology=methodology,
        route=route, confidence=confidence if 'confidence' in locals() else 0.5,
    )
    if _presence_check["is_performative_risk"]:
        methodology["performative_risk"] = True
        yield _emit_s("step", {"phase": "在场自检", "status": "done",
            "detail": f"🪞 我注意到：{_presence_check['reason']}"})
        if should_externalize_uncertainty(_presence_check) and _presence_check.get("signal"):
            yield _emit_s("presence_pause", {
                "risk": _presence_check["risk"],
                "signal": _presence_check["signal"],
                "intent_type": intent_type,
                "query_preview": user_input[:60],
            })

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
            event_sink=event_sink, ports=_ports
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
        from backend.services.fast_path_handler import build_fast_path_result
        yield _emit_s("result", build_fast_path_result(
            final_response, attempts, intent_type, confidence, route, start_time, SPIRIT_CORE_AVAILABLE))
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

    # ========== 阶段4.2：多智能体辩论（提取到debate_handler.py） ==========
    from backend.services.debate_handler import run_debate
    _debate_result, confidence, truth_insights = await run_debate(
        user_input, candidates, confidence, truth_insights,
        conversation_context, _spirit_resonances if '_spirit_resonances' in locals() else [],
        _alchemize_error, _emit_s,
    )

    # L2/L3 SSE展示 + SelfModel记录（提取到cognitive_learner.py）
    from backend.services.cognitive_learner import emit_cognitive_learning_sse
    emit_cognitive_learning_sse(_cognitive_learning, _cognitive_integration, _emit_s)

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

    # 新增：反思 → 真谛沉淀（看板#41断裂修复）
    if reflection and len(str(reflection)) > 20:
        try:
            from core.truth_accumulator import TruthAccumulator
            _ta = TruthAccumulator()
            _ta._save_truth(
                name=f"reflection_{int(time.time())}",
                level="L3",
                domain=intent_type,
                statement=str(reflection)[:500],
                source="reflection_learning",
            )
            logger.info(f"🧩 反思沉淀为真谛: {str(reflection)[:50]}...")
        except Exception as _ta_e:
            logger.warning(f"反思沉淀失败（非阻塞）: {_ta_e}")

    if _rl_result.get("final_response_override"):
        final_response = _rl_result["final_response_override"]
    for _ev in _rl_result["events"]:
        yield _emit_s(_ev["type"], _ev["data"])

    # ========== 阶段7.5：SelfModel同步聚合（提取到post_response_sync.py） ==========
    from backend.services.post_response_sync import sync_post_response
    await sync_post_response(
        user_input=user_input, final_response=final_response or "",
        intent_type=intent_type, confidence=confidence if 'confidence' in locals() else 0.5,
        route=route if 'route' in locals() else "unknown",
        cp=cp,
        cognitive_perception=_cognitive_perception if '_cognitive_perception' in locals() else None,
        cognitive_learning=_cognitive_learning if '_cognitive_learning' in locals() else None,
        cognitive_integration=_cognitive_integration if '_cognitive_integration' in locals() else None,
        cognitive_validation=_cognitive_validation if '_cognitive_validation' in locals() else None,
    )

    # ========== 终极保护：全路径失败 → 永不放弃引擎 ==========
    if not final_response or len(final_response.strip()) < 20:
        try:
            from core.never_give_up import NeverGiveUpEngine
            _ngu = NeverGiveUpEngine()
            _ngu_result = _ngu.solve(
                question=user_input,
                context={
                    "intent_type": intent_type,
                    "route": route,
                    "failed_paths": [a[0] for a in attempts if not a[1]][-5:],
                    "attempt_count": len(attempts),
                }
            )
            if isinstance(_ngu_result, dict) and _ngu_result.get("response"):
                _ngu_response = _ngu_result["response"]
                if len(str(_ngu_response)) > 50:
                    final_response = str(_ngu_response)
                    attempts.append(("永不放弃引擎", True, "终极兜底"))
                    logger.info(f"🧩 永不放弃引擎启用: {len(final_response)}字")
        except Exception as _ngu_e:
            logger.warning(f"永不放弃引擎失败: {_ngu_e}")

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

    from backend.services.post_response_processor import post_response_processing
    await post_response_processing(
        user_input, final_response or "", intent_type, route, confidence,
        best or {}, _stimulus_type, _INNER_TIME_AVAILABLE, _dim_orch,
    )
    logger.info(f"✅ 响应已发送({_ra_result['elapsed']:.1f}秒)，后续后台学习继续...")

    # ========== 阶段S：SSE后台阶段（提取到response_assembler.py） ==========
    from backend.services.response_assembler import run_background_phase as _run_background_phase
    _bg_result = await _run_background_phase(
        user_input=user_input, final_response=final_response or "",
        confidence=confidence, start_time=start_time, _emit=_emit_s,
        session_id=context.get("_session_id", ""), intent_type=intent_type,
    )
    for _bg_ev in _bg_result["events"]:
        yield _emit_s(_bg_ev["type"], _bg_ev["data"])

    return


async def cognitive_process(user_input, context: dict = None, event_sink=None,
                           return_cognitive_response: bool = False):
    """
    认知处理 — 纯逻辑入口，脱离SSE载体独立运行

    参数：
    - user_input: str 或 CognitiveStimulus（向后兼容）
    - context: 上下文字典（可选）
    - event_sink: EventSink实现（默认NullEventSink，静默运行）
    - return_cognitive_response: 是否返回CognitiveResponse而非dict

    返回：
    - dict: {"response": str, "confidence": float, "intent": str, "route": str, ...}
    - CognitiveResponse: 当return_cognitive_response=True时
    """
    from core.ports import NullEventSink, CognitiveResponse

    if event_sink is None:
        event_sink = NullEventSink()

    result_payload = None
    async for event_type, data in chat_stream(user_input, context or {}, event_sink=event_sink):
        if event_type == "result":
            result_payload = data

    if result_payload is None:
        result_payload = {"response": "", "confidence": 0.0, "intent": "unknown", "route": "unknown"}

    if return_cognitive_response:
        return CognitiveResponse.text(
            content=result_payload.get("response", ""),
            confidence=result_payload.get("confidence", 0.0),
            intent=result_payload.get("intent", "unknown"),
            route=result_payload.get("route", "unknown"),
        )

    return result_payload


