"""
L2/L3认知学习提前消费 — 将认知旁路结果注入推理上下文
"""
import asyncio
from loguru import logger


async def early_consume_cognitive_learning(
    user_input: str,
    cbnr_context: dict,
    cognitive_bypass_future,
    cp,
    cognitive_perception: dict,
    truth_insights: str,
    inner_time_available: bool,
    alchemize_error_fn,
):
    """
    L2/L3认知学习提前消费 — 旁路优先，降级执行为次

    Returns:
        {
            "cognitive_learning": dict,
            "cognitive_integration": dict,
            "bypass_result_l2l3": object | None,
            "truth_insights": str,
            "events": list,
        }
    """
    _cognitive_learning = {}
    _cognitive_integration = {}
    _bypass_result_l2l3 = None
    events = []

    if cognitive_bypass_future:
        try:
            _bypass_result_l2l3 = await asyncio.wait_for(cognitive_bypass_future, timeout=6)
        except (asyncio.TimeoutError, Exception):
            pass

    if cp and cognitive_perception:
        cognitive_perception["cbnr_context"] = cbnr_context
        if _bypass_result_l2l3 and _bypass_result_l2l3.success:
            _cognitive_learning = _bypass_result_l2l3.learning or {}
            _cognitive_integration = _bypass_result_l2l3.integration or {}
            logger.debug("L2/L3: 使用认知旁路结果（提前消费）")
        else:
            try:
                _cognitive_learning = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: cp._learn(user_input, cognitive_perception)
                )
            except Exception as e:
                logger.warning(f"L2认知学习跳过: {e}")
                alchemize_error_fn(e, context={"user_input": user_input[:50]}, phase="L2_cognitive_learning_early")
            try:
                if _cognitive_learning:
                    _cognitive_integration = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: cp._integrate(_cognitive_learning)
                    )
            except Exception as e:
                logger.warning(f"L3认知整合跳过: {e}")
                alchemize_error_fn(e, context={"user_input": user_input[:50]}, phase="L3_cognitive_integration_early")

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
            logger.info(f"L2知识提前注入推理上下文: {_cognitive_learning.get('knowledge_gained', 0)}项, 置信度{_l2_conf:.0%}")
        if inner_time_available:
            try:
                from core.presence.inner_time import inner_time_engine, CognitiveEventType
                inner_time_engine.tick(CognitiveEventType.LEARN, intensity=0.7, description="cognitive_learning_early")
            except Exception:
                pass

    return {
        "cognitive_learning": _cognitive_learning,
        "cognitive_integration": _cognitive_integration,
        "bypass_result_l2l3": _bypass_result_l2l3,
        "truth_insights": truth_insights,
        "events": events,
    }


def emit_cognitive_learning_sse(cognitive_learning: dict, cognitive_integration: dict, emit_fn):
    """L2/L3 SSE展示 + SelfModel记录"""
    if cognitive_learning and cognitive_learning.get("knowledge_gained", 0) > 0:
        emit_fn("step", {"phase": "L2认知学习", "status": "done",
            "detail": f"获得{cognitive_learning.get('knowledge_gained', 0)}项知识, 置信度={cognitive_learning.get('confidence', 0.7):.0%}"})
        emit_fn("learning", {
            "summary": f"我从这次交互中获得了{cognitive_learning.get('knowledge_gained', 0)}项新认知",
            "confidence": float(cognitive_learning.get("confidence", 0.5)),
            "sources": cognitive_learning.get("sources", []),
        })
    if cognitive_integration and cognitive_integration.get("success"):
        core_know = cognitive_integration.get("core_knowledge", [])
        if core_know:
            emit_fn("step", {"phase": "L3认知整合", "status": "done",
                "detail": f"整合{len(core_know)}项核心知识"})