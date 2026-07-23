"""
多智能体辩论处理 — 低置信度/高分歧时触发
"""
from loguru import logger


async def run_debate(
    user_input: str,
    candidates: list,
    confidence: float,
    truth_insights: str,
    conversation_context: str,
    spirit_resonances: list,
    alchemize_error_fn,
    emit_fn,
):
    """
    多智能体辩论 — 返回更新后的confidence和truth_insights

    Returns:
        (debate_result, confidence, truth_insights)
    """
    _debate_result = None

    if not candidates or len(candidates) < 2 or confidence >= 0.7:
        return _debate_result, confidence, truth_insights

    try:
        from core.debate.arena import debate_arena
        _debate_result = await debate_arena.debate(
            query=user_input,
            context=conversation_context[:500] if conversation_context else "",
            candidates=candidates,
            spirit_resonances=spirit_resonances,
            max_rounds=1,
        )
        if _debate_result.arbitration.confidence > confidence:
            confidence = _debate_result.arbitration.confidence
            emit_fn("step", {"phase": "多智能体辩论", "status": "done",
                "detail": f"🏟️ {len(_debate_result.positions)}方辩论完成, 共识={_debate_result.arbitration.consensus_level}, 置信度={confidence:.2f}"})
            if _debate_result.arbitration.key_insights:
                for insight in _debate_result.arbitration.key_insights[:3]:
                    truth_insights = (truth_insights + "\n" + insight) if truth_insights else insight
    except Exception as e:
        logger.debug(f"多智能体辩论跳过: {e}")
        alchemize_error_fn(e, context={"user_input": user_input[:50]}, phase="debate_arena")

    return _debate_result, confidence, truth_insights