"""
聊天路由 — /api/chat, /api/chat/stream, /api/feedback, /api/chat-history/*
"""
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from infrastructure.database_manager import DatabaseManager

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

    from backend.chat_handler import chat_never_giveup

    try:
        result = await asyncio.wait_for(chat_never_giveup(user_input, request), timeout=90)
    except asyncio.TimeoutError:
        logger.warning(f"非流式聊天超时(90s): {user_input[:50]}")
        return {
            "success": True,
            "response": "处理超时，请使用流式接口(/api/chat/stream)获取更好的体验。",
            "model": model,
            "intent": "timeout",
            "confidence": 0.1,
            "route": "timeout",
            "attempts": [],
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
            async for chunk in stream_generator(user_input, {"history": history, "session_id": session_id}):
                elapsed = asyncio.get_running_loop().time() - start_time
                if elapsed > max_duration:
                    logger.warning(f"流式生成超时({elapsed:.0f}s>{max_duration}s)，强制结束")
                    break
                if '"type": "result"' in chunk:
                    has_result = True
                yield chunk
        except Exception as e:
            logger.error(f"流式生成器异常: {e}")
        if not has_result:
            fallback = json.dumps({
                "type": "result",
                "response": "处理超时，请稍后重试。",
                "attempts": [],
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
    try:
        from datetime import datetime
        db = DatabaseManager.get("data/experience_pool.db")

        db.execute(
            "UPDATE experiences SET user_feedback = ? WHERE id = (SELECT MAX(id) FROM experiences)",
            (score,), commit=True
        )

    except Exception:
        logger.warning("操作降级跳过")
    return {"success": True, "message": "感谢反馈"}


@router.get("/chat-history/sessions")
async def get_chat_sessions(limit: int = 20, offset: int = 0):
    try:
        from infrastructure.chat_history import get_chat_history
        ch = get_chat_history()
        return {"sessions": ch.get_sessions(limit, offset), "stats": ch.get_stats()}
    except Exception as e:
        return {"error": str(e), "sessions": []}


@router.get("/chat-history/sessions/{session_id}")
async def get_chat_session_messages(session_id: str, limit: int = 100, before_id: int = 0):
    try:
        from infrastructure.chat_history import get_chat_history
        ch = get_chat_history()
        return {"session_id": session_id, "messages": ch.get_messages(session_id, limit, before_id)}
    except Exception as e:
        return {"error": str(e), "messages": []}


@router.post("/chat-history/sessions")
async def create_chat_session(request: dict):
    try:
        from infrastructure.chat_history import get_chat_history
        ch = get_chat_history()
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
        from infrastructure.chat_history import get_chat_history
        ch = get_chat_history()
        ch.delete_session(session_id)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/chat-history/search")
async def search_chat_history(q: str = "", limit: int = 20):
    try:
        from infrastructure.chat_history import get_chat_history
        ch = get_chat_history()
        return {"results": ch.search(q, limit)}
    except Exception as e:
        return {"error": str(e), "results": []}


@router.get("/chat-history/stats")
async def get_chat_history_stats():
    try:
        from infrastructure.chat_history import get_chat_history
        return get_chat_history().get_stats()
    except Exception as e:
        return {"error": str(e)}