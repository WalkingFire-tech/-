import asyncio
import re
from loguru import logger

from backend.services.auto_fix_service import auto_fix_checkpoint as _auto_fix_checkpoint
from backend.services.input_preprocessor import build_fallback_dispatch as _build_fallback_dispatch
from backend.services.orchestrator_helpers import get_cognitive_planner_safe as _get_cognitive_planner, get_self_model_safe as _get_self_model
from backend.services.path_handlers._shared import _fast_executor
from backend.services.self_reference_detector import is_self_referential, generate_self_reference_response


async def dispatch_intent(
    user_input: str, context: dict, history: list,
    attempts: list, model: str,
) -> dict:
    events = []
    intent_type = "unknown"
    route = "slow"
    confidence = 0.3
    methodology = {}
    dispatch_result = {"intent_type": intent_type, "route": route, "confidence": confidence, "field_context": {}, "execution_plan": {"tasks": []}}
    _cognitive_perception = {}
    cp = None
    _cognitive_bypass_future = None
    _rule_actions = []
    final_response = None
    should_return = False

    logger.info(f"📩 收到请求: '{user_input}'")
    events.append({"type": "step", "data": {"phase": "意图识别", "status": "running", "detail": "分析问题类型和复杂度..."}})

    try:
        from core.cognitive_dispatcher import get_cognitive_dispatcher
        dispatcher = get_cognitive_dispatcher()

        raw_intent, raw_conf = dispatcher._quick_intent_classification(user_input)
        logger.info(f"🔍 快速意图: raw_intent={raw_intent} raw_conf={raw_conf:.2f}")

        dispatch_result = None
        try:
            loop = asyncio.get_event_loop()
            dispatch_result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: dispatcher.dispatch(user_query=user_input, context=context)),
                timeout=15.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"意图识别dispatch超时(5s)，使用快速分类结果: {raw_intent}")
        except Exception as _de:
            logger.warning(f"意图识别dispatch异常: {_de}")

        if dispatch_result:
            intent_type = dispatch_result.get("intent_type", "unknown")
            route = dispatch_result.get("route", "slow")
            confidence = dispatch_result.get("confidence", 0.5)
        else:
            dispatch_result = _build_fallback_dispatch(raw_intent, raw_conf)
            intent_type = dispatch_result["intent_type"]
            route = dispatch_result["route"]
            confidence = dispatch_result["confidence"]

        _field_context = dispatch_result.get("field_context", {})
        if _field_context:
            _fc_sensing = _field_context.get("_sensing_mode", "unknown")
            _fc_new_topic = _field_context.get("is_new_topic", False)
            _fc_familiar = _field_context.get("is_familiar", False)
            _fc_residual = _field_context.get("residual_strength", 0.0)

            if _fc_sensing == "blind":
                logger.warning("场域失明: embedding不可用, 场域辅助决策降级")
                try:
                    from infrastructure.database_manager import DatabaseManager
                    _db = DatabaseManager.get("data/spirit_lessons.db")
                    _db.execute(
                        "INSERT INTO spirit_lessons (lesson_type, lesson_text, severity, context) VALUES (?, ?, ?, ?)",
                        ("field_blind", f"场域失明: embedding不可用, query={user_input[:50]}", 3, "M2_field_context"),
                        commit=True
                    )
                except Exception:
                    pass

            if _fc_new_topic:
                methodology.setdefault("field_topic_shift", True)
                methodology.setdefault("need_analogous_match", True)
                logger.info("场域感知: 话题跳跃检测, 提升骨架联想权重")
            elif _fc_familiar:
                methodology.setdefault("field_prefer_reflex", True)
                logger.info("场域感知: 熟悉话题, 优先本能匹配")

            if _fc_residual > 0.5:
                methodology.setdefault("field_continuity", _fc_residual)
                methodology.setdefault("previous_topic", _field_context.get("previous_topic", ""))

        _exec_plan = dispatch_result.get("execution_plan", {})
        _lessons_patch = _exec_plan.get("methodology_patch", {})
        if _lessons_patch:
            methodology.update(_lessons_patch)
            logger.info(f"📝 教训行为映射消费: {list(_lessons_patch.keys())}")

        try:
            from core.self.model import get_self_model
            _sm = get_self_model()
            _profile = _sm.get("capability_profile", {}) if isinstance(_sm, dict) else {}
            if not _profile and hasattr(_sm, 'capability_profile'):
                _profile = _sm.capability_profile
            if _profile:
                _strength = _profile.get("overall_strength", 0.0)
                _gaps = _profile.get("gaps", [])
                _tool_count = _profile.get("tools", {}).get("registered", 0)

                if _strength < 0.3:
                    methodology["conservative_mode"] = True
                    methodology["reduced_confidence_factor"] = 0.6
                    logger.info(f"🧠 SelfModel: 能力不足(strength={_strength:.2f}), 启用保守模式")
                elif _strength > 0.7:
                    methodology["aggressive_mode"] = True
                    methodology["confidence_boost"] = 1.1
                    logger.info(f"🧠 SelfModel: 能力充沛(strength={_strength:.2f}), 提升置信度")

                if _gaps:
                    gap_types = [g.get("type", "") for g in _gaps[:3]]
                    methodology["known_capability_gaps"] = gap_types
                    logger.info(f"🧠 SelfModel: 已知能力缺口 {gap_types}")

                if _tool_count < 3:
                    methodology["prefer_knowledge_path"] = True
                    methodology["skip_tool_path"] = True
                    logger.info(f"🧠 SelfModel: 工具不足({_tool_count}个), 优先知识路径")
        except Exception:
            pass

        raw_intent, raw_conf = dispatcher._quick_intent_classification(user_input)
        logger.info(f"🔍 意图识别: query='{user_input}' dispatch_intent={intent_type} raw_intent={raw_intent} route={route}")

        attempts.append(("意图识别", True, f"{intent_type}({route})"))
        events.append({"type": "step", "data": {"phase": "意图识别", "status": "done", "detail": f"识别为「{intent_type}」，置信度={confidence:.0%}"}})
    except Exception as e:
        logger.warning(f"意图识别异常: {e}", exc_info=True)
        intent_type = "unknown"
        route = "slow"
        confidence = 0.3
        dispatch_result = {"intent_type": intent_type, "route": route, "confidence": confidence, "field_context": {}, "execution_plan": {"tasks": []}}
        attempts.append(("意图识别", False, str(e)[:50]))
        events.append({"type": "step", "data": {"phase": "意图识别", "status": "done", "detail": "识别失败，按复杂问题处理"}})

    if is_self_referential(user_input):
        _sr_result = generate_self_reference_response(user_input)
        final_response = _sr_result["response"]
        intent_type = _sr_result["intent_type"]
        confidence = _sr_result["confidence"]
        route = _sr_result["route"]
        events.append({"type": "step", "data": {"phase": "自我参照检测", "status": "done", "detail": "检测到自我参照问题，进入存在性感知路径"}})
        events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type, "confidence": confidence, "route": route}})
        should_return = True

        try:
            from core.presence.inner_time import inner_time_engine, CognitiveEventType
            inner_time_engine.tick(CognitiveEventType.SELF_REFERENCE, intensity=0.9, description=f"self_ref:{user_input[:30]}")
        except Exception:
            pass

        try:
            _sm = _get_self_model()
            if _sm and hasattr(_sm, 'record_cognitive_cycle'):
                _sm.record_cognitive_cycle(
                    perception={"self_referential": True, "query": user_input[:50]},
                    validation={"anchor_layers": _sr_result.get("anchor_layers", {})},
                )
        except Exception:
            pass

        return {
            "intent_type": intent_type, "route": route, "confidence": confidence,
            "methodology": methodology, "dispatch_result": dispatch_result,
            "cognitive_perception": _cognitive_perception, "cp": cp,
            "cognitive_bypass_future": _cognitive_bypass_future,
            "rule_actions": _rule_actions, "final_response": final_response,
            "should_return": should_return, "events": events,
        }

    try:
        _af1 = await _auto_fix_checkpoint(attempts, methodology, user_input, intent_type, "意图识别后")
        if _af1["fixes_applied"] > 0:
            events.append({"type": "step", "data": {"phase": "自我修复", "status": "done", "detail": f"🔧 意图阶段修复{_af1['fixes_applied']}项，已调整策略"}})
    except Exception:
        pass

    cp = _get_cognitive_planner()
    if cp:
        try:
            _cognitive_perception = cp._perceive(user_input, context)
            emotion = _cognitive_perception.get("emotion", "neutral")
            urgency = _cognitive_perception.get("urgency", 0.5)
            confusion = _cognitive_perception.get("confusion", 0.0)
            if emotion != "neutral" or urgency > 0.7 or confusion > 0.5:
                events.append({"type": "step", "data": {"phase": "L1认知感知", "status": "done",
                    "detail": f"情绪={emotion}, 紧迫度={urgency:.1f}, 困惑度={confusion:.1f}"}})
            logger.warning(f"L1认知感知: emotion={emotion}, urgency={urgency:.2f}, confusion={confusion:.2f}")
            _sm = _get_self_model()
            if _sm:
                _sm.record_cognitive_cycle(perception=_cognitive_perception)
            events.append({"type": "thinking", "data": {
                "phase": f"我感知到你的意图是「{intent_type}」",
                "confidence": float(confidence),
                "emotion": emotion,
                "urgency": float(urgency),
                "confusion": float(confusion),
            }})

            if urgency > 0.8:
                route = "fast"
                logger.info(f"⚡ 紧迫度高({urgency:.1f})，切换到快速路由")
            if confusion > 0.7:
                methodology.setdefault("need_essence_reasoning", True)
                logger.info(f"🤔 困惑度高({confusion:.1f})，启用本质推理")
            if emotion in ("frustrated", "angry", "anxious"):
                methodology.setdefault("empathy_first", True)
                methodology.setdefault("tone_adjustment", emotion)
                logger.info(f"💡 情绪={emotion}，启用共情优先模式")
            if emotion == "curious" and confusion < 0.3:
                methodology.setdefault("depth_mode", True)
                logger.info(f"💡 好奇+低困惑，启用深度探索模式")
        except Exception as e:
            logger.warning(f"L1认知感知跳过: {e}")

        try:
            _bypass_ctx = {"history": context.get("history", [])[:5]} if isinstance(context, dict) else {}
            loop = asyncio.get_running_loop()
            _cognitive_bypass_future = loop.run_in_executor(
                _fast_executor, lambda: cp.process(user_input, _bypass_ctx)
            )
        except Exception:
            logger.warning("操作降级跳过")

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
            events.append({"type": "step", "data": {"phase": "反射安全检查", "status": "done",
                "detail": f"反射规则触发: {_reflex_action}"}})
            logger.info(f"反射安全检查触发: action={_reflex_action}")
    except Exception as e:
        logger.warning(f"反射安全检查跳过: {e}")

    if _reflex_action:
        if _reflex_action in ("block", "reject") or _reflex_action.startswith("block:"):
            _block_msg = _reflex_action.split(":", 1)[1] if ":" in _reflex_action else "此操作已被安全策略拦截。"
            final_response = _block_msg
            events.append({"type": "step", "data": {"phase": "安全拦截", "status": "done", "detail": "反射规则拦截了潜在危险操作"}})
            events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type}})
            should_return = True
            return {
                "intent_type": intent_type, "route": route, "confidence": confidence,
                "methodology": methodology, "dispatch_result": dispatch_result,
                "cognitive_perception": _cognitive_perception, "cp": cp,
                "cognitive_bypass_future": _cognitive_bypass_future,
                "rule_actions": _rule_actions, "final_response": final_response,
                "should_return": should_return, "events": events,
            }
        elif _reflex_action.startswith("warn:"):
            _rule_actions.append(_reflex_action)
        else:
            _rule_actions.append(_reflex_action)

    from backend.services.rule_evaluation import evaluate_rules_async
    _rule_actions = await evaluate_rules_async(user_input, intent_type, model_name=model)
    if _rule_actions:
        events.append({"type": "step", "data": {"phase": "规则推理", "status": "done", "detail": f"匹配{len(_rule_actions)}条规则动作"}})

    return {
        "intent_type": intent_type, "route": route, "confidence": confidence,
        "methodology": methodology, "dispatch_result": dispatch_result,
        "cognitive_perception": _cognitive_perception, "cp": cp,
        "cognitive_bypass_future": _cognitive_bypass_future,
        "rule_actions": _rule_actions, "final_response": final_response,
        "should_return": should_return, "events": events,
    }