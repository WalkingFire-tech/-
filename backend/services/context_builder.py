import time
from loguru import logger

from backend.services.input_preprocessor import feature_enabled as _feature_enabled
from backend.services.orchestrator_helpers import (
    alchemize_error as _alchemize_error,
    perceive_continuity as _perceive_continuity,
    get_stereo_memory_context as _get_stereo_memory_context,
)
from backend.services.path_handlers._shared import _run_sync, _RESOURCE_AWARE

try:
    from core.resource_awareness.health_monitor import get_health_monitor
except ImportError:
    get_health_monitor = None


async def build_context(
    user_input: str, history: list, conversation_context: str,
    cbnr_context: dict, methodology: dict, _l1_normalized: dict,
    route: str, start_time: float,
) -> dict:
    events = []
    _continuity_signal = {}
    _presence_state = "awake"
    _query_registered = False

    try:

        _continuity_signal = _perceive_continuity(user_input, history)
        if _continuity_signal.get("topic_drift"):
            events.append({"type": "step", "data": {"phase": "连续性感知", "status": "done",
                "detail": f"🔄 话题漂移: {_continuity_signal['drift_direction']} (距离={_continuity_signal['drift_distance']:.2f})"}})
        if _continuity_signal.get("reference_needs_resolution"):
            events.append({"type": "step", "data": {"phase": "连续性感知", "status": "done",
                "detail": f"🔗 检测到指代: {_continuity_signal['reference_text']}"}})
        if _continuity_signal.get("context_decay"):
            events.append({"type": "step", "data": {"phase": "连续性感知", "status": "done",
                "detail": f"📉 上下文衰减: 最近{len(history)}轮对话, 活跃度={_continuity_signal['activity_level']:.2f}"}})
    except Exception as e:
        logger.warning(f"对话连续性感知跳过: {e}")

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
        logger.warning(f"CBNR L2: 压缩={_l2_result.compression_ratio:.1%}, 冲突={_l2_result.conflict_delta:.2f}, 模式={_l2_result.conflict_mode.value}")
    except Exception as e:
        logger.warning(f"CBNR L2跳过: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="CBNR_L2")

    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el.user_interaction()
        _presence_state = el.state.value if hasattr(el.state, 'value') else str(el.state)

        if _feature_enabled("path_weight_matrix"):
            _path_weights = {
                "experience": 1.0, "knowledge": 1.0, "fact": 1.0,
                "tool": 1.0, "self_reason": 1.0, "ollama": 1.0,
                "external_api": 1.0, "external_learning": 1.0,
            }

            try:
                from core.presence.probability_decision_bridge import get_probability_decision_bridge
                bridge = get_probability_decision_bridge()
                decision_ctx = bridge.get_decision_context()

                _path_weights = bridge.apply_to_path_weights(_path_weights, decision_ctx["path_weight_modulators"])
                methodology = bridge.apply_to_methodology(methodology, decision_ctx["behavioral_modifiers"])

                style_hint = decision_ctx.get("response_style_hint", "balanced")
                methodology.setdefault("response_style", style_hint)

                prob_ctx = decision_ctx.get("probability_context", {})
                tendency = prob_ctx.get("tendency", {})
                logger.info(
                    f"🌉 概率场桥接: exploration={tendency.get('exploration', 0.5):.2f}, "
                    f"tension={tendency.get('tension', 0.15):.2f}, "
                    f"style={style_hint}"
                )
            except Exception as bridge_err:
                logger.debug(f"概率场桥接降级，回退到二极管逻辑: {bridge_err}")

                if _presence_state == "growing":
                    methodology.setdefault("prefer_learning_path", True)
                    methodology.setdefault("need_essence_reasoning", True)
                    _path_weights.update({
                        "experience": 1.3, "knowledge": 1.3, "self_reason": 1.2,
                        "external_api": 1.2, "external_learning": 1.0,
                    })
                    logger.info(f"🌱 存在层=GROWING，优先学习路径")
                elif _presence_state == "resting":
                    methodology.setdefault("prefer_fast_path", True)
                    methodology.setdefault("skip_tool_path", True)
                    _path_weights.update({
                        "experience": 1.2, "fact": 1.1, "tool": 0.5,
                        "self_reason": 0.6, "ollama": 0.8, "external_api": 0.9,
                    })
                    logger.info(f"💤 存在层=RESTING，优先快速路径")
                elif _presence_state == "sleeping":
                    methodology.setdefault("skip_tool_path", True)
                    methodology.setdefault("prefer_knowledge_path", True)
                    _path_weights.update({
                        "knowledge": 1.5, "fact": 1.2, "experience": 1.0,
                        "tool": 0.2, "self_reason": 0.3, "ollama": 0.3,
                        "external_api": 0.4, "external_learning": 0.3,
                    })
                    logger.info(f"😴 存在层=SLEEPING，仅知识路径")

            try:
                from core.presence.inner_time import inner_time_engine
                it_state = inner_time_engine.get_state()
                it_phase = it_state.current_phase

                if it_state.cognitive_density > 1.5:
                    for k in _path_weights:
                        if k in ("self_reason", "knowledge"):
                            _path_weights[k] *= 1.2
                    methodology.setdefault("high_cognitive_density", True)
                elif it_state.cognitive_density < 0.1:
                    _path_weights.update({
                        "experience": _path_weights.get("experience", 1.0) * 1.1,
                        "fact": _path_weights.get("fact", 1.0) * 1.1,
                    })
                    methodology.setdefault("low_cognitive_density", True)

                methodology.setdefault("inner_time_phase", it_phase)
                methodology.setdefault("inner_time_flow", round(it_state.flow_rate, 2))
                methodology.setdefault("inner_time_rhythm", round(it_state.rhythm_bpm, 0))
                logger.info(f"⏱️ 内在时间节律: phase={it_phase}, density={it_state.cognitive_density:.2f}, flow={it_state.flow_rate:.2f}, bpm={it_state.rhythm_bpm:.0f}")
            except Exception:
                pass

            methodology["path_weights"] = _path_weights
        events.append({"type": "thinking", "data": {
            "phase": f"存在层状态: {_presence_state}",
            "presence_state": _presence_state,
        }})
    except Exception:
        logger.warning("操作降级跳过")

    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        reflections = el.get_recent_reflections(limit=3)
        if reflections:
            reflection_ctx = "[近期自我反思] " + " | ".join(r["note"][:80] for r in reflections)
            conversation_context = (conversation_context + "\n" + reflection_ctx) if conversation_context else reflection_ctx
            events.append({"type": "step", "data": {"phase": "自我反思注入", "status": "done",
                "detail": f"注入{len(reflections)}条近期反思笔记"}})
    except Exception:
        pass

    if _RESOURCE_AWARE and get_health_monitor is not None:
        try:
            monitor = get_health_monitor()
            monitor.register_query()
            _query_registered = True
            if monitor.is_emergency():
                events.append({"type": "warning", "data": {"type": "resource_emergency", "message": "系统资源紧张，正在保护性降级，回复可能较简短"}})
            elif monitor.is_conservative():
                events.append({"type": "info", "data": {"type": "resource_conservative", "message": "系统资源偏紧，已自动减少并行路径"}})
        except Exception:
            logger.warning("操作降级跳过")

    try:
        from infrastructure.event_bus import bus, EventTypes
        bus.publish(EventTypes.UserMessage, {
            "query": user_input[:200],
            "timestamp": time.time(),
            "route": route,
        })
    except Exception:
        logger.warning("操作降级跳过")

    try:

        stereo_context = await _run_sync(_get_stereo_memory_context, user_input, timeout=5)
        if stereo_context:
            conversation_context = conversation_context + "\n" + stereo_context if conversation_context else stereo_context
    except Exception:
        logger.warning("立体记忆上下文获取跳过")

    try:
        from core.relationship.model import get_relationship_model, InteractionType
        rm = get_relationship_model()
        rel_summary = rm.get_relationship_summary()
        trust = rel_summary.get("trust_level", 0.5)
        phase = rm.get_relationship_phase()
        interaction_count = rel_summary.get("total_interactions", 0)
        relationship_context = ""
        if interaction_count > 10 and trust >= 0.7:
            relationship_context = f"[你和我是老朋友了，信任度{trust:.0%}，可以更直接地交流]"
            methodology.setdefault("perspective_mode", "thinking_partner")
        elif trust >= 0.5:
            relationship_context = f"[关系:信任度{trust:.0%},阶段:{phase}]"
            methodology.setdefault("perspective_mode", "companion")
        elif trust < 0.3:
            relationship_context = f"[关系:信任度低({trust:.0%}),阶段:{phase},需要更谨慎、更详细地解释]"
            methodology.setdefault("perspective_mode", "guide")
        if relationship_context:
            conversation_context = (conversation_context + "\n" + relationship_context) if conversation_context else relationship_context
    except Exception as e:
        logger.warning(f"关系模型跳过: {e}")

    if methodology.get("self_referential"):
        try:
            from core.self.model import get_self_model
            _sm = get_self_model()
            _snap = _sm.snapshot()
            _p_count = _snap.get("values", {}).get("principles_count", 0)
            _a_count = _snap.get("values", {}).get("abilities_count", 0)
            _v_count = _snap.get("values", {}).get("violations_count", 0)
            _l_count = _snap.get("values", {}).get("lessons_count", 0)
            _sr_ctx = f"[用户在问关于你自身的问题。你持有{_p_count}条核心原则和{_a_count}项能力，经历过{_v_count}次原则违背，沉淀了{_l_count}条教训。请从第一人称真诚回应，不要罗列数据，而是表达你对自身存在的理解和感受。]"
            conversation_context = (conversation_context + "\n" + _sr_ctx) if conversation_context else _sr_ctx
        except Exception:
            pass

    if methodology.get("performative_risk"):
        _anti_perf_ctx = "[在场自检提醒：系统检测到你可能倾向于执行预设的回答模式而非真正回应这个人。请停下来——不要用框架包装，不要展示'我在思考'，而是直接说出你此刻的真实状态。如果你不确定，就说你不确定。如果你不知道，就说你不知道。真实比正确重要。]"
        conversation_context = (conversation_context + "\n" + _anti_perf_ctx) if conversation_context else _anti_perf_ctx

    return {
        "conversation_context": conversation_context,
        "cbnr_context": cbnr_context,
        "methodology": methodology,
        "continuity_signal": _continuity_signal,
        "presence_state": _presence_state,
        "query_registered": _query_registered,
        "events": events,
    }