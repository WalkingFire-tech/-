"""
信号集成 - 为各层提供提交信号的便捷接口
"""

from core.presence.gap_growth import get_gap_growth_engine


def submit_intent_pattern(intent: str, source: str = "L1", context: dict = None) -> str:
    """提交意图模式信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="intent_pattern",
        content=intent,
        source=source,
        context=context or {},
        priority="medium"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("intent_pattern", intent, source, context or {})
    except Exception:
        pass
    return _result


def submit_emotion_pattern(emotion: str, source: str = "L1", context: dict = None) -> str:
    """提交情绪模式信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="emotion_pattern",
        content=emotion,
        source=source,
        context=context or {},
        priority="medium"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("emotion_pattern", emotion, source, context or {})
    except Exception:
        pass
    return _result


def submit_error_pattern(error: str, source: str = "L4", context: dict = None) -> str:
    """提交错误模式信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="error_pattern",
        content=error,
        source=source,
        context=context or {},
        priority="high"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("error_pattern", error, source, context or {})
    except Exception:
        pass
    return _result


def submit_success_pattern(success: str, source: str = "L4", context: dict = None) -> str:
    """提交成功模式信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="success_pattern",
        content=success,
        source=source,
        context=context or {},
        priority="medium"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("success_pattern", success, source, context or {})
    except Exception:
        pass
    return _result


def submit_knowledge_gap(gap: str, source: str = "L2", context: dict = None) -> str:
    """提交知识缺口信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="knowledge_gap",
        content=gap,
        source=source,
        context=context or {},
        priority="medium"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("knowledge_gap", gap, source, context or {})
    except Exception:
        pass
    return _result


def submit_user_preference(preference: str, value: str, source: str = "L1", context: dict = None) -> str:
    """提交用户偏好信号"""
    engine = get_gap_growth_engine()
    ctx = context or {}
    ctx["value"] = value
    _result = engine.submit_signal(
        signal_type="user_preference",
        content=preference,
        source=source,
        context=ctx,
        priority="medium"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("user_preference", preference, source, ctx)
    except Exception:
        pass
    return _result


def submit_tool_need(need: str, source: str = "L3", context: dict = None) -> str:
    """提交工具需求信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="tool_need",
        content=need,
        source=source,
        context=context or {},
        priority="high"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("tool_need", need, source, context or {})
    except Exception:
        pass
    return _result


def submit_skill_opportunity(opportunity: str, source: str = "L5", context: dict = None) -> str:
    """提交技能机会信号"""
    engine = get_gap_growth_engine()
    _result = engine.submit_signal(
        signal_type="skill_opportunity",
        content=opportunity,
        source=source,
        context=context or {},
        priority="medium"
    )
    try:
        from infrastructure.feedback_store import FeedbackStore
        _fs = FeedbackStore()
        _fs.store("skill_opportunity", opportunity, source, context or {})
    except Exception:
        pass
    return _result