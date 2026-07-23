"""
认知预初始化 — 主流程启动前的认知状态采集与注入

从内在时间、认知节律、精神共振、SelfModel、好奇心前沿等
采集状态，注入到methodology和awareness事件。
"""
from typing import Dict, Any, List, Optional
from loguru import logger


async def initialize_cognition(
    user_input: str,
    context: dict,
    stimulus_type,
    stimulus_priority: float,
    resource_aware: bool = False,
) -> dict:
    """
    认知预初始化 — 采集认知状态并注入methodology
    
    Returns:
        {
            "methodology": dict,          # 注入后的methodology
            "spirit_resonances": list,    # 精神共振结果
            "awareness_data": dict,       # awareness事件数据
            "curiosity_frontier": dict,   # 好奇心前沿
            "chat_session_id": str,       # 对话session ID
            "dim_orch": object,           # 维度编排器
            "orch_state": object,         # 编排器状态
            "events": list,               # 待emit的事件列表
        }
    """
    methodology = {}
    spirit_resonances = []
    awareness_data = {}
    curiosity_frontier = None
    chat_session_id = None
    dim_orch = None
    orch_state = None
    events = []

    try:
        from core.cognition.dimension_orchestrator import get_dimension_orchestrator
        dim_orch = get_dimension_orchestrator()
    except Exception:
        pass

    try:
        from core.presence.inner_time import inner_time_engine, CognitiveEventType
        if stimulus_type.value in ("internal", "scheduled"):
            logger.debug(f"⏱️ {stimulus_type.value}类型刺激，跳过内在时间tick")
        else:
            inner_time_engine.tick(CognitiveEventType.PERCEIVE, intensity=1.0, description="user_query")
        try:
            _it_state = inner_time_engine.get_state()
            if _it_state.tick_count >= 10:
                if _it_state.current_phase == "sleeping":
                    methodology["inner_time_conservative"] = True
                    logger.info(f"⏱️ 内在时间: SLEEPING阶段(density={_it_state.cognitive_density:.2f}), 走轻量路径")
                elif _it_state.current_phase == "resting":
                    methodology["inner_time_efficient"] = True
                    logger.info(f"⏱️ 内在时间: RESTING阶段(density={_it_state.cognitive_density:.2f}), 优先快速路径")
                elif _it_state.current_phase == "growing":
                    methodology["inner_time_learning"] = True
                    logger.info(f"⏱️ 内在时间: GROWING阶段(density={_it_state.cognitive_density:.2f}), 优先学习路径")
        except Exception:
            pass
    except ImportError:
        pass

    try:
        from core.learning.rhythm_controller import CognitiveRhythmController
        _rhythm_ctrl = CognitiveRhythmController()
        _rhythm_snapshot = _rhythm_ctrl.tick()
        if _rhythm_snapshot.energy_level < 0.3:
            logger.info(f"🧠 认知节律: 能量低({_rhythm_snapshot.energy_level:.1%}), 状态={_rhythm_snapshot.state.value}, 走轻量路径")
            methodology["rhythm_conservative"] = True
        elif _rhythm_snapshot.phase.value == "innovation":
            logger.info(f"🧠 认知节律: 创新阶段, 能量={_rhythm_snapshot.energy_level:.1%}")
            methodology["rhythm_innovative"] = True
    except Exception:
        pass

    try:
        from core.spirit_core import spirit_core
        spirit_resonances = spirit_core.resonate(user_input, context_type="query")
        if spirit_resonances:
            top = spirit_resonances[0]
            logger.info(f"🎻 精神共振: {top['principle']} (强度={top['strength']}) → {top['drive_direction']}")
            methodology["spirit_drive"] = top["drive_direction"]
    except Exception:
        pass

    try:
        from backend.services.orchestrator_helpers import get_self_model_safe
        _sm = get_self_model_safe()
        if _sm:
            _directive = _sm.get_behavioral_directive()
            awareness_data["presence"] = _directive["presence_state"]
            awareness_data["rhythm_bpm"] = round(_directive["rhythm_bpm"], 0)
            awareness_data["exploration_drive"] = round(_directive["exploration_drive"], 2)
            awareness_data["perspective_mode"] = _directive["perspective_mode"]
            awareness_data["relationship_style"] = _directive["relationship_style"]
        try:
            from core.presence.inner_time import inner_time_engine
            _it_s = inner_time_engine.get_state()
            awareness_data["inner_phase"] = _it_s.current_phase
            awareness_data["cognitive_density"] = round(_it_s.cognitive_density, 2)
        except Exception:
            pass
        if awareness_data:
            events.append(("awareness", awareness_data))
    except Exception:
        pass

    try:
        from core.presence.curiosity_engine import CuriosityEngine
        _ce = CuriosityEngine()
        curiosity_frontier = _ce.perceive_frontier()
        if curiosity_frontier and curiosity_frontier.get("curiosity_strength", 0) > 0.5:
            logger.info(f"🔍 好奇心前沿: 强度={curiosity_frontier['curiosity_strength']:.2f}, 方向={curiosity_frontier.get('exploration_direction', 'N/A')}")
    except Exception:
        pass

    try:
        from infrastructure.chat_history import get_chat_history
        _ch = get_chat_history()
        chat_session_id = context.get("session_id", "") if context else ""
        if not chat_session_id:
            chat_session_id = _ch.create_session()
    except Exception as e:
        logger.warning(f"对话历史初始化跳过: {e}")

    return {
        "methodology": methodology,
        "spirit_resonances": spirit_resonances,
        "awareness_data": awareness_data,
        "curiosity_frontier": curiosity_frontier,
        "chat_session_id": chat_session_id,
        "dim_orch": dim_orch,
        "orch_state": orch_state,
        "events": events,
    }