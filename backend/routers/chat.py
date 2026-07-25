"""
聊天路由 — /api/chat, /api/chat/stream, /api/feedback, /api/chat-history/*
"""
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from core.ports.adapters import get_storage_port, get_chat_history_port

router = APIRouter()


@router.post("/chat")
async def chat(request: dict):
    user_input = request.get("message", "")
    model = request.get("model", "auto")

    try:
        from core.defense.input_sanitizer import input_sanitizer
        user_input, threat = input_sanitizer.sanitize(user_input)
        if threat:
            return {"success": True, "response": f"检测到潜在安全风险({threat})，输入已清理。请重新描述您的问题。", "model": model, "intent": "security_block", "confidence": 1.0}
    except Exception:
        user_input = (user_input or "").strip().rstrip("/\\|")

    try:
        from backend.services.chat_orchestrator import cognitive_process
        from core.ports import NullEventSink
        result = await asyncio.wait_for(
            cognitive_process(user_input, event_sink=NullEventSink()),
            timeout=90
        )
        return {
            "success": True,
            "response": result.get("response", ""),
            "model": model,
            "intent": result.get("intent", "unknown"),
            "confidence": result.get("confidence", 0.5),
            "route": result.get("route", "slow"),
            "attempts": [],
        }
    except asyncio.TimeoutError:
        logger.warning(f"认知处理超时(90s): {user_input[:50]}")
    except Exception as e:
        logger.warning(f"认知处理异常: {e}")

    from backend.chat_handler import chat_never_giveup

    try:
        result = await asyncio.wait_for(chat_never_giveup(user_input, request), timeout=90)
    except asyncio.TimeoutError:
        logger.warning(f"非流式聊天超时(90s): {user_input[:50]}")

        system_state = "unknown"
        try:
            from core.presence.existence_layer import ExistenceLayer
            el = ExistenceLayer()
            if hasattr(el, 'current_state'):
                system_state = el.current_state
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        if system_state in ("growing", "resting"):
            try:
                from backend.chat_handler import _query_experience_pool_semantic
                similar = _query_experience_pool_semantic(user_input, top_k=1)
                if similar and similar[0].get("response"):
                    return {
                        "success": True,
                        "response": similar[0]["response"] + "\n\n（系统当前处于" + system_state + "状态，使用历史经验回复）",
                        "model": model,
                        "intent": "timeout_degraded",
                        "confidence": 0.3,
                        "route": "timeout_degraded",
                        "attempts": [("经验池降级", True, f"系统{system_state}状态")],
                    }
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")

        try:
            from core.spirit_core import spirit_core
            timeout_response = spirit_core._craft_meaningful_failure_response(
                user_input,
                [{"method": "chat_handler", "success": False, "error": f"处理超时(90s), 系统状态={system_state}"}]
            )
        except Exception:
            from backend.chat_handler import _generate_meaningful_fallback
            timeout_response = _generate_meaningful_fallback(
                user_input,
                [("chat_handler", False, f"处理超时(90s), 系统状态={system_state}")]
            )
        return {
            "success": True,
            "response": timeout_response,
            "model": model,
            "intent": "timeout",
            "confidence": 0.1,
            "route": "timeout",
            "attempts": [("chat_handler", False, f"处理超时(90s), 系统状态={system_state}")],
            "thinking_process": {"deep_intent": "timeout", "scene_role": "general", "intent_confidence": 0.1, "response_strategy": "timeout", "solution_path": []}
        }

    return {
        "success": True,
        "response": result["response"],
        "model": model,
        "intent": result.get("intent", "unknown"),
        "confidence": result.get("confidence", 0.5),
        "route": result.get("route", "slow"),
        "attempts": result.get("attempts", []),
        "thinking_process": {
            "deep_intent": result.get("intent", "unknown"),
            "scene_role": "general",
            "intent_confidence": result.get("confidence", 0.5),
            "response_strategy": result.get("route", "slow"),
            "solution_path": [a[0] for a in result.get("attempts", []) if a[1]]
        }
    }


@router.post("/chat/stream")
async def chat_stream(request: dict):
    user_input = request.get("message", "")
    history = request.get("history", [])
    session_id = request.get("session_id", "")

    try:
        from core.defense.input_sanitizer import input_sanitizer
        user_input, threat = input_sanitizer.sanitize(user_input)
        if threat:
            async def _blocked_stream():
                yield f"data: {{'type': 'content', 'content': '检测到潜在安全风险({threat})，输入已清理。请重新描述您的问题。'}}\n\n"
                yield f"data: {{'type': 'done'}}\n\n"
            return StreamingResponse(_blocked_stream(), media_type="text/event-stream")
    except Exception:
        user_input = (user_input or "").strip().rstrip("/\\|")

    from backend.chat_stream import chat_stream as stream_generator

    async def _safe_stream():
        has_result = False
        start_time = asyncio.get_running_loop().time()
        max_duration = 180
        try:
            async for event_type, data in stream_generator(user_input, {"history": history, "session_id": session_id}):
                elapsed = asyncio.get_running_loop().time() - start_time
                if elapsed > max_duration:
                    logger.warning(f"流式生成超时({elapsed:.0f}s>{max_duration}s)，强制结束")
                    break
                if event_type == "result":
                    has_result = True
                import json
                from backend.services.orchestrator_helpers import SafeEncoder
                try:
                    from core.stream_rules import StreamInterrupter
                    _si = StreamInterrupter()
                    _action = _si.check(event_type, data)
                    if _action and _action.type == "interrupt":
                        logger.info(f"StreamRule拦截: {_action.reason}")
                        continue
                    elif _action and _action.type == "inject":
                        data.update(_action.payload)
                except Exception as e:
                    logger.warning(f"操作降级跳过: {e}")
                yield f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False, cls=SafeEncoder)}\n\n"
        except Exception as e:
            logger.error(f"流式生成器异常: {e}")
        if not has_result:
            try:
                from backend.chat_handler import _generate_smart_reply
                meaningful = _generate_smart_reply(user_input, "unknown")
            except Exception:
                try:
                    from core.spirit_core import spirit_core
                    meaningful = spirit_core._craft_meaningful_failure_response(
                        user_input,
                        [{"method": "stream_orchestrator", "success": False, "error": "流式生成未产出结果"}]
                    )
                except Exception:
                    meaningful = f"关于「{user_input}」，我暂时无法给出完整回答。\n\n💡 建议：\n1. 换个方式提问（更具体或更简单）\n2. 提供更多背景信息\n3. 稍后重试"
            fallback = json.dumps({
                "type": "result",
                "response": meaningful,
                "attempts": [("流式生成", False, "未产出结果")],
                "intent": "error",
                "confidence": 0.1,
            }, ensure_ascii=False)
            yield f"data: {fallback}\n\n"

    return StreamingResponse(
        _safe_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "close",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/feedback")
async def feedback(request: dict):
    score = request.get("score", 0)
    conversation_id = request.get("conversation_id", "")
    response_id = request.get("response_id", "")
    reason = request.get("reason", "")

    try:
        from datetime import datetime
        db = get_storage_port("data/experience_pool.db")
        db.execute(
            "UPDATE experiences SET user_feedback = ? WHERE id = (SELECT MAX(id) FROM experiences)",
            (score,), commit=True
        )
    except Exception:
        logger.warning("操作降级跳过")

    try:
        from core.feedback.signal_capture import FeedbackSignalCapture, FeedbackSignal, FeedbackType
        from core.feedback.feedback_router import FeedbackSignalRouter
        from core.feedback.knowledge_pipeline import KnowledgePromotionPipeline

        capture = FeedbackSignalCapture()
        ft = FeedbackType.LIKE if score > 0 else FeedbackType.DISLIKE
        signal = FeedbackSignal(
            signal_id=f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            conversation_id=conversation_id,
            turn_id="",
            feedback_type=ft,
            value=score,
            context={"reason": reason, "response_id": response_id},
            timestamp=datetime.now().isoformat(),
            source="ui"
        )
        signal_id = capture.capture(signal)

        router = FeedbackSignalRouter()
        routed = router.route({
            "feedback_type": ft.value,
            "value": score,
            "context": {"reason": reason, "conversation_id": conversation_id}
        })

        if routed.category.value in ("pairwise_preference", "adoption", "correction"):
            try:
                unprocessed = capture.get_unprocessed_signals(limit=5)
                pipeline = KnowledgePromotionPipeline()
                for sig in unprocessed:
                    routed_sig = router.route(sig)
                    if routed_sig.category.value == "correction":
                        pipeline.add_candidate(
                            content=sig.get("context", {}).get("reason", ""),
                            source="user_correction",
                            signals=[sig]
                        )
                    capture.mark_processed(sig.get("signal_id", ""))
            except Exception as e:
                logger.warning(f"反馈管道处理失败: {e}")

        logger.info(f"📊 反馈已处理: {ft.value} score={score} category={routed.category.value}")
    except Exception as e:
        logger.warning(f"反馈信号管道降级: {e}")

    return {"success": True, "message": "感谢反馈"}


@router.get("/chat-history/sessions")
async def get_chat_sessions(limit: int = 20, offset: int = 0):
    try:
        ch = get_chat_history_port()
        return {"sessions": ch.get_sessions(limit, offset), "stats": ch.get_stats()}
    except Exception as e:
        return {"error": str(e), "sessions": []}


@router.get("/chat-history/sessions/{session_id}")
async def get_chat_session_messages(session_id: str, limit: int = 100, before_id: int = 0):
    try:
        ch = get_chat_history_port()
        return {"session_id": session_id, "messages": ch.get_messages(session_id, limit, before_id)}
    except Exception as e:
        return {"error": str(e), "messages": []}


@router.post("/chat-history/sessions")
async def create_chat_session(request: dict):
    try:
        ch = get_chat_history_port()
        session_id = ch.create_session(
            session_id=request.get("session_id"),
            title=request.get("title", "")
        )
        return {"session_id": session_id}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/chat-history/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    try:
        ch = get_chat_history_port()
        ch.delete_session(session_id)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/chat-history/search")
async def search_chat_history(q: str = "", limit: int = 20):
    try:
        ch = get_chat_history_port()
        return {"results": ch.search(q, limit)}
    except Exception as e:
        return {"error": str(e), "results": []}


@router.get("/chat-history/stats")
async def get_chat_history_stats():
    try:
        return get_chat_history_port().get_stats()
    except Exception as e:
        return {"error": str(e)}