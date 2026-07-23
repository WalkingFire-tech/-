"""
响应后处理 — 维度编排、内在时间tick、元认知自厌检测
"""
from loguru import logger


async def post_response_processing(
    user_input: str,
    final_response: str,
    intent_type: str,
    route: str,
    confidence: float,
    best: dict,
    stimulus_type,
    inner_time_available: bool,
    dim_orch,
):
    """
    响应后处理 — 维度编排、内在时间tick、元认知自厌检测

    Returns:
        {"events": list}
    """
    events = []

    if inner_time_available and stimulus_type.value not in ("internal", "scheduled"):
        try:
            from core.presence.inner_time import inner_time_engine, CognitiveEventType
            inner_time_engine.tick(CognitiveEventType.OUTPUT, intensity=1.0, description="response_sent")
        except Exception:
            pass

    if dim_orch:
        try:
            from core.cognition.dimension_orchestrator import CognitiveDimension
            dim_orch.update_dimension(CognitiveDimension.SYMBOLIC, confidence, f"route={route}")
            _alignment = dim_orch.decide_primary_dimension(user_input[:50])
            logger.debug(f"维度编排: 主={_alignment.primary_dimension.value}, 平衡={_alignment.wisdom_truth_vector:.2f}")
        except Exception:
            pass

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

    return {"events": events}