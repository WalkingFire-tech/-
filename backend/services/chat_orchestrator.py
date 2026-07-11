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
import json
from typing import Optional
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request
from infrastructure.database_manager import DatabaseManager

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
    final_response = None
    intent_type = "unknown"
    route = "slow"
    confidence = 0.5
    logger.info(f"⏱️ [T+0s] chat_stream开始: {user_input[:50]}")

    _chat_session_id = None
    try:
        from infrastructure.chat_history import get_chat_history
        _ch = get_chat_history()
        _chat_session_id = context.get("session_id", "") if context else ""
        if not _chat_session_id:
            _chat_session_id = _ch.create_session()
    except Exception as e:
        logger.debug(f"对话历史初始化跳过: {e}")

    user_input = user_input.strip().rstrip("/\\|").strip()
    if not user_input:
        yield _emit("result", {"response": "请输入你的问题。", "attempts": [], "intent": "greeting"})
        return

    if _chat_session_id:
        try:
            from infrastructure.chat_history import get_chat_history
            get_chat_history().add_message(_chat_session_id, "user", user_input)
        except Exception as e:
            logger.debug(f"对话历史写入user跳过: {e}")

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
                pass
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
            logger.debug(f"CBNR L1: 清除偏差{_l1_result.bias_cleared}, 不确定性={_l1_result.uncertainty:.2f}")
        if _attn.get("high_surprise"):
            logger.info(f"CBNR L1: 高预测误差({cbnr_context['l1_prediction_error']:.2f}), 增强深度推理权重")
    except Exception as e:
        logger.debug(f"CBNR L1跳过: {e}")
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
                        pass
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
                    pass
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
            pass


    history = context.get("history", []) if context else []
    conversation_context = _build_conversation_context(history)
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 对话上下文构建完成")

    # ========== 对话连续性感知 ==========
    # 检测话题跳跃、上下文衰减、指代消解需求
    # 从PheromoneField方案提取核心价值，不需要整个粒子引擎
    _continuity_signal = {}
    try:
        _continuity_signal = _perceive_continuity(user_input, history)
        if _continuity_signal.get("topic_drift"):
            yield _emit("step", {"phase": "连续性感知", "status": "done",
                "detail": f"🔄 话题漂移: {_continuity_signal['drift_direction']} (距离={_continuity_signal['drift_distance']:.2f})"})
        if _continuity_signal.get("reference_needs_resolution"):
            yield _emit("step", {"phase": "连续性感知", "status": "done",
                "detail": f"🔗 检测到指代: {_continuity_signal['reference_text']}"})
        if _continuity_signal.get("context_decay"):
            yield _emit("step", {"phase": "连续性感知", "status": "done",
                "detail": f"📉 上下文衰减: 最近{len(history)}轮对话, 活跃度={_continuity_signal['activity_level']:.2f}"})
    except Exception as e:
        logger.debug(f"对话连续性感知跳过: {e}")

    # CBNR L2: 认知瓶颈 — 压缩核心+双模型推理（接收L1的normalized_input）
    try:
        from core.cbnr.hub import get_cbnr_hub
        _cbnr_hub = get_cbnr_hub()
        _l2_result = _cbnr_hub.process_l2(_l1_normalized)
        cbnr_context["l2_compression"] = _l2_result.compression_ratio
        cbnr_context["l2_conflict_delta"] = _l2_result.conflict_delta
        cbnr_context["l2_conflict_mode"] = _l2_result.conflict_mode.value
        cbnr_context["l2_topic"] = _l2_result.core_essence.get("topic", "")
        cbnr_context["l2_entities"] = _l2_result.core_essence.get("entities", [])
        cbnr_context["l2_question_type"] = _l2_result.core_essence.get("question_type", "")
        cbnr_context["l2_causal_chain"] = _l2_result.reconstructed_output.get("causal_chain", [])
        cbnr_context["l2_counterfactuals"] = _l2_result.reconstructed_output.get("counterfactuals", [])
        logger.debug(f"CBNR L2: 压缩={_l2_result.compression_ratio:.1%}, 冲突={_l2_result.conflict_delta:.2f}, 模式={_l2_result.conflict_mode.value}")
    except Exception as e:
        logger.debug(f"CBNR L2跳过: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="CBNR_L2")

    # 通知存在层：用户正在交互
    try:
        from core.presence.existence_layer import get_existence_layer
        get_existence_layer().user_interaction()
    except Exception:
        pass

    # 资源感知：注册活跃查询 + 紧急模式预警
    _query_registered = False
    if _RESOURCE_AWARE:
        try:
            monitor = get_health_monitor()
            monitor.register_query()
            _query_registered = True
            if monitor.is_emergency():
                yield _emit("warning", {"type": "resource_emergency", "message": "系统资源紧张，正在保护性降级，回复可能较简短"})
            elif monitor.is_conservative():
                yield _emit("info", {"type": "resource_conservative", "message": "系统资源偏紧，已自动减少并行路径"})
        except Exception:
            pass

    # P1-1: 发布UserMessage事件
    try:
        from infrastructure.event_bus import bus, EventTypes
        bus.publish(EventTypes.UserMessage, {
            "query": user_input[:200],
            "timestamp": time.time(),
            "route": route,
        })
    except Exception:
        pass

    stereo_context = await _run_sync(_get_stereo_memory_context, user_input, timeout=5)
    if stereo_context:
        conversation_context = conversation_context + "\n" + stereo_context if conversation_context else stereo_context

    # 关系模型：获取当前关系状态，用于调整回复风格
    relationship_context = ""
    try:
        from core.relationship.model import get_relationship_model, InteractionType
        rm = get_relationship_model()
        rel_summary = rm.get_relationship_summary()
        trust = rel_summary.get("trust_level", 0.5)
        phase = rm.get_relationship_phase()
        interaction_count = rel_summary.get("total_interactions", 0)
        if interaction_count > 10 and trust >= 0.7:
            relationship_context = f"[你和我是老朋友了，信任度{trust:.0%}，可以更直接地交流]"
        elif trust >= 0.5:
            relationship_context = f"[关系:信任度{trust:.0%},阶段:{phase}]"
        elif trust < 0.3:
            relationship_context = f"[关系:信任度低({trust:.0%}),阶段:{phase},需要更谨慎、更详细地解释]"
        if relationship_context:
            conversation_context = (conversation_context + "\n" + relationship_context) if conversation_context else relationship_context
    except Exception as e:
        logger.debug(f"关系模型跳过: {e}")

    # ========== 阶段1：意图识别 ==========
    logger.info(f"📩 收到请求: '{user_input}'")
    yield _emit("step", {"phase": "意图识别", "status": "running", "detail": "分析问题类型和复杂度..."})

    try:
        from core.cognitive_dispatcher import get_cognitive_dispatcher
        dispatcher = get_cognitive_dispatcher()
        
        # 直接在当前线程同步调用，避免线程问题
        dispatch_result = dispatcher.dispatch(user_query=user_input, context=context)
        
        intent_type = dispatch_result.get("intent_type", "unknown")
        route = dispatch_result.get("route", "slow")
        confidence = dispatch_result.get("confidence", 0.5)
        
        # 额外验证：直接调用_quick_intent_classification
        raw_intent, raw_conf = dispatcher._quick_intent_classification(user_input)
        logger.info(f"🔍 意图识别: query='{user_input}' dispatch_intent={intent_type} raw_intent={raw_intent} route={route}")
        
        attempts.append(("意图识别", True, f"{intent_type}({route})"))
        yield _emit("step", {"phase": "意图识别", "status": "done", "detail": f"识别为「{intent_type}」，置信度={confidence:.0%}"})
    except Exception as e:
        attempts.append(("意图识别", False, str(e)[:50]))
        yield _emit("step", {"phase": "意图识别", "status": "done", "detail": "识别失败，按复杂问题处理"})

    # L1认知感知层：通过CognitivePlanner获取情绪/紧迫度/困惑度信号
    _cognitive_perception = {}
    cp = _get_cognitive_planner()
    if cp:
        try:
            _cognitive_perception = cp._perceive(user_input, context)
            emotion = _cognitive_perception.get("emotion", "neutral")
            urgency = _cognitive_perception.get("urgency", 0.5)
            confusion = _cognitive_perception.get("confusion", 0.0)
            if emotion != "neutral" or urgency > 0.7 or confusion > 0.5:
                yield _emit("step", {"phase": "L1认知感知", "status": "done",
                    "detail": f"情绪={emotion}, 紧迫度={urgency:.1f}, 困惑度={confusion:.1f}"})
            logger.debug(f"L1认知感知: emotion={emotion}, urgency={urgency:.2f}, confusion={confusion:.2f}")
            _sm = _get_self_model()
            if _sm:
                _sm.record_cognitive_cycle(perception=_cognitive_perception)
            yield _emit("thinking", {
                "phase": f"我感知到你的意图是「{intent_type}」",
                "confidence": float(confidence),
                "emotion": emotion,
                "urgency": float(urgency),
                "confusion": float(confusion),
            })

            if urgency > 0.8:
                route = "fast"
                logger.info(f"⚡ 紧迫度高({urgency:.1f})，切换到快速路由")
            if confusion > 0.7:
                methodology.setdefault("need_essence_reasoning", True)
                logger.info(f"🤔 困惑度高({confusion:.1f})，启用本质推理")
        except Exception as e:
            logger.debug(f"L1认知感知跳过: {e}")

    # ========== 阶段1.5：规则匹配与执行 ==========

    # 【墙上的画→引擎】反射级安全检查：reflex_engine处理安全关键场景
    # 之前：reflex_engine仅被旧orchestrator(planner.py)调用，chat_orchestrator完全绕过
    # 现在：在输入处理阶段执行安全检查（危险命令拦截、资源保护等）
    _reflex_action = None
    try:
        from infrastructure.reflex_engine import reflex_engine
        _reflex_ctx = {
            "user_input": user_input,
            "intent_type": intent_type,
            "recent_failures": sum(1 for _h in history[-5:] if _h.get("role") == "assistant" and ("抱歉" in _h.get("content", "") or "无法" in _h.get("content", ""))),
        }
        _reflex_action = reflex_engine.check(_reflex_ctx)
        if _reflex_action:
            yield _emit("step", {"phase": "反射安全检查", "status": "done",
                "detail": f"反射规则触发: {_reflex_action}"})
            logger.info(f"反射安全检查触发: action={_reflex_action}")
    except Exception as e:
        logger.debug(f"反射安全检查跳过: {e}")

    if _reflex_action:
        if _reflex_action in ("block", "reject") or _reflex_action.startswith("block:"):
            _block_msg = _reflex_action.split(":", 1)[1] if ":" in _reflex_action else "此操作已被安全策略拦截。"
            final_response = _block_msg
            yield _emit("step", {"phase": "安全拦截", "status": "done", "detail": "反射规则拦截了潜在危险操作"})
            yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
            return
        elif _reflex_action.startswith("warn:"):
            _rule_actions = _rule_actions if '_rule_actions' in dir() else []
            _rule_actions.append(_reflex_action)
        else:
            _rule_actions = _rule_actions if '_rule_actions' in dir() else []
            _rule_actions.append(_reflex_action)

    from backend.services.rule_evaluation import evaluate_rules_async
    _rule_actions = await evaluate_rules_async(user_input, intent_type, model_name=model if 'model' in dir() else "unknown")
    if _rule_actions:
        yield _emit("step", {"phase": "规则推理", "status": "done", "detail": f"匹配{len(_rule_actions)}条规则动作"})

    # ========== 阶段2：简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "嘿，我在。有什么想聊的，或者遇到了什么问题？我们一起看看。"
        yield _emit("step", {"phase": "快速回复", "status": "done", "detail": "问候语直接回复"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    elif intent_type == "confirmation":
        final_response = "好的，我明白了。"
        yield _emit("step", {"phase": "快速回复", "status": "done", "detail": "确认直接回复"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    elif intent_type == "history_query":
        final_response = await _solve_history_query(user_input)
        yield _emit("step", {"phase": "历史查询", "status": "done", "detail": "检索历史记录"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    elif intent_type == "challenge":
        # 质疑检测：获取上一轮回答，触发重验证
        yield _emit("step", {"phase": "质疑检测", "status": "running", "detail": "用户质疑上一轮回答，触发重验证..."})
        previous_response = _get_last_response(user_input)
        if previous_response:
            challenge_prompt = f"你上一轮的回答是：\n---\n{previous_response}\n---\n用户对此提出了质疑：「{user_input}」。请重新严谨论证，检查上一轮回答中是否有事实错误、逻辑漏洞或不严谨之处，并给出修正后的回答。如果上一轮回答是正确的，请给出更有力的论证和证据。"
            yield _emit("step", {"phase": "质疑检测", "status": "progress", "detail": "已拼接上一轮回答，启动重验证推理..."})
            model = await _get_available_ollama_model_async()
            challenge_result = None
            if model:
                challenge_result = await _fetch_ollama(challenge_prompt, model, timeout=30, conversation_context=conversation_context)
            if not challenge_result:
                challenge_result = await _fetch_external_api(challenge_prompt, conversation_context=conversation_context)
            if challenge_result and challenge_result.get("response"):
                final_response = challenge_result["response"]
                _save_to_experience_pool(user_input, final_response, success=True, intent_type="challenge", model_name="challenge")
                attempts.append(("质疑重验证", True, f"已重新论证并修正"))
                yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "重验证完成，已修正回答 ✅"})
            else:
                rule_challenge = _generate_smart_reply(challenge_prompt, "complex_query")
                if rule_challenge == "__NEED_DYNAMIC_REPLY__":
                    rule_challenge = f"我重新审视了你的质疑，但目前无法生成更深入的重验证。请提供更多具体信息。"
                final_response = f"🔍 你提出了质疑，我重新审视了上一轮的回答：\n\n{rule_challenge}"
                attempts.append(("质疑重验证", True, "规则重验证"))
                yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "使用规则重验证完成"})
            yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
            return
        else:
            yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "未找到上一轮回答记录，降级为正常处理"})
            intent_type = "complex_query"

    # ========== 阶段2.5：本质闸门 + 方法论发现 + 真谛类推 ==========
    # 先问"这个问题的本质是什么"，再问"我该用什么方式解决"，再用已有真谛类推
    essence_gate_result = None
    try:
        from core.essence_reasoner import essence_reasoner
        essence_gate_result = essence_reasoner.essence_gate(user_input)
        yield _emit("step", {"phase": "本质闸门", "status": "done", "detail": f"本质单元：{essence_gate_result['essence_unit'][:40]} | 策略：{essence_gate_result['dispatch_strategy']}"})
        if essence_gate_result["is_paradox"]:
            attempts.append(("本质闸门", True, f"悖论识别→{essence_gate_result['dispatch_strategy']}"))
        else:
            attempts.append(("本质闸门", True, essence_gate_result['essence_unit'][:40]))
    except ImportError:
        yield _emit("step", {"phase": "本质闸门", "status": "done", "detail": "本质闸门未安装，使用默认策略"})

    methodology = _discover_methodology(user_input, intent_type)
    if essence_gate_result:
        methodology["strategy"] = essence_gate_result["dispatch_strategy"]
        if essence_gate_result["is_paradox"]:
            methodology["need_essence_reasoning"] = True

    # 注入对话连续性信号到methodology
    if _continuity_signal:
        if _continuity_signal.get("topic_drift"):
            methodology["topic_drift"] = True
            methodology["drift_direction"] = _continuity_signal.get("drift_direction", "")
        if _continuity_signal.get("reference_needs_resolution"):
            methodology["reference_resolution"] = _continuity_signal.get("reference_text", "")
        if _continuity_signal.get("continuity_hint"):
            methodology["continuity_hint"] = _continuity_signal["continuity_hint"]

    # 真谛类推：用已有真谛洞察类推当前问题
    truth_insights = ""
    try:
        from core.truth_accumulator import truth_accumulator
        domain = essence_gate_result.get("domain", "通用") if essence_gate_result else "通用"
        truth_insights = truth_accumulator.get_applicable_insights(user_input, domain)
        if truth_insights:
            applicable = truth_accumulator.analogize(user_input, domain)
            insight_names = [a["name"] for a in applicable[:3]]
            yield _emit("step", {"phase": "真谛类推", "status": "done", "detail": f"类推适用：{', '.join(insight_names)}"})
            attempts.append(("真谛类推", True, f"{len(applicable)}条洞察"))
    except Exception:
        pass

    # ========== 阶段2.6：能力评估 + 本能查询 ==========
    # 先查本能：有没有匹配的本能级技能可直接触发？
    instinct_hit = None
    skeleton_analogy = None
    try:
        from core.skill_emergence import SkillEmergence
        se = SkillEmergence()
        instinct_hit = se.reflex_query(user_input)
        if instinct_hit:
            yield _emit("step", {"phase": "本能查询", "status": "done",
                "detail": f"⚡ 本能触发: {instinct_hit['skill_name']} (置信度{instinct_hit['confidence']:.2f})"})
            methodology["instinct_path"] = instinct_hit["solution_path"]
            methodology["instinct_skeleton"] = instinct_hit.get("skeleton", "")
    except Exception:
        pass

    # 没有本能→查骨架联想：有没有结构相似的历史经验可迁移？
    if not instinct_hit:
        try:
            from core.cognition.experience_abstractor import ExperienceAbstractor
            skeleton_analogy = ExperienceAbstractor.find_analogous(user_input)
            if skeleton_analogy:
                yield _emit("step", {"phase": "骨架联想", "status": "done",
                    "detail": f"🧠 类比迁移: {skeleton_analogy['skill_name']} (相似度{skeleton_analogy['similarity']:.2f})"})
                methodology["analogous_skeleton"] = skeleton_analogy["skeleton"]
                methodology["analogous_path"] = skeleton_analogy["solution_path"]
        except Exception:
            pass

    # 能力缺口检测：我有没有合适的工具？
    capability_gap = None
    try:
        from core.tool_registry import tool_registry
        applicable_tools = tool_registry.plan_tools(user_input, intent_type, methodology=methodology)
        if not applicable_tools and intent_type not in ("greeting", "confirmation", "simple_query"):
            capability_gap = f"解决'{user_input[:40]}'所需的工具"
            yield _emit("step", {"phase": "能力评估", "status": "done",
                "detail": f"⚠️ 检测到能力缺口: 无适用工具"})
            methodology["capability_gap"] = capability_gap
    except Exception:
        pass

    # ========== 阶段2.7：三思后行 — R4七维自检 ==========
    # 在关键决策点（能力评估后、执行前）强制执行元宪法检查
    _r4_result = _r4_self_check(user_input, intent_type, methodology, capability_gap)
    if _r4_result.get("warnings"):
        for _w in _r4_result["warnings"]:
            yield _emit("step", {"phase": "三思后行", "status": "warning", "detail": _w})
    if _r4_result.get("blocked"):
        final_response = _r4_result["block_reason"]
        yield _emit("step", {"phase": "三思后行", "status": "done", "detail": f"🛑 行动被阻断: {_r4_result['block_reason']}"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    if _r4_result.get("adjustments"):
        for _adj_key, _adj_val in _r4_result["adjustments"].items():
            methodology[_adj_key] = _adj_val

    # 事实锚点查询：从事实库获取相关客观事实，注入推理上下文
    fact_context = ""
    try:
        from infrastructure.fact_store import fact_store
        fact_assertions = await _run_sync(fact_store.search_by_keywords, user_input, limit=5, timeout=5)
        if fact_assertions:
            fact_parts = []
            for fa in fact_assertions:
                fact_parts.append(f"- {fa['subject']} {fa['predicate']} {fa['object']} (置信度{fa['confidence']:.0%}, 来源:{fa['source']})")
            fact_context = "【事实锚点-客观验证】\n" + "\n".join(fact_parts)
            yield _emit("step", {"phase": "事实锚点", "status": "done", "detail": f"检索到{len(fact_assertions)}条相关事实"})
            attempts.append(("事实锚点", True, f"{len(fact_assertions)}条"))
        else:
            yield _emit("step", {"phase": "事实锚点", "status": "done", "detail": "无相关事实锚点"})
    except Exception as e:
        logger.debug(f"事实锚点查询跳过: {e}")

    if fact_context and not truth_insights:
        truth_insights = fact_context
    elif fact_context:
        truth_insights = fact_context + "\n" + truth_insights

    # 分层记忆查询（P1-6）：战略/程序/工具三层记忆上下文
    try:
        from core.memory.layered_memory import layered_memory
        lm_context = layered_memory.get_context_for_query(user_input)
        if lm_context["context"]:
            if truth_insights:
                truth_insights = lm_context["context"] + "\n" + truth_insights
            else:
                truth_insights = lm_context["context"]
            yield _emit("step", {"phase": "分层记忆", "status": "done",
                "detail": f"战略{lm_context['strategic_count']}/程序{lm_context['procedural_count']}/工具{lm_context['tool_count']}"})
    except Exception as e:
        logger.debug(f"分层记忆查询跳过: {e}")

    yield _emit("step", {"phase": "方法论发现", "status": "done", "detail": f"解决策略：{methodology['strategy']} | 来源优先级：{' → '.join(methodology['source_priority'][:3])}"})

    # ========== 阶段1.6：规则动作注入 ==========
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
                    intent_type = _new_intent
            except Exception:
                pass

    # ========== 阶段2：能力评估与获取 ==========
    # 在行动之前，先想清楚：我能不能做这件事？如果不能，怎么获得能力？
    _capability_assessment = None
    try:
        from core.learning.capability_gap_learner import capability_gap_learner
        _capability_assessment = capability_gap_learner.assess_capability(user_input, intent_type, methodology)
        if _capability_assessment and _capability_assessment.get("gap_detected"):
            gap_type = _capability_assessment["gap_type"]
            yield _emit("thinking", {
                "phase": f"我发现这个问题需要「{_capability_assessment['needed_capability']}」的能力，我正在想办法获得它",
                "gap_type": gap_type,
                "resolution_plan": _capability_assessment.get("resolution_plan", ""),
            })
            yield _emit("step", {"phase": "能力评估", "status": "running",
                "detail": f"检测到能力缺失: {gap_type}，正在获取能力..."})

            _acquired = await capability_gap_learner.acquire_capability(_capability_assessment)
            if _acquired:
                yield _emit("step", {"phase": "能力评估", "status": "done",
                    "detail": f"已获得能力: {_acquired}"})
                methodology = capability_gap_learner.update_methodology(methodology, _capability_assessment)
            else:
                yield _emit("step", {"phase": "能力评估", "status": "done",
                    "detail": f"能力获取进行中: {_capability_assessment.get('resolution_plan', '探索中')}"})
        else:
            yield _emit("step", {"phase": "能力评估", "status": "done", "detail": "能力充足，开始执行"})
    except Exception as _ce:
        logger.debug(f"能力评估跳过: {_ce}")

    # ========== 阶段3：多策略并行尝试 ==========
    yield _emit("thinking", {
        "phase": f"我正在用多种策略同时思考你的问题",
        "confidence": float(confidence) if 'confidence' in dir() else 0.5,
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

    # ========== 阶段4：对比择优 ==========

    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 进入阶段4: 对比择优, {len(candidates)}个候选")
    for i, c in enumerate(candidates):
        logger.debug(f"[ORCH_DIAG] 候选{i}: source={c.get('source')}, quality={c.get('quality')}, resp_len={len(c.get('response',''))}, resp_preview={c.get('response','')[:80]}")
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
            logger.debug(f"ToolBuilder观察跳过: {e}")

        # 贡献度归因（SHAP风格）+ 路径权重更新（AdaBoost风格，不确定性感知）
        try:
            from core.contrib_attributor import contrib_attributor
            from core.path_weight_manager import path_weight_manager
            attrib = contrib_attributor.compute_contributions(
                candidates, final_response, best["source"], user_input
            )
            for src, score in attrib.get("contributions", {}).items():
                unc_info = (attrib.get("retrieval_uncertainties") or {}).get(src)
                uncertainty = unc_info.get("retrieval_entropy") if unc_info else None
                path_weight_manager.update_weight(src, True, score, uncertainty=uncertainty)
            if attrib.get("contributions"):
                contrib_str = " | ".join(f"{k}:{v:.0%}" for k, v in list(attrib["contributions"].items())[:5] if v is not None)
                unc_str = ""
                if attrib.get("retrieval_uncertainties"):
                    unc_dims = len(attrib["retrieval_uncertainties"])
                    unc_str = f" | 不确定性维度:{unc_dims}"
                yield _emit("step", {"phase": "贡献归因", "status": "done", "detail": f"贡献度: {contrib_str}{unc_str}"})
        except Exception as e:
            logger.debug(f"贡献归因跳过: {e}")

        # 动态概率场初始化（异步概率计算核心）+ 不确定性驱动路由
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
                    "detail": f"概率分布: top={prob_dist['top']['source']}({prob_dist['top']['probability']:.0%}) 熵={prob_dist['entropy']:.2f}{action_hint}"})
        except Exception as e:
            logger.debug(f"概率场初始化跳过: {e}")

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
            logger.debug(f"世界模型反事实推理跳过: {e}")
    else:
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": "无有效候选结果"})

    # L2学习层 + L3整合层：通过CognitivePlanner从交互中学习并整合知识
    _cognitive_learning = {}
    _cognitive_integration = {}
    if cp and _cognitive_perception:
        try:
            _cognitive_learning = cp._learn(user_input, _cognitive_perception)
            knowledge_gained = _cognitive_learning.get("knowledge_gained", 0)
            if knowledge_gained > 0:
                yield _emit("step", {"phase": "L2认知学习", "status": "done",
                    "detail": f"获得{knowledge_gained}项知识, 置信度={_cognitive_learning.get('confidence', 0.7):.0%}"})
            logger.debug(f"L2认知学习: gained={knowledge_gained}, sources={_cognitive_learning.get('sources', [])}")
        except Exception as e:
            logger.debug(f"L2认知学习跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L2_cognitive_learning")
        try:
            _cognitive_integration = cp._integrate(_cognitive_learning)
            if _cognitive_integration.get("success"):
                core_know = _cognitive_integration.get("core_knowledge", [])
                if core_know:
                    yield _emit("step", {"phase": "L3认知整合", "status": "done",
                        "detail": f"整合{len(core_know)}项核心知识"})
            logger.debug(f"L3认知整合: success={_cognitive_integration.get('success')}")
        except Exception as e:
            logger.debug(f"L3认知整合跳过: {e}")
    _sm = _get_self_model()
    if _sm and (_cognitive_learning or _cognitive_integration):
        _sm.record_cognitive_cycle(learning=_cognitive_learning, integration=_cognitive_integration)
    if _cognitive_learning and _cognitive_learning.get("knowledge_gained"):
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

    # ========== 阶段4.5：本质推理与自洽验证 ==========
    essence_passed = True
    essence_confidence = 1.0
    essence_issues = []
    essence_cross_validated = False
    if final_response:
        yield _emit("step", {"phase": "本质推理", "status": "running", "detail": "第一性原理推理→自洽性验证→事实锚点验证→跨域一致性→反向归谬..."})
        try:
            from core.essence_reasoner import essence_reasoner
            essence_result = await _run_sync(essence_reasoner.reason, user_input, final_response, conversation_context, timeout=15, phase="本质推理")
            
            # 事实锚点验证：用事实库断言校验回复中的关键声明
            fact_verified = True
            fact_issues = []
            try:
                from infrastructure.fact_store import fact_store
                negations = await _run_sync(fact_store.get_negations, user_input, timeout=5, phase="事实锚点验证")
                if negations:
                    for neg in negations:
                        neg_claim = f"{neg['subject']}{neg['predicate']}{neg['object']}"
                        if neg_claim in final_response:
                            fact_verified = False
                            fact_issues.append(f"与已纠错事实冲突: {neg_claim}")
            except Exception:
                pass
            
            if not fact_verified:
                essence_result["passed"] = False
                essence_result["consistency_issues"].extend(fact_issues)
                if essence_result["confidence"] > 0.7:
                    essence_result["confidence"] = 0.5
                yield _emit("step", {"phase": "事实验证", "status": "done", "detail": f"发现{len(fact_issues)}个事实冲突 ⚠️"})
            elif fact_context:
                yield _emit("step", {"phase": "事实验证", "status": "done", "detail": "事实锚点验证通过 ✅"})
            
            if essence_result["passed"]:
                essence_passed = True
                essence_confidence = essence_result["confidence"]
                attempts.append(("本质推理", True, f"{essence_result['verdict']} (置信度{essence_result['confidence']:.0%})"))
                yield _emit("step", {"phase": "本质推理", "status": "done", "detail": f"推理自洽 ✅ {essence_result['verdict']}"})
            else:
                essence_passed = False
                essence_confidence = essence_result["confidence"]
                essence_issues = essence_result.get("consistency_issues", [])
                issues_str = '；'.join(essence_result["consistency_issues"][:3])
                attempts.append(("本质推理", False, f"发现{len(essence_result['consistency_issues'])}个问题：{issues_str[:60]}"))
                yield _emit("step", {"phase": "本质推理", "status": "done", "detail": f"发现自洽性问题：{issues_str[:80]}，尝试修正..."})

                if essence_result["enhanced_response"] and len(essence_result["enhanced_response"]) > len(final_response):
                    final_response = essence_result["enhanced_response"]
                    yield _emit("step", {"phase": "本质修正", "status": "done", "detail": "已附加推理审视和自洽性提示"})

                # 本质推理发现严重问题→多源并行交叉验证（不用同一个模型重推）
                if essence_result["confidence"] < 0.5:
                    yield _emit("step", {"phase": "多源交叉验证", "status": "running", "detail": "置信度过低，启动多源并行交叉验证..."})
                    multi_sources = []

                    # 来源1：外部模型（与本地模型不同源，避免偏见叠加）
                    ext_result = await _fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                    if ext_result and ext_result.get("response"):
                        multi_sources.append({"source": ext_result["source"], "response": ext_result["response"]})

                    # 来源2：知识库精确检索
                    know_result = await _fetch_knowledge(user_input)
                    if know_result and know_result.get("response"):
                        multi_sources.append({"source": "知识库", "response": know_result["response"]})

                    # 来源3：经验池（已含历史经验注入）
                    exp_result = await _fetch_experience(user_input)
                    if exp_result and exp_result.get("response"):
                        multi_sources.append({"source": "经验池", "response": exp_result["response"]})

                    if len(multi_sources) >= 2:
                        essence_cross_validated = True
                        # 多源差异萃取
                        yield _emit("step", {"phase": "多源交叉验证", "status": "progress", "detail": f"收集到{len(multi_sources)}个来源，进行差异萃取..."})
                        merged = _cross_source_merge(user_input, multi_sources, essence_result["consistency_issues"])
                        if merged:
                            final_response = merged
                            _save_to_experience_pool(user_input, merged, success=True, intent_type="multi_source_merge", model_name="merge")
                            attempts.append(("多源交叉验证", True, f"{len(multi_sources)}源融合成功"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": f"多源融合完成 ✅ ({len(multi_sources)}个来源)"})
                        else:
                            # 无法融合→诚实罗列分歧
                            divergence = _list_divergences(user_input, multi_sources)
                            final_response = divergence
                            attempts.append(("多源交叉验证", True, "罗列分歧"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "多源存在分歧，诚实罗列各方观点"})
                    elif len(multi_sources) == 1:
                        essence_cross_validated = True
                        single = multi_sources[0]
                        recheck = None
                        try:
                            from core.essence_reasoner import essence_reasoner
                            recheck = await _run_sync(essence_reasoner.reason, user_input, single["response"], conversation_context, timeout=30)
                        except Exception:
                            pass
                        if recheck and recheck["confidence"] > essence_result["confidence"]:
                            final_response = single["response"]
                            _save_to_experience_pool(user_input, final_response, success=True, intent_type="single_source", model_name=best.get("source","unknown") if best else "unknown")
                            attempts.append(("多源交叉验证", True, f"单源({single['source']})置信度提升"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": f"单源验证通过 ({single['source']})"})
                        else:
                            attempts.append(("多源交叉验证", False, "单源未改善"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "单源验证未改善，保留修正后回答"})
                    else:
                        yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "无可用外部来源，保留修正后回答"})
        except ImportError:
            yield _emit("step", {"phase": "本质推理", "status": "done", "detail": "本质推理器未安装，跳过"})
        except asyncio.TimeoutError:
            logger.warning("本质推理超时(15秒)")
            yield _emit("step", {"phase": "本质推理", "status": "timeout", "detail": "本质推理超时，跳过验证继续"})
        except Exception as e:
            logger.debug(f"本质推理异常: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="essence_reasoning")
            yield _emit("step", {"phase": "本质推理", "status": "done", "detail": "本质推理异常，继续后续验证"})

    # ========== 阶段5：自我验证 ==========
    if not final_response:
        try:
            from core.learning.capability_gap_learner import capability_gap_learner
            gap = capability_gap_learner.detect_gap(user_input, attempts, "")
            if gap:
                logger.info(f"🔍 检测到能力缺失: {gap['gap_type']} — {user_input[:50]}")
                gap_resolution = await capability_gap_learner.try_resolve_gap(gap)
                if gap_resolution:
                    logger.info(f"🧠 能力缺失学习结果: {gap_resolution[:100]}")
                    yield _emit("learning", {"type": "capability_gap", "gap_type": gap["gap_type"], "resolution": gap_resolution[:200]})

                # 【墙上的画→引擎】工具构建器：当能力缺失为工具类时，调用ToolSelfBuilder
                # 审计报告要求：observe_need()记录需求，需求频率达阈值后build_tool()自动构建
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
                                yield _emit("learning", {"type": "tool_built", "tool_id": _build_result.tool_id})
                            else:
                                logger.debug(f"工具构建器: 构建失败 - {_build_result.error}")
                    except Exception as _tbe:
                        logger.debug(f"工具构建器跳过: {_tbe}")
        except Exception as _ge:
            logger.debug(f"能力缺失学习异常: {_ge}")

        fallback = _generate_meaningful_fallback(user_input, attempts)
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
                    from backend.services.persistent_solver import persistent_solve, review_solution
                    _ps_events = []
                    async def _ps_emit(event_type, data):
                        _ps_events.append((event_type, data))

                    yield _emit("step", {"phase": "持续求解", "status": "running", "detail": "常规方法未解决，启动持续求解引擎..."})
                    ps_response, ps_new_attempts, ps_solved = await persistent_solve(
                        user_input, attempts,
                        conversation_context=conversation_context,
                        truth_insights=truth_insights,
                        emit_fn=_ps_emit,
                    )
                    for _et, _ed in _ps_events:
                        yield _emit(_et, _ed)
                    attempts.extend(ps_new_attempts)
                    if ps_solved and ps_response:
                        final_response = ps_response
                        attempts.append(("持续求解", True, f"第{len(ps_new_attempts)}轮成功"))
                        await review_solution(user_input, ps_response, attempts, True)
                    else:
                        final_response = ps_response or _never_give_up_response(user_input, attempts)
                        attempts.append(("持续求解", False, f"{len(ps_new_attempts)}轮后未解决"))
                except Exception as _pse:
                    logger.warning(f"持续求解异常: {_pse}")
                    final_response = _never_give_up_response(user_input, attempts)
                    attempts.append(("持续求解", False, f"异常: {str(_pse)[:60]}"))
        else:
            final_response = fallback
            attempts.append(("降级保护", True, "基础回复"))
        yield _emit("step", {"phase": "自我验证", "status": "done", "detail": "使用动态推理回复"})

    if final_response:
        yield _emit("step", {"phase": "自我验证", "status": "running", "detail": "验证回复质量和逻辑性..."})

        if intent_type == "hardware" and final_response:
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
                yield _emit("step", {"phase": "意图-产出对照", "status": "warning", "detail": f"⚠️ {_mismatch_reason}"})
                try:
                    from core.cognition.failure_classifier import FailureClassifier
                    from core.cognition.audit_logger import AuditLogger
                    reflection = {"status": "mismatch", "reason": _mismatch_reason}
                    category = FailureClassifier.classify(reflection)
                    FailureClassifier.record_failure(category, user_input, {"intent_type": intent_type})
                    AuditLogger.log(user_input, {"intent_type": intent_type}, final_response[:200], reflection)
                except Exception:
                    pass
            else:
                verification = await _self_verify(user_input, final_response)
        else:
            verification = await _self_verify(user_input, final_response)
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
            yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"验证通过 ✅ 置信度{verification['confidence']:.0%}"})
        else:
            filtered_issues = [i for i in verification["issues"] if i not in essence_issues]
            if not filtered_issues and essence_cross_validated:
                attempts.append(("自我验证", True, f"本质推理已覆盖 (置信度{verification['confidence']:.0%})"))
                yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"本质推理已覆盖验证，跳过冗余修正 ✅"})
            else:
                attempts.append(("自我验证", False, f"问题: {'; '.join(verification['issues'])}"))
                yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"发现问题: {'; '.join(verification['issues'])}，尝试修正..."})

                # 验证不通过，尝试用Ollama重新推理（如果之前没有Ollama结果且未做多源交叉验证）
                if not essence_cross_validated and not any(a[0].startswith("Ollama") and a[1] for a in attempts):
                    model = await _get_available_ollama_model_async()
                    if model:
                        yield _emit("step", {"phase": "修正推理", "status": "running", "detail": f"验证未通过，调用 {model} 重新推理..."})
                        retry = await _fetch_ollama(user_input, model, timeout=15, conversation_context=conversation_context)
                        if retry and retry.get("response"):
                            retry_score = _score_response(retry, user_input)
                            current_score = _score_response(best, user_input) if best else 0
                            if retry_score > current_score:
                                final_response = retry["response"]
                                _save_to_experience_pool(user_input, retry["response"], success=True, intent_type="retry_correction", model_name="retry")
                                attempts.append(("修正推理", True, f"Ollama修正成功 (评分{retry_score:.0f}>{current_score:.0f})"))
                                yield _emit("step", {"phase": "修正推理", "status": "done", "detail": f"修正成功，新评分{retry_score:.0f}"})
                            else:
                                attempts.append(("修正推理", False, f"修正结果评分{retry_score:.0f}未超过原{current_score:.0f}"))
                                yield _emit("step", {"phase": "修正推理", "status": "done", "detail": "修正结果未优于原结果，保留原回复"})
                        else:
                            yield _emit("step", {"phase": "修正推理", "status": "done", "detail": "修正推理未返回有效结果"})
                    else:
                        yield _emit("step", {"phase": "修正推理", "status": "done", "detail": "无可用模型"})

        # 科学免责声明：基于语义理解判断"我刚才是否做出了需要验证的科学断言"
        # 不是关键词检索，而是理解回复的语义结构
        import re as _re_science
        content_understanding = _understand_response_content(user_input, final_response, cbnr_context)
        _simple_fact_exempt = bool(_re_science.search(r'(?:等于几|几加几|\d+\s*[+\-*/×÷]\s*\d+)', user_input))
        if content_understanding["needs_verification"] and content_understanding["claim_type"] == "scientific" and not _simple_fact_exempt:
            domain_ref = content_understanding["domain"]
            disclaimer = f"\n\n---\n⚠️ 以上涉及科学事实，我的推论可能存在偏差，建议参考{domain_ref}。\n（此声明仅为核实建议，非本回答的立论依据，请勿在后续推理中引用此声明）\n---"
            if "建议参考" not in final_response:
                final_response += disclaimer
                attempts.append(("科学免责", True, f"已附加{domain_ref}不确定性声明"))
                yield _emit("step", {"phase": "科学免责", "status": "done", "detail": f"语义理解: {content_understanding['reasoning']}，已附加不确定性声明 ⚠️"})

        # 不确定性坦诚表达（精神内核原则3+7：困惑时坦诚 + 有温度地回应）
        # 不是泛泛的"建议你也看看"，而是基于实际推理过程的针对性结语
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
            pass

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
                pass
        if intent_type == "code" and final_response:
            code_verify = _verify_code_response(user_input, final_response)
            if code_verify["passed"]:
                attempts.append(("代码验证", True, code_verify["detail"]))
                yield _emit("step", {"phase": "代码验证", "status": "done", "detail": f"代码验证通过 ✅ {code_verify['detail']}"})
            else:
                attempts.append(("代码验证", False, code_verify["detail"]))
                yield _emit("step", {"phase": "代码验证", "status": "done", "detail": f"代码验证发现问题：{code_verify['detail']}"})

    # ========== 阶段5.5：适应度评估 ==========
    fitness_score = None
    if final_response:
        try:
            from infrastructure.fitness_evaluator import fitness_evaluator
            fitness_score = await _run_sync(
                fitness_evaluator.evaluate,
                question=user_input,
                response=final_response,
                user_feedback=0,
                intent_type=intent_type,
                timeout=5
            )
            if fitness_score.is_factual_question:
                attempts.append(("适应度评估", True, f"客观{fitness_score.objective_score:.0f}/主观{fitness_score.subjective_score:.0f}→总分{fitness_score.final_score:.0f}"))
                yield _emit("step", {"phase": "适应度评估", "status": "done", "detail": f"事实性问题 | 客观分{fitness_score.objective_score:.0f} 主观分{fitness_score.subjective_score:.0f} 总分{fitness_score.final_score:.0f}"})
                
                should_inject, inject_reason = fitness_evaluator.should_inject_knowledge(fitness_score)
                if should_inject:
                    yield _emit("step", {"phase": "适应度评估", "status": "done", "detail": f"⚠️ 建议知识注入: {inject_reason}"})
            else:
                yield _emit("step", {"phase": "适应度评估", "status": "done", "detail": f"开放性问题 | 主观分{fitness_score.subjective_score:.0f}"})
        except Exception as e:
            logger.debug(f"适应度评估跳过: {e}")

    # 概率场更新：用适应度结果作为证据更新概率分布 + 闭环校准反馈
    try:
        from core.dynamic_probability_field import dynamic_probability_field
        if fitness_score and dynamic_probability_field._candidates:
            ev_type = "quality_boost" if fitness_score.final_score >= 60 else "essence_fail"
            dynamic_probability_field.update({
                "type": ev_type,
                "confidence": fitness_score.final_score / 100.0,
                "source": best.get("source", "") if best else "",
                "content": final_response[:300] if final_response else "",
            })
            dynamic_probability_field.save_snapshot(user_input)
            if best:
                dynamic_probability_field.record_outcome(
                    best.get("source", ""), fitness_score.final_score
                )
    except Exception as e:
        logger.debug(f"概率场更新跳过: {e}")

    # ========== 阶段5.55：ReAct迭代循环（P0-3/P0-5 — 适应度<60时启动Reason→Act→Observe→Reflect） ==========
    if fitness_score and fitness_score.final_score < 60 and fitness_score.final_score >= 20 and final_response and route == "slow":
        yield _emit("step", {"phase": "ReAct循环", "status": "running",
            "detail": f"适应度{fitness_score.final_score:.0f}不足60，启动ReAct迭代推理..."})
        try:
            from core.react_engine import react_engine

            # ReactEnhancer短板聚焦（XGBoost风格）：识别最弱维度，注入增强提示
            react_enhanced_query = user_input
            try:
                from core.react_enhancer import react_enhancer
                coverage = {}
                if fitness_score:
                    if hasattr(fitness_score, 'factual_score') and fitness_score.factual_score is not None:
                        coverage["factual_accuracy"] = fitness_score.factual_score / 100.0
                    if hasattr(fitness_score, 'subjective_score') and fitness_score.subjective_score is not None:
                        coverage["subjective_quality"] = fitness_score.subjective_score / 100.0
                    if hasattr(fitness_score, 'completeness') and fitness_score.completeness is not None:
                        coverage["completeness"] = fitness_score.completeness / 100.0
                gap = react_enhancer.identify_gap({
                    "query": user_input, "coverage": coverage, "iteration": 0
                })
                if gap.get("severity", 0) > 0.3:
                    react_enhanced_query = react_enhancer.generate_focused_prompt(gap, user_input)
                    yield _emit("step", {"phase": "短板聚焦", "status": "done",
                        "detail": f"识别短板: {gap['gap_type']}(严重度{gap['severity']:.2f}), 已注入增强提示"})
            except Exception as e:
                logger.debug(f"ReactEnhancer跳过: {e}")

            async def _react_fitness(q, r):
                try:
                    from infrastructure.fitness_evaluator import fitness_evaluator
                    return await _run_sync(fitness_evaluator.evaluate, question=q, response=r, timeout=5)
                except Exception:
                    return None

            react_result = await react_engine.run(
                query=react_enhanced_query,
                initial_response=final_response,
                initial_quality=fitness_score.final_score,
                candidates=candidates,
                fitness_score=fitness_score,
                intent_type=intent_type,
                conversation_context=conversation_context,
                truth_insights=truth_insights,
                fetch_ollama_fn=_fetch_ollama_all,
                fetch_external_fn=_fetch_external_api,
                fetch_knowledge_fn=_fetch_knowledge,
                fetch_experience_fn=_fetch_experience,
                self_reason_fn=_self_reason,
                fitness_fn=_react_fitness,
            )

            for it in react_result.iterations:
                status = "改善 ✅" if it.improved else "未显著改善"
                yield _emit("step", {"phase": f"ReAct-R{it.iter_num}", "status": "done",
                    "detail": f"策略:{it.action} | {status} | 适应度→{it.quality:.0f}"})

            if react_result.improved and react_result.final_response:
                final_response = react_result.final_response
                fitness_score_final = react_result.final_quality
                attempts.append(("ReAct循环", True,
                    f"{react_result.total_iterations}次迭代, 适应度{fitness_score.final_score:.0f}→{fitness_score_final:.0f}, 策略:{'+'.join(react_result.strategies_used)}"))
                yield _emit("step", {"phase": "ReAct循环", "status": "done",
                    "detail": f"✅ ReAct改善: {react_result.total_iterations}次迭代, 适应度{fitness_score.final_score:.0f}→{fitness_score_final:.0f}"})
            else:
                attempts.append(("ReAct循环", False, f"{react_result.total_iterations}次迭代未改善"))
                yield _emit("step", {"phase": "ReAct循环", "status": "done",
                    "detail": f"ReAct {react_result.total_iterations}次迭代未显著改善，保留当前结果"})
        except Exception as e:
            logger.debug(f"ReAct循环异常: {e}")
            yield _emit("step", {"phase": "ReAct循环", "status": "done", "detail": "ReAct循环跳过"})
    elif fitness_score and fitness_score.final_score >= 60:
        pass

    # ========== 阶段5.6：闭环迭代（P0-5 — 适应度<20的最终兜底，ReAct也无法挽救时） ==========
    if fitness_score and not fitness_score.is_factual_question and fitness_score.subjective_score >= 40:
        pass
    elif fitness_score and fitness_score.final_score < 20 and final_response and route == "slow":
        yield _emit("step", {"phase": "闭环迭代", "status": "running",
            "detail": f"适应度{fitness_score.final_score:.0f}过低，启动闭环迭代..."})
        try:
            from core.closed_loop_orchestrator import closed_loop_orchestrator, LoopContext, LoopState
            loop_ctx = LoopContext(
                query=user_input,
                conversation_context=conversation_context,
                intent_type=intent_type,
                complexity=complexity if 'complexity' in dir() else 0.5,
                confidence=confidence,
                route=route,
                iteration=0,
                candidates=candidates if candidates else [],
                best=best._asdict() if best and hasattr(best, '_asdict') else (best if isinstance(best, dict) else None),
                final_response=final_response,
                attempts=attempts[:],
                fitness_score=fitness_score,
            )
            loop_ctx.evaluation_passed = False
            loop_ctx.evaluation_issues = [f"适应度{fitness_score.final_score:.0f}低于阈值40"]
            loop_ctx.state = LoopState.EXECUTION
            
            loop_result = await closed_loop_orchestrator.orchestrate_from_context(loop_ctx)
            
            if loop_result.final_response and len(loop_result.final_response) > len(final_response):
                final_response = loop_result.final_response
                attempts.append(("闭环迭代", True, f"迭代{loop_result.iteration + 1}次改善"))
                yield _emit("step", {"phase": "闭环迭代", "status": "done",
                    "detail": f"✅ 闭环迭代改善 (迭代{loop_result.iteration + 1}次)"})
            else:
                attempts.append(("闭环迭代", False, "迭代未改善"))
                yield _emit("step", {"phase": "闭环迭代", "status": "done", "detail": "迭代未显著改善，保留当前结果"})
        except Exception as e:
            logger.debug(f"闭环迭代异常: {e}")
            yield _emit("step", {"phase": "闭环迭代", "status": "done", "detail": "闭环迭代跳过"})

    # ========== 阶段6：精神内核验证 ==========
    yield _emit("step", {"phase": "精神验证", "status": "running", "detail": "验证回复是否符合核心原则..."})

    # 【墙上的画→引擎】元宪法R1/R3：沙盒验证 + 人类批准
    # 审计报告要求：
    #   R1: "若回复引用了未经验证的真谛，应触发警告或降级"（不只是代码块）
    #   R3: "当进化操作影响范围超过阈值，应通过SSE推送人类审批请求"（不只是追加文本）
    _meta_constitution_violation = None
    _r1_unverified_truths = []
    _r3_needs_approval = False
    try:
        # R1检查①：代码/命令沙盒验证
        if final_response and any(kw in final_response for kw in ["```", "import ", "def ", "pip install", "rm ", "exec("]):
            _code_blocks = [line for line in final_response.split("\n") if line.strip().startswith(("import ", "def ", "pip ", "rm ", "exec("))]
            if _code_blocks:
                from backend.services.code_verifier import verify_code_response
                _code_check = verify_code_response(user_input, final_response)
                if not _code_check.get("passed", True):
                    _meta_constitution_violation = f"R1(沙盒验证-代码): {_code_check.get('detail', '代码未通过验证')}"
                    logger.warning(f"元宪法R1违反: {_meta_constitution_violation}")

        # R1检查②：回复引用了未经验证的真谛（level<=L2且evidence<3）
        if final_response and not _meta_constitution_violation:
            try:
                from core.truth_accumulator import truth_accumulator as _r1_ta
                _all_truths = _r1_ta.get_all_truths()
                for _t in _all_truths:
                    _t_name = _t.get("name", "")
                    _t_level = _t.get("level", "L1")
                    _t_evidence = _t.get("evidence", 0)
                    if _t_name and _t_name in final_response:
                        if _t_level in ("L1", "L2") and _t_evidence < 3:
                            _r1_unverified_truths.append(f"{_t_name}(L={_t_level},证据={_t_evidence})")
                if _r1_unverified_truths:
                    _meta_constitution_violation = f"R1(沙盒验证-真谛): 回复引用了未验证真谛: {', '.join(_r1_unverified_truths[:3])}"
                    if "⚠️" not in final_response:
                        final_response += f"\n\n⚠️ 以上引用的洞察（{', '.join(_r1_unverified_truths[:2])}）尚未经过充分验证，请谨慎参考。"
                    logger.warning(f"元宪法R1违反: {_meta_constitution_violation}")
            except Exception:
                pass

        # R3检查：涉及系统级变更的回复需要人类确认
        if final_response and any(kw in final_response for kw in ["我将修改", "我会删除", "我将关闭", "我将重启", "我将重置"]):
            if "确认" not in final_response and "请确认" not in final_response:
                _r3_needs_approval = True
                _meta_constitution_violation = f"R3(人类批准): 回复暗示系统级操作，需人类确认"
                yield _emit("approval_request", {
                    "type": "system_operation",
                    "message": "回复涉及系统级操作，需要您的确认才会执行",
                    "options": ["确认执行", "取消操作"],
                })
                logger.warning(f"元宪法R3: 系统级操作需人类确认，已推送SSE审批请求")

        if _meta_constitution_violation:
            attempts.append(("元宪法检查", not _r3_needs_approval, _meta_constitution_violation[:80]))
            yield _emit("step", {"phase": "元宪法", "status": "done", "detail": f"⚠️ {_meta_constitution_violation[:60]}"})
        else:
            yield _emit("step", {"phase": "元宪法", "status": "done", "detail": "R1/R3检查通过 ✅"})
    except Exception as e:
        logger.debug(f"元宪法检查跳过: {e}")

    if SPIRIT_CORE_AVAILABLE:
        original_response = final_response
        try:
            from core.spirit_core import spirit_core as _spirit_core_enforce
            final_response = await _run_sync(_spirit_core_enforce.enforce_on_output, final_response, source="chat_handler", query=user_input, timeout=3, phase="精神内核")
            if final_response != original_response:
                attempts.append(("精神内核修正", True, "自动修正"))
                yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "已自动修正"})
            else:
                attempts.append(("精神内核验证", True, "符合精神"))
                yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "回复符合核心原则 ✅"})
        except asyncio.TimeoutError:
            logger.warning("精神内核验证超时(3秒)，跳过")
            yield _emit("step", {"phase": "精神验证", "status": "timeout", "detail": "精神内核验证超时，跳过"})
        except Exception as e:
            logger.debug(f"精神内核异常: {e}")
            yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "精神内核异常，跳过验证"})
    else:
        yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "基础验证完成"})

    # L4认知校验层：通过CognitivePlanner校验整合结果并生成认知级响应
    _cognitive_validation = {}
    _l4_doubts = []
    _l4_should_correct = False
    if cp and _cognitive_integration and final_response:
        try:
            _cognitive_validation, _cognitive_response = cp._validate_and_respond(
                _cognitive_integration, user_input, _cognitive_perception
            )
            val_status = _cognitive_validation.get("status", "unknown")
            val_conf = _cognitive_validation.get("confidence", 0)
            doubts = _cognitive_validation.get("doubts", [])
            _l4_doubts = doubts if isinstance(doubts, list) else []
            if val_status == "pass" and val_conf >= 0.7:
                attempts.append(("L4认知校验", True, f"校验通过(置信度{val_conf:.0%})"))
            elif doubts:
                attempts.append(("L4认知校验", True, f"存疑{len(doubts)}项(置信度{val_conf:.0%})"))
            logger.debug(f"L4认知校验: status={val_status}, confidence={val_conf:.2f}, doubts={len(doubts)}")

            # 【墙上的画→引擎】L4 doubts触发回复修正
            # 之前：doubts仅记录到attempts，不影响任何决策
            # 现在：严重doubts(置信度<0.5或存在critical质疑)触发修正推理
            _l4_critical_doubts = [d for d in _l4_doubts if isinstance(d, dict) and d.get("severity") == "critical"]
            _l4_major_doubts = [d for d in _l4_doubts if isinstance(d, dict) and d.get("severity") == "major"]
            if val_conf < 0.5 or len(_l4_critical_doubts) > 0:
                _l4_should_correct = True
                _doubt_descs = []
                for _d in (_l4_critical_doubts + _l4_major_doubts)[:3]:
                    if isinstance(_d, dict):
                        _doubt_descs.append(_d.get("description", str(_d))[:80])
                    else:
                        _doubt_descs.append(str(_d)[:80])
                yield _emit("step", {"phase": "L4认知校验", "status": "done",
                    "detail": f"⚠️ L4发现{len(_l4_critical_doubts)}个严重质疑，触发修正: {'; '.join(_doubt_descs)}"})
                logger.info(f"L4质疑触发修正: {len(_l4_critical_doubts)} critical, {len(_l4_major_doubts)} major, conf={val_conf:.2f}")

                # 将L4质疑注入到essence_issues，让自我验证阶段知道
                for _d in (_l4_critical_doubts + _l4_major_doubts)[:3]:
                    if isinstance(_d, dict):
                        _desc = _d.get("description", "")
                        if _desc and _desc not in essence_issues:
                            essence_issues.append(f"[L4质疑] {_desc}")
                essence_passed = False
                if val_conf < essence_confidence:
                    essence_confidence = val_conf

                # L4质疑触发修正推理：用Ollama重新生成
                if not essence_cross_validated:
                    _l4_model = await _get_available_ollama_model_async()
                    if _l4_model:
                        yield _emit("step", {"phase": "L4修正推理", "status": "running",
                            "detail": f"L4质疑触发修正，调用 {_l4_model} 重新推理..."})
                        _l4_correction_prompt = user_input
                        if truth_insights:
                            _l4_correction_prompt = f"{user_input}\n\n参考信息:\n{truth_insights[:500]}"
                        _l4_retry = await _fetch_ollama(_l4_correction_prompt, _l4_model, timeout=20, conversation_context=conversation_context)
                        if _l4_retry and _l4_retry.get("response") and len(_l4_retry["response"]) > len(final_response) * 0.5:
                            _l4_retry_score = _score_response(_l4_retry, user_input)
                            _l4_current_score = _score_response(best, user_input) if best else 0
                            if _l4_retry_score > _l4_current_score * 0.8:
                                final_response = _l4_retry["response"]
                                _save_to_experience_pool(user_input, final_response, success=True, intent_type="l4_correction", model_name=_l4_model)
                                attempts.append(("L4修正推理", True, f"修正成功(评分{_l4_retry_score:.0f})"))
                                yield _emit("step", {"phase": "L4修正推理", "status": "done", "detail": f"L4修正成功 ✅"})
                            else:
                                attempts.append(("L4修正推理", False, f"修正评分{_l4_retry_score:.0f}未显著优于原{_l4_current_score:.0f}"))
                                yield _emit("step", {"phase": "L4修正推理", "status": "done", "detail": "L4修正未显著改善"})
                        else:
                            yield _emit("step", {"phase": "L4修正推理", "status": "done", "detail": "L4修正未返回有效结果"})
                    else:
                        yield _emit("step", {"phase": "L4修正推理", "status": "done", "detail": "无可用模型"})
        except Exception as e:
            logger.debug(f"L4认知校验跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L4_validation")
    _sm = _get_self_model()
    if _sm and _cognitive_validation:
        _sm.record_cognitive_cycle(validation=_cognitive_validation)

    # ========== 阶段7：反思学习 + 基因微调 ==========
    yield _emit("step", {"phase": "反思学习", "status": "running", "detail": "从本次交互中学习，微调系统基因..."})

    # L5进化层(异步) + L6内省层：通过CognitivePlanner触发进化引擎和自我认知
    if cp and _cognitive_perception:
        try:
            _conv_id = f"conv_{int(time.time())}"
            cp._trigger_async_evolution(
                _conv_id, user_input,
                final_response or "", _cognitive_perception,
                _cognitive_validation
            )
            logger.debug("L5进化层已异步触发")
        except Exception as e:
            logger.debug(f"L5进化层触发跳过: {e}")

        # 【认知增强旁路 Phase 1】异步运行cp.process()做交叉验证
        # process()是CognitivePlanner的核心入口，完整L1-L6认知循环
        # 旁路结果用于信号补充，不影响主流程
        _cognitive_bypass_result = None
        if cp and final_response:
            try:
                _bypass_ctx = {"history": context.get("history", [])[:5]} if isinstance(context, dict) else {}
                loop = asyncio.get_running_loop()
                _cognitive_bypass_result = await asyncio.wait_for(
                    loop.run_in_executor(_fast_executor, lambda: cp.process(user_input, _bypass_ctx)),
                    timeout=15
                )
                if _cognitive_bypass_result and _cognitive_bypass_result.success:
                    _bp = _cognitive_bypass_result
                    _bp_perception = _bp.perception or {}
                    _bp_validation = _bp.validation or {}

                    if _bp_perception.get("urgency", 0) > 0.8 and _cognitive_perception.get("urgency", 0.5) <= 0.7:
                        logger.info(f"认知旁路: 检测到高紧迫度信号 urgency={_bp_perception['urgency']:.2f}（主管道未捕获）")

                    if _bp_validation.get("status") == "fail" and _cognitive_validation.get("status") != "fail":
                        logger.warning(f"认知旁路: 校验失败但主管道通过 confidence={_bp_validation.get('confidence', 0):.2f}")
                        attempts.append(("认知旁路校验", True, f"旁路发现校验问题(conf={_bp_validation.get('confidence', 0):.2f})"))

                    _bp_emotion = _bp_perception.get("emotion", "neutral")
                    if _bp_emotion != "neutral" and _cognitive_perception.get("emotion", "neutral") == "neutral":
                        logger.info(f"认知旁路: 捕获情绪信号 emotion={_bp_emotion}（主管道未捕获）")

                    logger.debug(f"认知旁路完成: success={_bp.success}, time={_bp.processing_time_ms:.0f}ms")
            except asyncio.TimeoutError:
                logger.debug("认知旁路超时(15秒)，跳过")
            except Exception as e:
                logger.debug(f"认知旁路异常: {e}")

        # 【墙上的画→引擎】进化岛结果反馈到技能库和基因池
        # 之前：L5进化结果仅停留在L5内部（_sync_to_layers只向state_collector报告）
        # 现在：将L5的基因值和技能写回到实际的gene_pool和skill_emergence
        try:
            if hasattr(cp, 'l5') and cp.l5:
                _l5_status = cp.l5.get_evolution_status()
                _l5_genes = _l5_status.get("genes", {})
                _l5_skills_count = _l5_status.get("skills_count", 0)

                if _l5_genes:
                    from core.task_queue import task_queue, gene_pool
                    _synced_genes = 0
                    for _gid, _ginfo in _l5_genes.items():
                        if isinstance(_ginfo, dict) and "value" in _ginfo:
                            try:
                                _old_val = gene_pool.get(_gid)
                                _new_val = _ginfo["value"]
                                _delta = _new_val - _old_val
                                if abs(_delta) > 0.001:
                                    gene_pool.mutate(_gid, _delta, trigger="l5_evolution_sync")
                                    _synced_genes += 1
                            except Exception:
                                pass
                    if _synced_genes > 0:
                        logger.info(f"L5→基因池同步: {_synced_genes}个基因已通过mutate()写入gene_pool")

                if _l5_skills_count > 0 and hasattr(cp.l5, 'skills'):
                    from core.skill_emergence import skill_emergence
                    _synced_skills = 0
                    for _skill in cp.l5.skills:
                        if isinstance(_skill, dict) and _skill.get("name"):
                            try:
                                skill_emergence._create_skill(
                                    skill_name=_skill["name"],
                                    skill_type=_skill.get("type", "evolved"),
                                    trigger=_skill.get("pattern", _skill.get("trigger", "")),
                                    solution_path=_skill.get("solution", str(_skill.get("name", "")))
                                )
                                _synced_skills += 1
                            except Exception:
                                pass
                    if _synced_skills > 0:
                        logger.info(f"L5→技能库同步: {_synced_skills}个技能已写入skill_emergence")
        except Exception as e:
            logger.debug(f"进化岛结果反馈跳过: {e}")
        try:
            _cognitive_introspection = cp._get_introspection()
            if _cognitive_introspection:
                logger.debug(f"L6内省层: 获取到内省报告")
            if _cognitive_bypass_result and _cognitive_bypass_result.introspection:
                if not _cognitive_introspection:
                    _cognitive_introspection = _cognitive_bypass_result.introspection
                else:
                    _cognitive_introspection.update(_cognitive_bypass_result.introspection)
                logger.debug("L6内省层: 旁路内省报告已融合")
        except Exception as e:
            logger.debug(f"L6内省层跳过: {e}")
        try:
            cp._save_memory(user_input, final_response or "", _cognitive_perception, _cognitive_validation)
            logger.debug("认知记忆已保存")
        except Exception as e:
            logger.debug(f"认知记忆保存跳过: {e}")
        try:
            cp._update_relationship(user_input, final_response or "", _cognitive_perception, _cognitive_validation)
            logger.debug("认知关系模型已更新")
        except Exception as e:
            logger.debug(f"认知关系模型更新跳过: {e}")
        try:
            cp._submit_signals(_cognitive_perception, _cognitive_validation)
            logger.debug("认知信号已提交")
        except Exception as e:
            logger.debug(f"认知信号提交跳过: {e}")
        _sm = _get_self_model()
        if _sm:
            try:
                _sm.record_cognitive_cycle(introspection=_cognitive_introspection if '_cognitive_introspection' in dir() else None)
                _sm.sync_from_cognitive_planner(cp)
                _sm.evaluate_and_act()
            except Exception as e:
                logger.debug(f"SelfModel同步跳过: {e}")

    try:
        reflection = await _run_sync(_reflect_and_learn, user_input, final_response, attempts, start_time, comparison if candidates else [], timeout=5, phase="反思学习")
    except asyncio.TimeoutError:
        logger.warning("反思学习超时(5秒)")
        reflection = "反思学习超时，跳过"
        yield _emit("step", {"phase": "反思学习", "status": "timeout", "detail": "反思学习超时，跳过"})
    except Exception as e:
        logger.debug(f"反思学习异常: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="reflection_learning")
        reflection = "反思学习异常，跳过"

    # 经验抽象：从具体经历中提炼可迁移模式（补全7步闭环"抽象"层）
    try:
        from core.cognition.experience_abstractor import ExperienceAbstractor
        _abstraction_steps = [{"action": a[0], "result_preview": str(a[2])[:100] if len(a) > 2 else "", "success": a[1]} for a in attempts]
        _abstraction_result = ExperienceAbstractor.abstract(
            user_query=user_input,
            intent_type=intent_type,
            steps=_abstraction_steps,
            final_success=any(a[1] for a in attempts),
            failure_reason=str(failed_steps[0][2])[:200] if failed_steps and len(failed_steps[0]) > 2 else "",
        )
        ExperienceAbstractor.settle_to_skill_db(_abstraction_result, user_input, intent_type)
        if _abstraction_result.get("key_insights"):
            reflection += f"; 🧬 抽象:{_abstraction_result['key_insights'][0][:60]}"
    except Exception as e:
        logger.debug(f"经验抽象跳过: {e}")

    # 基因微调：从交互中学习（反脆弱性：失败也触发学习）
    try:
        from core.task_queue import task_queue, gene_pool
        task_queue.notify_user_interaction()
        overall_success = any(a[1] for a in attempts)
        failed_steps = [a for a in attempts if not a[1]]
        gene_pool.learn_from_interaction(
            elapsed=time.time() - start_time,
            success=overall_success,
            model_used=best.get("source", "") if best else ""
        )
        if failed_steps and overall_success:
            gene_pool.mutate("caution_threshold", 0.02, "partial_failure")
            gene_pool.mutate("self_doubt_frequency", 0.01, "partial_failure")
            reflection += f"; 🧬 基因已微调(部分失败: {len(failed_steps)}步)"
        else:
            reflection += "; 🧬 基因已微调"
    except Exception as e:
        logger.debug(f"基因微调异常: {e}")

    # 【墙上的画→引擎】错误炼金：从失败步骤中提炼学习信号
    # 之前：ErrorAlchemy从未被chat_orchestrator调用，错误信息仅记录到日志
    # 现在：将失败步骤交给ErrorAlchemy处理，提取avoid_pattern和retry_strategy
    _error_alchemy_signals = []
    try:
        from core.learning.error_alchemy import ErrorAlchemy
        _alchemy = ErrorAlchemy()
        _failed_steps = [a for a in attempts if not a[1]]
        for _step_name, _step_success, _step_detail in _failed_steps[:5]:
            _fake_err = Exception(f"Step '{_step_name}' failed: {_step_detail}")
            _err_id = _alchemy.record_error(_fake_err, context={
                "user_input": user_input[:100],
                "step": _step_name,
                "detail": _step_detail[:200],
                "intent_type": intent_type,
            })
            _result = _alchemy.alchemize(_err_id)
            if _result.gold_extracted:
                _error_alchemy_signals.extend(_result.patterns_found)
                logger.info(f"错误炼金: 从'{_step_name}'中提炼出{len(_result.patterns_found)}个学习信号")
        if _error_alchemy_signals:
            reflection += f"; 🔮 错误炼金提取{len(_error_alchemy_signals)}个信号({','.join(_error_alchemy_signals[:3])})"
    except Exception as e:
        logger.debug(f"错误炼金跳过: {e}")

    # 【墙上的画→引擎】元学习：优化学习策略本身
    # 审计报告要求：推荐策略应指导learn_from_interaction逻辑，而非仅记录推荐
    _meta_learning_strategy = None
    try:
        from core.learning.meta_learning import MetaLearner, EvaluationMetric
        _meta = MetaLearner()
        _meta_context = {
            "task_type": intent_type,
            "recent_accuracy": sum(1 for a in attempts if a[1]) / max(len(attempts), 1),
            "complexity": len(user_input) / 100,
        }
        _recommendations = _meta.recommend_strategy(_meta_context)
        if _recommendations:
            _top_rec = _recommendations[0]
            _meta_learning_strategy = _top_rec.strategy
            logger.info(f"元学习推荐: {_top_rec.strategy.name} (置信度{_top_rec.confidence:.2f}, 原因:{_top_rec.reason})")
            for _rec in _recommendations[:2]:
                _perf_score = 0.7 if overall_success else 0.3
                _meta.evaluate_strategy(
                    _rec.strategy.strategy_id,
                    EvaluationMetric.ACCURACY,
                    _perf_score,
                    context=_meta_context
                )
            reflection += f"; 📚 元学习推荐:{_recommendations[0].strategy.name}"
    except Exception as e:
        logger.debug(f"元学习跳过: {e}")

    # 元学习策略指导基因微调：不同策略→不同学习率
    if _meta_learning_strategy:
        try:
            from core.task_queue import gene_pool
            _s_type = _meta_learning_strategy.type.value if hasattr(_meta_learning_strategy.type, 'value') else str(_meta_learning_strategy.type)
            _s_params = _meta_learning_strategy.parameters if hasattr(_meta_learning_strategy, 'parameters') else {}
            if _s_type == "memorization":
                gene_pool.mutate("learning_rate", 0.02, trigger="meta_memorization")
            elif _s_type == "understanding":
                gene_pool.mutate("depth_preference", 0.02, trigger="meta_understanding")
                gene_pool.mutate("learning_rate", -0.01, trigger="meta_understanding")
            elif _s_type == "application":
                gene_pool.mutate("retry_aggression", 0.02, trigger="meta_application")
            elif _s_type == "evaluation":
                gene_pool.mutate("self_doubt_frequency", 0.02, trigger="meta_evaluation")
            logger.debug(f"元学习策略指导基因微调: {_s_type}")
        except Exception as e:
            logger.debug(f"元学习策略微调跳过: {e}")

    # Agent协作触发：复杂查询且质量不达标时，启动多Agent闭环
    if intent_type in ("complex_query", "code") and isinstance(fitness_score, (int, float)) and fitness_score < 50:
        try:
            from core.agents.coordinator import agent_coordinator
            agent_result = await asyncio.wait_for(
                agent_coordinator.collaborate(user_input, context={"attempts": [a[0] for a in attempts]}),
                timeout=60,
            )
            if agent_result.get("quality", 0) > fitness_score * 100:
                final_response = agent_result.get("response", final_response)
                reflection += f"; Agent协作提升(迭代{agent_result.get('iterations', 0)}次,质量{agent_result.get('quality', 0):.0f})"
                yield _emit("step", {"phase": "Agent协作", "status": "done", "detail": f"多Agent闭环完成,质量提升至{agent_result.get('quality', 0):.0f}"})
        except asyncio.TimeoutError:
            logger.debug("Agent协作超时,跳过")
        except Exception as e:
            logger.debug(f"Agent协作异常: {e}")

    # 双速进化快循环：秒级经验积累 + 痛点信号收集
    try:
        from infrastructure.dual_speed_evolution import dual_speed_evolution
        fitness_val = fitness_score if isinstance(fitness_score, (int, float)) else 0.0
        dual_speed_evolution.run_fast_loop(
            question=user_input, response=final_response,
            fitness_score=fitness_val, intent_type=intent_type,
        )
    except Exception as e:
        logger.debug(f"双速进化快循环异常: {e}")

    # 路径权重批量更新（AdaBoost快循环）：根据attempts结果更新各路径权重
    try:
        from core.path_weight_manager import path_weight_manager
        for src, success, detail in attempts:
            path_name = src
            if path_name in path_weight_manager._paths:
                conf = 0.5
                if "置信度" in detail:
                    try:
                        conf = float(detail.split("置信度")[-1].split("%")[0]) / 100
                    except (ValueError, IndexError):
                        pass
                path_weight_manager.update_weight(path_name, success, conf)
    except Exception as e:
        logger.debug(f"路径权重批量更新跳过: {e}")

    # 知识固化：高质量回复升级为知识
    try:
        gene_result = await _run_sync(_try_solidify_to_gene_pool, user_input, final_response, attempts, comparison, timeout=10, phase="基因固化")
        if gene_result:
            reflection += f"; {gene_result}"
    except Exception as e:
        logger.debug(f"知识固化异常: {e}")

    # 事实提取：高质量回复自动提取三元组存入事实库
    try:
        from infrastructure.fact_store import fact_store
        overall_success = any(a[1] for a in attempts)
        if overall_success and final_response and len(final_response) > 50:
            fact_count = await _run_sync(fact_store.extract_and_store, user_input, final_response, source="chat_auto", timeout=10, phase="事实提取")
            if fact_count > 0:
                reflection += f"; 📚 事实提取{fact_count}条三元组"
    except Exception as e:
        logger.debug(f"事实提取异常: {e}")

    # 反思管道：异步触发深度反思（不阻塞响应）
    try:
        from infrastructure.reflection_pipeline import get_reflection_pipeline
        pipeline = get_reflection_pipeline()
        if pipeline:
            execution_context = {
                "query": user_input,
                "plan": str(essence_gate_result) if essence_gate_result else "",
                "tool_calls": tool_calls_log if 'tool_calls_log' in dir() else [],
                "final_answer": final_response,
                "confidence": confidence,
                "model_used": best.get("source", "") if best else "",
                "duration_ms": int((time.time() - start_time) * 1000),
                "extra": {"intent": intent_type, "attempts": [(a[0], a[1]) for a in attempts]}
            }
            asyncio.create_task(pipeline.process(execution_context))
    except Exception as e:
        logger.debug(f"反思管道触发跳过: {e}")

    # SelfReflection联动：从精神内核获取教训，注入反思学习
    try:
        if SPIRIT_CORE_AVAILABLE:
            from core.spirit_core import spirit_core as _spirit_core_reflect
            failed_steps = [a for a in attempts if not a[1]]
            if failed_steps:
                lessons = _spirit_core_reflect.get_lessons_for_reflection()
                if lessons:
                    lesson_summary = str(lessons)[:200]
                    reflection += f"; 精神教训: {lesson_summary}"
            violations = _spirit_core_reflect.get_violations_for_analysis()
            if violations:
                reflection += f"; 违规记录: {len(violations)}条"
    except Exception as e:
        logger.debug(f"精神内核联动跳过: {e}")

    # ========== 先发射最终响应（确保前端立即收到，不再被后续处理阻塞） ==========
    elapsed = time.time() - start_time

    if not final_response:
        try:
            ollama_result = await _fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights="")
            if ollama_result and ollama_result.get("response") and len(ollama_result["response"]) > 20:
                final_response = ollama_result["response"]
                attempts.append(("终极保护-动态", True, "模型实时生成"))
            else:
                attempts.append(("终极保护-动态", False, "模型无有效回复"))
        except Exception as _e:
            logger.warning(f"终极保护-动态推理异常: {_e}")
            attempts.append(("终极保护-动态", False, f"模型异常: {str(_e)[:40]}"))

        if not final_response:
            try:
                from backend.services.persistent_solver import persistent_solve, review_solution
                _ps_events2 = []
                async def _ps_emit2(event_type, data):
                    _ps_events2.append((event_type, data))

                yield _emit("step", {"phase": "终极持续求解", "status": "running", "detail": "终极保护启动持续求解引擎..."})
                ps_resp2, ps_attempts2, ps_solved2 = await persistent_solve(
                    user_input, attempts,
                    conversation_context=conversation_context,
                    truth_insights="",
                    emit_fn=_ps_emit2,
                )
                for _et2, _ed2 in _ps_events2:
                    yield _emit(_et2, _ed2)
                attempts.extend(ps_attempts2)
                if ps_solved2 and ps_resp2:
                    final_response = ps_resp2
                    attempts.append(("终极持续求解", True, f"成功"))
                    await review_solution(user_input, ps_resp2, attempts, True)
                else:
                    final_response = ps_resp2 or _never_give_up_response(user_input, attempts)
                    attempts.append(("终极持续求解", False, "未解决"))
            except Exception as _pse2:
                logger.warning(f"终极持续求解异常: {_pse2}")
                final_response = _never_give_up_response(user_input, attempts)
                attempts.append(("终极持续求解", False, f"异常: {str(_pse2)[:40]}"))

    _save_to_experience_pool(
        user_input, final_response,
        success=any(a[1] for a in attempts),
        intent_type=intent_type,
        quality_score=int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40),
        duration=elapsed,
        model_name=best.get("source", "unknown") if best else "unknown"
    )

    # 轨迹进化：将完整解决路径存入轨迹库
    try:
        from core.trajectory_evolution import trajectory_store
        traj_steps = []
        for a in attempts:
            traj_steps.append({
                "phase": a[0] if len(a) > 0 else "",
                "success": a[1] if len(a) > 1 else False,
                "detail": a[2] if len(a) > 2 else "",
                "duration_ms": 0
            })
        traj_decisions = []
        if route == "slow" and candidates:
            best_src = comparison[0]["source"] if comparison else ""
            traj_decisions.append({"type": "path_selection", "chosen": best_src, "reason": "highest_score"})
        if 'path_percentages' in dir() and path_percentages:
            traj_decisions.append({"type": "path_contribution", "distribution": path_percentages})
        traj_outcome = {
            "quality_score": int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40),
            "confidence": confidence,
            "duration": elapsed,
            "response_length": len(final_response) if final_response else 0,
            "success": any(a[1] for a in attempts)
        }
        traj_fitness = trajectory_store.evaluate_trajectory(traj_steps, traj_outcome)
        trajectory_store.store_trajectory(
            query=user_input,
            steps=traj_steps,
            decisions=traj_decisions,
            outcome=traj_outcome,
            intent_type=intent_type,
            route=route,
            fitness_score=traj_fitness,
            duration=elapsed,
            source="live"
        )
    except Exception as e:
        logger.debug(f"轨迹存储跳过: {e}")

    token_summary = {}
    for c in candidates:
        if isinstance(c, dict) and "tokens" in c:
            src = c.get("source", "未知")
            tk = c["tokens"]
            if tk.get("total_tokens", 0) > 0:
                token_summary[src] = tk

    try:
        from core.alignment_guard import get_alignment_guard
        guard = get_alignment_guard()
        guard.check_response_alignment(user_input, final_response or "", "chat_stream")
    except Exception:
        pass

    # CBNR L3: 认知残差 — 经验复用+增量学习+状态更新 (移至result前确保L3数据包含在响应中)
    try:
        from core.cbnr.hub import get_cbnr_hub
        _cbnr_hub = get_cbnr_hub()
        _l2_output = {
            "topic": cbnr_context.get("l2_topic", ""),
            "entities": cbnr_context.get("l2_entities", []),
            "causal_chain": cbnr_context.get("l2_causal_chain", []),
            "counterfactuals": cbnr_context.get("l2_counterfactuals", []),
            "resolution_mode": cbnr_context.get("l2_conflict_mode", "unknown"),
        }
        _l3_result = _cbnr_hub.process_l3(_l1_normalized, _l2_output)
        cbnr_context["l3_reuse_rate"] = _l3_result.state_reuse_rate
        cbnr_context["l3_search_tree_size"] = _l3_result.search_tree_size
        cbnr_context["l3_fallback_used"] = _l3_result.fallback_used
        cbnr_context["l3_has_experience_base"] = _l3_result.new_state.get("_has_experience_base", False)
        logger.debug(f"CBNR L3: 复用率={_l3_result.state_reuse_rate:.1%}, 搜索树={_l3_result.search_tree_size}")
        try:
            _cbnr_hub.finalize_distributed()
        except Exception:
            pass
    except Exception as e:
        logger.debug(f"CBNR L3跳过: {e}")

    if final_response and len(final_response) > _MAX_RESPONSE_CHARS:
        logger.warning(f"响应过长({len(final_response)}字符)，截断至{_MAX_RESPONSE_CHARS}(GPU过热保护)")
        final_response = final_response[:_MAX_RESPONSE_CHARS] + "\n\n[回复已截断以保护GPU，避免过热断电]"

    companion_layers = {}
    try:
        if SPIRIT_CORE_AVAILABLE and final_response:
            from core.spirit_core import spirit_core as _spirit_core
            validation = _spirit_core.validate_response(final_response, context={"query": user_input, "content_understanding": content_understanding if 'content_understanding' in dir() else {}})
            companion_layers = {
                "L1_paradigm_match": validation.get("checks", {}).get("meaningful", False),
                "L2_boundary_awareness": validation.get("checks", {}).get("pursue_essence", False),
                "L3_silence_allowed": validation.get("checks", {}).get("state_sync", False),
                "L4_success_archive": validation.get("checks", {}).get("failure_direction", False),
                "L5_self_alignment": validation.get("checks", {}).get("honest_when_lost", False),
                "spirit_score": validation.get("score", 0),
            }
    except Exception:
        pass

    # ========== 目标达成检查：半成品不输出，继续求解 ==========
    if final_response and not _is_goal_achieved(user_input, final_response, intent_type, attempts):
        logger.info(f"🔄 目标未达成检测: 回复是半成品，启动持续求解...")
        yield _emit("step", {"phase": "目标达成检查", "status": "running", "detail": "检测到回复未真正解决问题，启动持续求解..."})
        try:
            from backend.services.persistent_solver import persistent_solve, review_solution
            _ps_events3 = []
            async def _ps_emit3(event_type, data):
                _ps_events3.append((event_type, data))

            ps_resp3, ps_attempts3, ps_solved3 = await persistent_solve(
                user_input, attempts,
                conversation_context=conversation_context,
                truth_insights=truth_insights if 'truth_insights' in dir() else "",
                emit_fn=_ps_emit3,
            )
            for _et3, _ed3 in _ps_events3:
                yield _emit(_et3, _ed3)
            attempts.extend(ps_attempts3)
            if ps_solved3 and ps_resp3:
                final_response = ps_resp3
                attempts.append(("目标达成求解", True, "持续求解成功"))
                await review_solution(user_input, ps_resp3, attempts, True)
                yield _emit("step", {"phase": "目标达成检查", "status": "done", "detail": "✅ 持续求解成功，目标达成"})
            else:
                ps_fallback = ps_resp3 or final_response
                final_response = ps_fallback
                attempts.append(("目标达成求解", False, "持续求解未完全解决"))
                yield _emit("step", {"phase": "目标达成检查", "status": "done", "detail": "⚠️ 持续求解后仍需人工介入"})
        except Exception as _pse3:
            logger.warning(f"目标达成求解异常: {_pse3}")
            attempts.append(("目标达成求解", False, f"异常: {str(_pse3)[:40]}"))

    yield _emit("result", {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "elapsed": round(elapsed, 1),
        "spirit_compliant": SPIRIT_CORE_AVAILABLE,
        "candidates": comparison if candidates else [],
        "path_contributions": path_percentages if 'path_percentages' in dir() else {},
        "token_usage": token_summary,
        "cbnr": cbnr_context if 'cbnr_context' in dir() else {},
        "session_id": _chat_session_id or "",
        "companion_layers": companion_layers,
        "cognitive_layers": {
            "L1_perception": {k: v for k, v in _cognitive_perception.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if '_cognitive_perception' in dir() and isinstance(_cognitive_perception, dict) else {},
            "L2_learning": {k: v for k, v in _cognitive_learning.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if '_cognitive_learning' in dir() and isinstance(_cognitive_learning, dict) else {},
            "L3_integration": {k: v for k, v in _cognitive_integration.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if '_cognitive_integration' in dir() and isinstance(_cognitive_integration, dict) else {},
            "L4_validation": {k: v for k, v in _cognitive_validation.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if '_cognitive_validation' in dir() and isinstance(_cognitive_validation, dict) else {},
            "L5_evolution_triggered": cp is not None and '_cognitive_perception' in dir(),
            "L6_introspection": str(_cognitive_introspection)[:500] if '_cognitive_introspection' in dir() and _cognitive_introspection else {},
        } if cp else {},
    })

    logger.info(f"✅ 响应已发送({elapsed:.1f}秒)，后续后台学习继续...")

    try:
        from infrastructure.hardware_monitor import set_ollama_cooldown
        set_ollama_cooldown(3.0)
    except Exception:
        pass

    if _chat_session_id and final_response:
        try:
            from infrastructure.chat_history import get_chat_history
            _ch = get_chat_history()
            _cbnr_sum = ""
            try:
                if cbnr_context:
                    _cbnr_sum = json.dumps(cbnr_context, ensure_ascii=False)[:500]
            except Exception:
                pass
            _ch.add_message(
                _chat_session_id, "assistant", final_response,
                intent=intent_type, route=route, confidence=confidence,
                elapsed=round(elapsed, 1), cbnr_summary=_cbnr_sum
            )
        except Exception as e:
            logger.debug(f"对话历史写入assistant跳过: {e}")

    try:
        from infrastructure.ratchet_gate import guard_change
        resp_quality = confidence if fitness_score is None else fitness_score.final_score / 100.0
        guard_change("chat_response", resp_quality, f"chat: {user_input[:40]} intent={intent_type} route={route}")
    except Exception:
        pass

    try:
        from core.perception_snapshot import update_action_trace
        belief_summary = final_response[:80] if final_response else ""
        update_action_trace(
            action=f"responded:{intent_type}",
            belief=belief_summary,
            intent=intent_type,
            confidence=confidence,
            route=route,
        )
    except Exception:
        pass

    # P1-1: 发布KnowledgeUpdate和ModelStatusChange事件
    try:
        from infrastructure.event_bus import bus, EventTypes
        if fitness_score and fitness_score.final_score > 0:
            bus.publish(EventTypes.KnowledgeUpdate, {
                "query": user_input[:100],
                "quality": fitness_score.final_score,
                "source": best.get("source", "") if best else "",
                "timestamp": time.time(),
            })
        model_src = best.get("source", "") if best else ""
        if model_src:
            bus.publish(EventTypes.ModelStatusChange, {
                "model": model_src,
                "status": "responded",
                "quality": best.get("quality", 0) if isinstance(best, dict) else 0,
                "timestamp": time.time(),
            })
    except Exception:
        pass

    # ========== 以下全部为后台fire-and-forget任务，不阻塞SSE流 ==========

    # 知识缺失检测 + 自动学习进化（fire-and-forget后台任务，绝不阻塞响应）
    try:
        from core.knowledge_gap_detector import gap_detector
        has_gap, reason, issues = gap_detector.detect_knowledge_gap(
            user_input, final_response, confidence=confidence
        )
        if has_gap:
            yield _emit("step", {"phase": "反思学习", "status": "running", "detail": f"检测到知识缺失({reason})，后台学习中..."})

            async def _bg_auto_evolution():
                try:
                    from core.auto_learning_evolution import auto_evolution
                    evolution_result = await asyncio.get_running_loop().run_in_executor(
                        _slow_executor,
                        lambda: auto_evolution.process_query_with_evolution(
                            user_input, final_response, confidence=confidence
                        )
                    )
                    if evolution_result and evolution_result.get('corrected'):
                        logger.info(f"🧬 自动学习进化修正: {reason}")
                    logger.info("🧬 后台自动学习进化完成")
                except Exception as e:
                    logger.warning(f"后台自动学习进化异常: {e}")

            asyncio.create_task(_bg_auto_evolution())
            yield _emit("step", {"phase": "反思学习", "status": "done", "detail": "后台学习中..."})
    except Exception as e:
        logger.debug(f"自动学习进化跳过: {e}")

    # 自适应进化目标：从交互中推断进化方向
    try:
        from core.evolution.adaptive_goal import get_adaptive_evolution_goal
        agm = get_adaptive_evolution_goal()
        agm.infer_value_from_feedback({
            "type": "interaction",
            "query": user_input[:200],
            "value": fitness_score.final_score / 100.0 if fitness_score else 0.5,
            "success": any(a[1] for a in attempts),
        })
    except Exception as e:
        logger.debug(f"自适应进化目标跳过: {e}")

    # 注入验证：验证知识注入/事实提取/知识固化的实际效果
    try:
        from infrastructure.injection_verifier import injection_verifier
        injected_items = []
        if gene_result:
            injected_items.append({"type": "gene_solidification", "confidence": 0.9})
        if fact_count if 'fact_count' in dir() else 0:
            injected_items.append({"type": "fact_extraction", "confidence": 0.7, "count": fact_count if 'fact_count' in dir() else 0})
        if has_gap if 'has_gap' in dir() else False:
            injected_items.append({"type": "auto_evolution", "confidence": 0.6})
        
        if injected_items:
            before_score = best.get("quality", 50) if best else 30
            verification = injection_verifier.verify_injection(
                injection_id=f"chat_{int(time.time())}",
                question=user_input,
                before_score=float(before_score),
                injected_knowledge=injected_items
            )
            if not verification.passed:
                reflection += f"; ⚠️ 注入验证未通过(改进{verification.improvement:.1f}分)"
            else:
                reflection += f"; ✅ 注入验证通过(改进{verification.improvement:.1f}分)"
    except Exception as e:
        logger.debug(f"注入验证跳过: {e}")

    yield _emit("step", {"phase": "反思学习", "status": "done", "detail": reflection})


    # 立体记忆存储：将本次交互存入立体记忆系统
    try:
        from core.memory.stereo_memory import get_stereo_memory, MemoryType, MemoryImportance, SelfDimension, MemoryContext
        sm = get_stereo_memory()
        
        overall_success = any(a[1] for a in attempts)
        importance = MemoryImportance.HIGH if overall_success and confidence >= 0.7 else MemoryImportance.MEDIUM
        
        emotional_state = "confident" if overall_success and confidence >= 0.8 else "uncertain" if not overall_success else "neutral"
        
        sm_store_coro = _run_sync(
            lambda: sm.store(
                content={"query": user_input[:200], "response": final_response[:300]},
                memory_type=MemoryType.CONVERSATION,
                importance=importance,
                related_entities=set([w for w in user_input.split() if len(w) >= 2][:5]),
                self_dimension=SelfDimension(
                    role="assistant",
                    confidence=confidence,
                    emotional_state=emotional_state,
                    learning_progress=0.0,
                ),
                context=MemoryContext(
                    user_id=context.get("user_id", "default") if context else "default",
                    trigger="user_query",
                    related_concepts=[intent_type],
                ),
            ),
            timeout=5
        )
        asyncio.ensure_future(sm_store_coro)
    except Exception as e:
        logger.debug(f"立体记忆存储跳过: {e}")

    # 关系模型更新：记录本次互动，演化信任度
    try:
        from core.relationship.model import get_relationship_model, InteractionType
        rm = get_relationship_model()
        
        interaction_type = InteractionType.CONVERSATION
        if intent_type == "challenge":
            interaction_type = InteractionType.CORRECTION
        elif intent_type in ["question", "factual", "verification"]:
            interaction_type = InteractionType.QUESTION
        elif intent_type == "greeting":
            interaction_type = InteractionType.CONVERSATION
        
        satisfaction = 0.7 if any(a[1] for a in attempts) else 0.3
        if fitness_score:
            satisfaction = fitness_score.final_score / 100.0
        
        rm_record_coro = _run_sync(
            lambda: rm.record_interaction(
                user_input=user_input[:200],
                system_response=final_response[:300],
                interaction_type=interaction_type,
                user_satisfaction=satisfaction,
                context={"intent": intent_type, "confidence": confidence},
            ),
            timeout=5
        )
        asyncio.ensure_future(rm_record_coro)
    except Exception as e:
        logger.debug(f"关系模型更新跳过: {e}")

    # 存在层信号：将交互结果发送给存在层
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el.receive_signal({
            "type": "interaction_completed",
            "query": user_input[:100],
            "success": any(a[1] for a in attempts),
            "confidence": confidence,
            "intent": intent_type,
            "fitness": fitness_score.final_score if fitness_score else None,
        })
    except Exception:
        pass

    # ========== 阶段8：后台持续进化（认知时差：延迟启动） ==========
    try:
        from core.task_queue import task_queue
        # 认知时差：深度思考延迟15秒启动，让系统先"喘口气"
        task_queue.enqueue("deep_thinking", {"query": user_input, "context": context}, priority=3, delay_seconds=15)
        if best and best.get("source", "").startswith("Ollama"):
            task_queue.enqueue("model_review", {"query": user_input, "response": final_response}, priority=7, delay_seconds=5)
        # 认知代谢：每10次交互触发一次排毒（低优先级，空闲时执行）
        try:
            db = DatabaseManager.get("data/experience_pool.db")
            row = db.query_one("SELECT COUNT(*) FROM experiences")
            exp_count = row[0] if row else 0
            if exp_count > 0 and exp_count % 10 == 0:
                task_queue.enqueue("cognitive_metabolism", {}, priority=9, delay_seconds=60)
            if exp_count > 0 and exp_count % 50 == 0:
                task_queue.enqueue("stress_test", {}, priority=9, delay_seconds=120)
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"任务入队失败，降级为内存任务: {e}")
        asyncio.create_task(_background_deep_thinking(user_input, context, intent_type))

    elapsed_bg = time.time() - start_time
    logger.info(f"✅ 完整闭环(后台): {user_input[:30]} → {[(a[0], a[1]) for a in attempts]} (总耗时{elapsed_bg:.1f}秒，响应已提前发送)")


async def _background_deep_thinking(query: str, context: dict, intent_type: str):
    try:
        logger.info(f"🧠 后台深度思考: {query[:30]}...")
        from core.metacognitive_executor import MetacognitiveExecutor
        executor = MetacognitiveExecutor()
        exec_result = await executor.execute_with_full_metacognition(user_query=query, context=context)
        result = exec_result.get("final_result", "")
        if result and len(result) > 20:
            _save_to_experience_pool(query, result, success=True, intent_type="background_thinking", model_name="ollama")
            logger.info(f"✅ 后台思考完成: {len(result)}字")
    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


async def _solve_history_query(query: str) -> str:
    try:
        db = DatabaseManager.get("data/experience_pool.db")
        rows = db.query("SELECT raw_input, response FROM experiences ORDER BY timestamp DESC LIMIT 10")
        if rows:
            history_text = "\n".join([f"- {r[0][:30]}... → {r[1][:50]}..." for r in rows[:5]])
            return f"📜 最近的历史记录：\n{history_text}\n\n（完整历史功能开发中）"
        else:
            return "暂无历史记录。开始和我对话吧！"
    except Exception:
        return "历史记录功能正在初始化，请稍后再试。"


def _generate_smart_reply(query: str, intent_type: str) -> str:
    return "__NEED_DYNAMIC_REPLY__"


def _generate_meaningful_fallback(query: str, attempts: list) -> str:
    return "__NEED_DYNAMIC_FALLBACK__"


def _never_give_up_response(user_input: str, attempts: list) -> str:
    try:
        from core.spirit_core import spirit_core
        attempt_dicts = []
        for a in attempts:
            if isinstance(a, tuple) and len(a) >= 2:
                attempt_dicts.append({"method": a[0], "success": a[1], "error": a[2] if len(a) > 2 else ""})
            elif isinstance(a, dict):
                attempt_dicts.append(a)
        return spirit_core.ensure_meaningful_response(user_input, attempt_dicts)
    except Exception:
        failed_names = [a[0] for a in attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
        if failed_names:
            return f"我尝试了{len(attempts)}种方法（{', '.join(failed_names[:4])}均未成功），但我不打算放弃。此问题已记入学习清单，我会持续思考。你可以换个方式提问或提供更多背景，我们一起解决。"
        return f"关于「{user_input[:30]}」，我暂时还没找到最佳答案，但我在持续思考。换个角度试试？"


def _is_goal_achieved(user_input: str, response: str, intent_type: str, attempts: list) -> bool:
    """
    目标达成检查：回复是否真正解决了用户的问题？
    
    核心逻辑：
    - 操作类问题（串口/硬件/命令/文件）→ 必须有实际执行结果，不能只是"你可以这样做..."
    - 知识类问题 → 回复必须有实质内容，不能是"我不确定"
    - 任何"无法/不能/没有能力"的回复 → 未达成
    - 只有文本指导没有执行结果的操作类 → 未达成
    """
    if not response or len(response) < 15:
        return False

    resp_lower = response.lower()
    user_lower = user_input.lower()

    is_operational = any(kw in user_lower for kw in [
        "读取", "获取", "执行", "运行", "访问", "打开", "写入", "发送",
        "串口", "com", "serial", "硬件", "设备", "端口", "命令", "cmd",
        "bash", "shell", "powershell", "安装", "部署", "启动", "停止",
        "gps", "nmea", "传感器", "扫描", "检测",
    ])

    if is_operational:
        code_block_count = resp_lower.count("```")
        has_real_data = any(kw in resp_lower for kw in [
            "$gpgga", "$gprmc", "$gpgsv", "nmea",
            "com8", "serial", "波特率", "baud",
            "成功打开", "读取到", "执行结果", "返回值",
            "pid", "进程", "exit code",
        ])
        is_just_instructions = (
            "你可以" in response or "你可以使用" in response or "你可以尝试" in response
            or "以下是" in response or "步骤如下" in response
            or "具体步骤" in response or "需要安装" in response
        ) and not has_real_data

        if is_just_instructions and code_block_count > 0 and not has_real_data:
            logger.info(f"🔄 目标未达成: 操作类问题只给了指导文本，没有实际执行结果")
            return False

    evasion_patterns = [
        "我无法访问", "我无法直接", "我不能访问", "我没有能力",
        "我无法连接", "我无法执行", "我无法获取", "我无法读取",
        "无法直接访问", "无法直接操作", "无法直接执行",
        "作为ai", "作为一个ai", "作为语言模型",
        "我建议你", "你可以自己", "你需要手动",
    ]
    for pattern in evasion_patterns:
        if pattern in resp_lower:
            logger.info(f"🔄 目标未达成: 回复包含敷衍模式'{pattern}'")
            return False

    if is_operational:
        fabricated_patterns = [
            "sensor data:", "sensor id:", "[device:main]",
            "temperature:", "humidity:", "pressure:",
        ]
        real_data_markers = ["$gpgga", "$gprmc", "$gngga", "$gnrmc", "nmea", "com8", "波特率", "serial_port"]
        has_fabricated = any(p in resp_lower for p in fabricated_patterns)
        has_real = any(p in resp_lower for p in real_data_markers)
        if has_fabricated and not has_real:
            logger.info(f"🔄 目标未达成: 检测到LLM伪造的硬件数据，非真实读取结果")
            return False

    if is_operational:
        has_execution = any(a[1] for a in attempts if isinstance(a, tuple) and len(a) >= 2
                          and any(kw in str(a[0]).lower() for kw in ["工具", "串口", "bash", "serial", "执行"]))
        if not has_execution and code_block_count == 0:
            tool_attempted = any("工具" in str(a[0]) for a in attempts if isinstance(a, tuple) and len(a) >= 1)
            if not tool_attempted:
                logger.info(f"🔄 目标未达成: 操作类问题没有尝试工具执行")
                return False

        best_source = ""
        for a in attempts:
            if isinstance(a, tuple) and len(a) >= 2 and a[1]:
                best_source = str(a[0])
                break
        if best_source == "自我推理":
            logger.info(f"🔄 目标未达成: 操作类问题最优来源是自我推理而非工具执行")
            return False

        has_real_data = any(kw in resp_lower for kw in [
            "$gpgga", "$gprmc", "$gpgsv", "nmea",
            "com8", "serial", "波特率", "baud",
            "成功打开", "读取到", "执行结果", "返回值",
            "pid", "进程", "exit code", "stdout", "stderr", "output",
        ])
        if not has_real_data and not code_block_count:
            logger.info(f"🔄 目标未达成: 操作类问题回复不含任何实际执行数据")
            return False

    return True


def _perceive_continuity(user_input: str, history: list) -> dict:
    """
    对话连续性感知——从PheromoneField方案提取的核心价值。
    检测：1)话题漂移 2)上下文衰减 3)指代消解需求
    返回信号字典，注入methodology影响后续推理策略。
    """
    signal = {
        "topic_drift": False,
        "drift_distance": 0.0,
        "drift_direction": "",
        "reference_needs_resolution": False,
        "reference_text": "",
        "context_decay": False,
        "activity_level": 1.0,
        "previous_topics": [],
        "continuity_hint": "",
    }

    if not history or len(history) < 2:
        return signal

    recent_user_msgs = []
    for msg in history[-10:]:
        if msg.get("role") == "user" and msg.get("content"):
            recent_user_msgs.append(msg["content"])

    if not recent_user_msgs:
        return signal

    last_user_msg = recent_user_msgs[-1]

    domain_keywords = {
        "hardware": ["串口", "com", "端口", "传感器", "gps", "nmea", "串口", "波特率", "arduino", "esp32", "电压", "电流", "引脚"],
        "code": ["代码", "函数", "编程", "算法", "python", "实现", "调试", "编译", "运行"],
        "science": ["为什么", "原理", "物理", "化学", "天文", "生物", "数学", "机制", "本质"],
        "philosophy": ["意义", "命运", "哲学", "悖论", "存在", "意识"],
        "daily": ["你好", "谢谢", "再见", "怎么样", "今天"],
    }

    def _detect_domain(text: str) -> str:
        text_lower = text.lower()
        best_domain = "unknown"
        best_count = 0
        for domain, keywords in domain_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_domain = domain
        return best_domain if best_count > 0 else "unknown"

    current_domain = _detect_domain(user_input)
    previous_domains = [_detect_domain(msg) for msg in recent_user_msgs[-5:]]
    signal["previous_topics"] = previous_domains

    if previous_domains and current_domain != "unknown":
        last_domain = previous_domains[-1] if previous_domains else "unknown"
        if last_domain != "unknown" and current_domain != last_domain:
            signal["topic_drift"] = True
            signal["drift_direction"] = f"{last_domain}→{current_domain}"
            domain_distance = 1.0 if {last_domain, current_domain} in [
                {"hardware", "code"}, {"science", "philosophy"}
            ] else 0.5
            signal["drift_distance"] = domain_distance
            signal["continuity_hint"] = f"话题从{last_domain}跳转到{current_domain}"

    reference_patterns = ["它", "这个", "那个", "上面说的", "刚才的", "之前的", "他", "她"]
    for ref in reference_patterns:
        if ref in user_input and len(user_input) < 30:
            signal["reference_needs_resolution"] = True
            signal["reference_text"] = ref
            signal["continuity_hint"] = f"检测到指代词'{ref}'，需要消解上下文"
            break

    if len(history) > 20:
        recent_active = sum(1 for msg in history[-5:] if msg.get("role") == "user")
        signal["activity_level"] = recent_active / 5.0
        if recent_active < 2:
            signal["context_decay"] = True
            signal["continuity_hint"] = "长对话中近期交互稀疏，上下文可能衰减"

    return signal


def _r4_self_check(user_input: str, intent_type: str, methodology: dict, capability_gap) -> dict:
    """
    R4七维自检 — 元宪法「三思后行」的代码事实。
    在关键决策点（能力评估后、执行前）强制执行。
    7维: ①方向一致 ②看板衔接 ③最小侵入 ④无过度设计 ⑤治标+治本 ⑥可验证 ⑦精神内核对齐
    """
    result = {"warnings": [], "adjustments": {}, "blocked": False, "block_reason": ""}

    # ① 方向一致：意图与方法论策略是否一致
    strategy = methodology.get("strategy", "")
    if intent_type == "hardware" and strategy not in ("tool_first", "slow"):
        result["warnings"].append(f"方向不一致: hardware意图但策略={strategy}，建议tool_first")
        result["adjustments"]["strategy"] = "tool_first"

    # ② 最小侵入：是否需要造新工具
    if capability_gap and methodology.get("strategy") == "tool_first":
        result["warnings"].append(f"能力缺口: {capability_gap}，将尝试工具构建")

    # ③ 无过度设计：操作类问题不应走纯推理路径
    if intent_type in ("hardware", "code") and methodology.get("strategy") == "reasoning_only":
        result["warnings"].append(f"过度设计: {intent_type}意图不应走纯推理，切换为tool_first")
        result["adjustments"]["strategy"] = "tool_first"

    # ④ 治标+治本：质疑类必须有历史记录
    if intent_type == "challenge" and not methodology.get("challenge_history"):
        result["warnings"].append("质疑类无历史记录，已降级为complex_query")

    # ⑤ 可验证：操作类问题必须走工具执行路径
    if intent_type == "hardware" and not methodology.get("source_priority"):
        result["adjustments"]["source_priority"] = ["工具执行", "经验池", "知识库", "Ollama"]

    # ⑥ 精神内核对齐：伪造数据检测
    if methodology.get("fabricated_data_detected"):
        result["blocked"] = True
        result["block_reason"] = "检测到伪造数据倾向，阻断执行以保护真实性"

    # ⑦ 看板衔接：连续性信号检查
    if methodology.get("topic_drift"):
        result["warnings"].append(f"话题漂移: {methodology.get('drift_direction', '')}，注意上下文衔接")

    return result
