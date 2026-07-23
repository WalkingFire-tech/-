import asyncio
from loguru import logger

from backend.services.input_preprocessor import (
    generate_smart_reply as _generate_smart_reply,
    solve_history_query as _solve_history_query,
)
from backend.services.path_handlers._shared import _save_to_experience_pool
from backend.services.path_handlers.ollama_path import (
    get_available_ollama_model_async as _get_available_ollama_model_async,
    fetch_ollama as _fetch_ollama,
)
from backend.services.path_handlers.external_api_path import fetch_external_api as _fetch_external_api
from backend.services.path_handlers.experience_path import get_last_response as _get_last_response


async def handle_fast_path(
    intent_type: str, user_input: str, attempts: list,
    conversation_context: str, model: str,
) -> dict:
    events = []
    final_response = None
    handled = False
    new_intent_type = intent_type

    if intent_type == "greeting":
        final_response = "嘿，我在。有什么想聊的，或者遇到了什么问题？我们一起看看。"
        events.append({"type": "step", "data": {"phase": "快速回复", "status": "done", "detail": "问候语直接回复"}})
        events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type}})
        handled = True
        return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}

    if intent_type == "confirmation":
        final_response = "好的，我明白了。"
        events.append({"type": "step", "data": {"phase": "快速回复", "status": "done", "detail": "确认直接回复"}})
        events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type}})
        handled = True
        return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}

    if intent_type == "history_query":

        final_response = await _solve_history_query(user_input)
        events.append({"type": "step", "data": {"phase": "历史查询", "status": "done", "detail": "检索历史记录"}})
        events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type}})
        handled = True
        return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}

    if intent_type == "time":
        try:
            from datetime import datetime
            now = datetime.now()
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            final_response = f"现在是 {now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]} {now.strftime('%H时%M分%S秒')}"
            events.append({"type": "step", "data": {"phase": "时间查询", "status": "done", "detail": "时间快速路径"}})
            events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type, "confidence": 0.95}})
            handled = True
            return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}
        except Exception as _te:
            logger.warning(f"时间查询异常: {_te}")

    if intent_type == "simple_query":
        import re as _calc_re
        calc_match = _calc_re.search(r'(\d+\s*[\+\-\*/×÷]\s*\d+)', user_input)
        if calc_match:
            try:
                expr = calc_match.group(1).replace('×', '*').replace('÷', '/')
                _allowed = set("0123456789+-*/. ")
                if all(c in _allowed for c in expr):
                    result = eval(expr, {"__builtins__": {}}, {})
                    final_response = f"{calc_match.group(1)} = {result}"
                    events.append({"type": "step", "data": {"phase": "计算器", "status": "done", "detail": "calc fast path"}})
                    events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type, "confidence": 0.95}})
                    handled = True
                    return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}
            except Exception:
                pass

    if intent_type == "challenge":
        events.append({"type": "step", "data": {"phase": "质疑检测", "status": "running", "detail": "用户质疑上一轮回答，触发重验证..."}})

        previous_response = _get_last_response(user_input)
        if previous_response:
            challenge_prompt = (
                f"你上一轮的回答是：\n---\n{previous_response}\n---\n"
                f"用户对此提出了质疑：「{user_input}」。请重新严谨论证，"
                "检查上一轮回答中是否有事实错误、逻辑漏洞或不严谨之处，"
                "并给出修正后的回答。如果上一轮回答是正确的，请给出更有力的论证和证据。"
            )
            events.append({"type": "step", "data": {"phase": "质疑检测", "status": "progress", "detail": "已拼接上一轮回答，启动重验证推理..."}})


            _model = await _get_available_ollama_model_async()
            challenge_result = None
            if _model:
                challenge_result = await _fetch_ollama(challenge_prompt, _model, timeout=30, conversation_context=conversation_context)
            if not challenge_result:
                challenge_result = await _fetch_external_api(challenge_prompt, conversation_context=conversation_context)
            if challenge_result and challenge_result.get("response"):
                final_response = challenge_result["response"]
                _save_to_experience_pool(user_input, final_response, success=True, intent_type="challenge", model_name="challenge")
                attempts.append(("质疑重验证", True, "已重新论证并修正"))
                events.append({"type": "step", "data": {"phase": "质疑检测", "status": "done", "detail": "重验证完成，已修正回答 ✅"}})
            else:
                rule_challenge = _generate_smart_reply(challenge_prompt, "complex_query")
                if rule_challenge == "__NEED_DYNAMIC_REPLY__":
                    rule_challenge = "我重新审视了你的质疑，但目前无法生成更深入的重验证。请提供更多具体信息。"
                final_response = f"🔍 你提出了质疑，我重新审视了上一轮的回答：\n\n{rule_challenge}"
                attempts.append(("质疑重验证", True, "规则重验证"))
                events.append({"type": "step", "data": {"phase": "质疑检测", "status": "done", "detail": "使用规则重验证完成"}})
            events.append({"type": "result", "data": {"response": final_response, "attempts": attempts, "intent": intent_type}})
            handled = True
            return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}
        else:
            events.append({"type": "step", "data": {"phase": "质疑检测", "status": "done", "detail": "未找到上一轮回答记录，降级为正常处理"}})
            new_intent_type = "complex_query"

    return {"handled": handled, "final_response": final_response, "events": events, "new_intent_type": new_intent_type}


async def handle_map_weather_fast_path(
    intent_type: str, user_input: str, attempts: list, final_response: str,
) -> dict:
    events = []
    confidence = None

    if intent_type == "map":
        try:
            from core.capability_creation_loop import capability_creation_loop
            events.append({"type": "step", "data": {"phase": "地图生成", "status": "running", "detail": "检测到地图意图，直接生成地图..."}})
            map_result = await capability_creation_loop._solve_map_render(user_input)
            if map_result and map_result.get("success"):
                final_response = map_result["data"]
                attempts.append(("地图生成", True, "map fast path"))
                confidence = 0.85
                events.append({"type": "step", "data": {"phase": "地图生成", "status": "done", "detail": "地图已生成 ✅"}})
                logger.info("🗺️ Map快速路径: 地图生成成功")
            else:
                events.append({"type": "step", "data": {"phase": "地图生成", "status": "done", "detail": "地图生成失败，尝试常规路径..."}})
                logger.warning("🗺️ Map快速路径失败，回退到常规路径")
        except Exception as _me:
            logger.warning(f"Map快速路径异常: {_me}", exc_info=True)
            events.append({"type": "step", "data": {"phase": "地图生成", "status": "done", "detail": f"地图生成异常({str(_me)[:60]})，尝试常规路径..."}})

    if intent_type == "weather" and not final_response:
        try:
            from core.capability_creation_loop import capability_creation_loop
            events.append({"type": "step", "data": {"phase": "天气查询", "status": "running", "detail": "检测到天气意图，正在获取天气信息..."}})
            weather_result = await capability_creation_loop._solve_weather_query(user_input)
            if weather_result and weather_result.get("success"):
                final_response = weather_result["data"]
                attempts.append(("天气查询", True, "weather fast path"))
                confidence = 0.85
                events.append({"type": "step", "data": {"phase": "天气查询", "status": "done", "detail": "天气信息已获取 ✅"}})
                logger.info("🌤️ Weather快速路径: 天气查询成功")
            else:
                events.append({"type": "step", "data": {"phase": "天气查询", "status": "done", "detail": "天气查询失败，尝试常规路径..."}})
                logger.warning("🌤️ Weather快速路径失败，回退到常规路径")
        except Exception as _we:
            logger.warning(f"Weather快速路径异常: {_we}", exc_info=True)
            events.append({"type": "step", "data": {"phase": "天气查询", "status": "done", "detail": f"天气查询异常({str(_we)[:60]})，尝试常规路径..."}})

    return {"final_response": final_response, "confidence": confidence, "events": events}


def build_fast_path_result(final_response, attempts, intent_type, confidence, route, start_time, spirit_core_available):
    """快速路径提前返回 — 构建result payload"""
    import time
    elapsed = time.time() - start_time
    logger.info(f"⏱️ [T+{elapsed:.1f}s] 快速路径已完成，跳过阶段4-7")
    result = {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "elapsed": round(elapsed, 1),
        "spirit_compliant": spirit_core_available,
        "candidates": [],
        "path_contributions": {},
        "token_usage": {},
        "cbnr": {},
        "session_id": "",
        "companion_layers": {},
        "cognitive_layers": {},
    }
    logger.info(f"✅ 快速路径响应已发送({elapsed:.1f}秒)")
    return result