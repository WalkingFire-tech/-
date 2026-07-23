"""
CBNR L1处理器 — 认知规范化在处理前进行认知复位
"""
from loguru import logger


async def process_cbnr_l1(
    user_input: str,
    intent_type: str,
    stimulus_type,
    stimulus_priority: float,
    resource_aware: bool = False,
) -> dict:
    """
    CBNR L1处理 — 认知复位/偏差清除/注意力权重
    
    Returns:
        {
            "cbnr_context": dict,      # CBNR指标
            "l1_normalized": dict,      # 归一化输入
            "events": list,             # 待emit的事件
        }
    """
    cbnr_context = {}
    l1_normalized = {"user_input": user_input, "intent": intent_type}
    events = []

    try:
        from core.cbnr.hub import get_cbnr_hub
        _cbnr_hub = get_cbnr_hub()
        _resource_mode = "normal"
        if resource_aware:
            try:
                from core.resource_awareness.health_monitor import get_health_monitor
                monitor = get_health_monitor()
                snap = monitor.check()
                from core.resource_awareness.health_monitor import OperatingMode
                if hasattr(snap, 'operating_mode'):
                    _resource_mode = snap.operating_mode.value if hasattr(snap.operating_mode, 'value') else str(snap.operating_mode)
            except Exception:
                logger.warning("操作降级跳过")
        _l1_result = _cbnr_hub.process_l1(
            {"user_input": user_input, "intent": intent_type,
             "_stimulus_type": stimulus_type.value, "_stimulus_priority": stimulus_priority},
            {"resource_mode": _resource_mode}
        )
        l1_normalized = _l1_result.normalized_input
        cbnr_context["l1_uncertainty"] = _l1_result.uncertainty
        cbnr_context["l1_strength"] = _l1_result.normalization_strength
        cbnr_context["l1_biases"] = _l1_result.bias_cleared
        cbnr_context["l1_principles"] = _l1_result.principles_anchored
        _attn = l1_normalized.get("_attention_weights", {})
        cbnr_context["l1_prediction_error"] = _attn.get("avg_prediction_error", 0.5)
        cbnr_context["l1_high_surprise"] = _attn.get("high_surprise", False)
        cbnr_context["l1_focus_boost"] = _attn.get("focus_boost", 1.0)
        cbnr_context["l1_info_retention"] = _l1_result.information_retention
        cbnr_context["l1_attention_fidelity"] = _l1_result.attention_fidelity
        if _l1_result.bias_cleared:
            logger.warning(f"CBNR L1: 清除偏差{_l1_result.bias_cleared}, 不确定性={_l1_result.uncertainty:.2f}")
        if _attn.get("high_surprise"):
            logger.info(f"CBNR L1: 高预测误差({cbnr_context['l1_prediction_error']:.2f}), 增强深度推理权重")
    except Exception as e:
        logger.warning(f"CBNR L1跳过: {e}")

    if cbnr_context:
        events.append(("awareness", {
            "cbnr_uncertainty": round(cbnr_context.get("l1_uncertainty", 0.5), 2),
            "cbnr_attention_fidelity": round(cbnr_context.get("l1_attention_fidelity", 0.5), 2),
            "cbnr_info_retention": round(cbnr_context.get("l1_info_retention", 1.0), 2),
            "cbnr_high_surprise": cbnr_context.get("l1_high_surprise", False),
        }))

    return {
        "cbnr_context": cbnr_context,
        "l1_normalized": l1_normalized,
        "events": events,
    }