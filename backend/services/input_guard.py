"""
输入守卫 — 长输入提炼、资源保护、认知节律保护
"""
from loguru import logger


async def guard_input(
    user_input: str,
    resource_aware: bool,
    input_processor_available: bool,
    stimulus_priority: float,
    fetch_ollama_all_fn,
    fetch_external_api_fn,
    never_give_up_fn,
    run_sync_fn,
    get_self_model_fn,
    alchemize_error_fn,
):
    """
    输入守卫处理 — 返回提炼后的user_input + 是否应提前返回的事件列表

    Returns:
        {
            "user_input": str,
            "events": list,       # [(event_type, data), ...]
            "should_return": bool, # True=资源保护已触发，应提前返回
            "early_result": dict | None,  # should_return时的result payload
        }
    """
    events = []
    should_return = False
    early_result = None

    MAX_INPUT_LENGTH = 4000
    if len(user_input) > MAX_INPUT_LENGTH:
        if input_processor_available:
            try:
                from core.input_processing.processor import get_input_processor
                processor = get_input_processor()
                mem_usage = 0.5
                mode = "normal"
                if resource_aware:
                    try:
                        from core.resource_awareness.health_monitor import get_health_monitor
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
                    events.append(("step", {"phase": "输入提炼", "status": "info", "detail": detail, "skeleton": processed.skeleton.to_dict(), "cognitive_strategy": processed.cognitive_strategy}))
                user_input = processed.distilled
            except Exception as e:
                logger.warning(f"动态提炼失败，回退截断: {e}")
                alchemize_error_fn(e, context={"input_len": len(user_input)}, phase="input_distill")
                user_input = user_input[:MAX_INPUT_LENGTH]
        else:
            logger.warning(f"输入过长({len(user_input)}字符)，截断至{MAX_INPUT_LENGTH}")
            user_input = user_input[:MAX_INPUT_LENGTH]

    if resource_aware:
        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            snap = monitor.check()
            _sm_health = 1.0
            _sm_obj = get_self_model_fn()
            if _sm_obj:
                try:
                    _sm_snap = _sm_obj.snapshot()
                    _sm_health = _sm_snap.get("health", {}).get("score", 1.0)
                except Exception:
                    logger.warning("操作降级跳过")
            _mem_threshold = 0.85 if stimulus_priority >= 0.5 else 0.75
            _health_threshold = 0.3 if stimulus_priority >= 0.5 else 0.4
            if snap.memory_usage > _mem_threshold or _sm_health < _health_threshold:
                reason = f"内存{snap.memory_usage:.1%}" if snap.memory_usage > 0.85 else f"系统健康度低({_sm_health:.1%})"
                logger.warning(f"资源保护触发: {reason}，走轻量响应")
                events.append(("step", {"phase": "资源保护", "status": "warning", "detail": f"{reason}，使用轻量响应"}))
                try:
                    ollama_result = await run_sync_fn(fetch_ollama_all_fn, user_input, timeout=30, intent_type="unknown")
                    if ollama_result and ollama_result.get("response"):
                        early_result = {"response": ollama_result["response"], "attempts": [{"source": "Ollama(轻量)", "success": True}], "intent": "simple", "confidence": 0.5, "route": "fast"}
                    else:
                        early_result = {"response": never_give_up_fn(user_input, []), "attempts": [], "intent": "simple", "confidence": 0.3, "route": "fast"}
                except Exception:
                    early_result = {"response": never_give_up_fn(user_input, []), "attempts": [], "intent": "simple", "confidence": 0.2, "route": "fast"}
                should_return = True
        except Exception:
            logger.warning("操作降级跳过")

    return {
        "user_input": user_input,
        "events": events,
        "should_return": should_return,
        "early_result": early_result,
    }


async def check_inner_time_guard(methodology: dict, user_input: str, fetch_external_api_fn, fetch_ollama_all_fn, run_sync_fn):
    """
    认知节律保护 — 内在时间SLEEPING时走轻量路径

    Returns:
        {
            "should_return": bool,
            "early_result": dict | None,
            "events": list,
        }
    """
    events = []
    should_return = False
    early_result = None

    if not methodology.get("inner_time_conservative"):
        return {"should_return": False, "early_result": None, "events": []}

    try:
        from core.presence.inner_time import inner_time_engine
        _it_check = inner_time_engine.get_state()
        if _it_check.tick_count < 10:
            logger.info(f"⏱️ 内在时间tick不足({_it_check.tick_count})，跳过节律保护")
            return {"should_return": False, "early_result": None, "events": []}

        events.append(("step", {"phase": "认知节律保护", "status": "info", "detail": "内在时间处于SLEEPING阶段，走轻量响应"}))
        _it_light_result = await fetch_external_api_fn(user_input, conversation_context="", truth_insights="")
        if _it_light_result and _it_light_result.get("response"):
            early_result = {"response": _it_light_result["response"], "attempts": [{"source": "外部API(节律保护)", "success": True}], "intent": "unknown", "confidence": 0.6, "route": "fast"}
            should_return = True
        else:
            ollama_result = await run_sync_fn(fetch_ollama_all_fn, user_input, timeout=30, intent_type="unknown")
            if ollama_result and ollama_result.get("response"):
                early_result = {"response": ollama_result["response"], "attempts": [{"source": "Ollama(节律保护)", "success": True}], "intent": "unknown", "confidence": 0.5, "route": "fast"}
                should_return = True
    except Exception:
        logger.warning("认知节律保护路径降级")

    return {"should_return": should_return, "early_result": early_result, "events": events}