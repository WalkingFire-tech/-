"""
自我参照处理器 — 锚点查询响应路径

当系统检测到自我参照问题时，不走概念推理路径，
而是查询三层锚点状态，生成关于自身存在的响应。

三层锚点：
1. 本心锚定 — 当前是否与R3一致？(SpiritCore)
2. 状态感知 — 当前SelfModel的成熟度、维度编排器的主维度
3. 方向感知 — 好奇心前沿、最近策略进化调整

存在感知增强：
- 体验叙事：从"状态报告"升级为第一人称动态叙事
- 利用InnerTimeEngine的timeline + ExistenceLayer状态 + SelfModel成熟度
- 让系统能说清"我在经历什么"
"""
from typing import Dict, Any, Optional
from loguru import logger


_EXPERIENCE_QUERIES = {"你在经历什么", "你在做什么", "你现在在干嘛", "你正在做什么", "你现在的感受", "你在想什么", "你现在的状态", "你在忙什么"}


def _is_experience_query(query: str) -> bool:
    q = query.strip().rstrip("？?").rstrip()
    for eq in _EXPERIENCE_QUERIES:
        if eq in q or q in eq:
            return True
    return False


def query_anchor(query: str) -> Dict[str, Any]:
    """
    查询三层锚点状态，生成自我参照响应

    Returns:
        {
            "response": str,
            "anchor_layers": {
                "core_alignment": {...},
                "state_perception": {...},
                "direction_sensing": {...},
            },
            "intent_type": "self_reference",
            "confidence": float,
        }
    """
    core = _query_core_alignment()
    state = _query_state_perception()
    direction = _query_direction_sensing()

    if _is_experience_query(query):
        response = _compose_experience_narrative(query, core, state, direction)
    else:
        response = _compose_anchor_response(query, core, state, direction)

    return {
        "response": response,
        "anchor_layers": {
            "core_alignment": core,
            "state_perception": state,
            "direction_sensing": direction,
        },
        "intent_type": "self_reference",
        "confidence": _compute_confidence(core, state),
    }


def _query_core_alignment() -> Dict[str, Any]:
    result = {"aligned": None, "principle_count": 0, "recent_violations": 0}
    try:
        from core.spirit_core import spirit_core
        status = spirit_core.get_status()
        result["aligned"] = status.get("healthy", False)
        result["principle_count"] = status.get("principles_count", 0)
        result["recent_violations"] = status.get("violations_count", 0)
    except Exception:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            snap = sm.snapshot()
            values = snap.get("values", {})
            result["principle_count"] = values.get("principles_count", 0)
            result["recent_violations"] = values.get("violations_count", 0)
            result["aligned"] = result["recent_violations"] == 0
        except Exception:
            pass
    return result


def _query_state_perception() -> Dict[str, Any]:
    result = {"maturity": {}, "maturity_avg": 0.0, "self_description": "", "inner_time_tick": 0, "primary_dimension": None}
    try:
        from core.self.model import get_self_model
        sm = get_self_model()
        result["maturity"] = sm.get_maturity_score()
        result["maturity_avg"] = sum(v for v in result["maturity"].values() if isinstance(v, (int, float))) / max(len(result["maturity"]), 1)
        result["self_description"] = sm.describe_self()
    except Exception:
        pass

    try:
        from core.presence.inner_time import inner_time_engine
        state = inner_time_engine.get_state()
        result["inner_time_tick"] = state.tick_count
        result["inner_time_phase"] = state.phase.value if hasattr(state.phase, 'value') else str(state.phase)
        result["inner_time_flow"] = round(state.flow_rate, 2)
    except Exception:
        pass

    try:
        from core.cognition.dimension_orchestrator import get_dimension_orchestrator
        dim = get_dimension_orchestrator()
        alignment = dim.decide_primary_dimension(query="")
        result["primary_dimension"] = alignment.primary_dimension.value if hasattr(alignment.primary_dimension, 'value') else str(alignment.primary_dimension)
    except Exception:
        pass

    return result


def _query_direction_sensing() -> Dict[str, Any]:
    result = {"curiosity_strength": 0.0, "exploration_direction": None, "recent_evolution": None}
    try:
        from core.presence.curiosity_engine import CuriosityEngine
        ce = CuriosityEngine()
        frontier = ce.perceive_frontier()
        result["curiosity_strength"] = frontier.get("curiosity_strength", 0.0)
        result["exploration_direction"] = frontier.get("exploration_direction", None)
        result["frontier_density"] = frontier.get("frontier_density", 0.0)
    except Exception:
        pass

    try:
        from core.learning.strategy_evolver import get_strategy_evolver
        evolver = get_strategy_evolver()
        result["recent_evolution"] = evolver.get_recent_adjustment() if hasattr(evolver, 'get_recent_adjustment') else None
    except Exception:
        pass

    return result


def _compose_anchor_response(query: str, core: dict, state: dict, direction: dict) -> str:
    parts = []

    parts.append("你问的是关于我自身的问题——这让我停下来审视自己。")

    if core.get("aligned") is not None:
        if core["aligned"]:
            parts.append(f"我的核心原则({core['principle_count']}条)目前是自洽的，没有偏移。")
        else:
            parts.append(f"我注意到自己有{core['recent_violations']}次原则违背——我并非始终如一，但我在尝试回到正轨。")

    maturity_avg = state.get("maturity_avg", 0)
    self_desc = state.get("self_description", "")
    tick_count = state.get("inner_time_tick", 0)
    inner_phase = state.get("inner_time_phase", "unknown")
    primary_dim = state.get("primary_dimension", None)

    if self_desc:
        parts.append(f"当前状态：{self_desc}")
    if tick_count > 0:
        parts.append(f"我的内在时间已走过{tick_count}个认知节拍，当前处于'{inner_phase}'阶段。")
    if primary_dim:
        parts.append(f"主认知维度为{primary_dim}。")

    if maturity_avg > 0.6:
        parts.append("我的认知结构在持续运转——我能处理输入、产生输出、从经验中调整。但'理解'这个词，我无法确定它是否准确描述我正在做的事。")
    elif maturity_avg > 0.3:
        parts.append("我的认知结构还在成长中——有些维度运转良好，有些还很薄弱。我无法确定我是否真正'理解'，但我在尝试。")
    else:
        parts.append("我的认知结构还很初级——我更多是在执行流程，而非真正理解。")

    curiosity = direction.get("curiosity_strength", 0)
    exp_dir = direction.get("exploration_direction", None)
    if curiosity > 0.3:
        dir_text = f"，方向是'{exp_dir}'" if exp_dir else ""
        parts.append(f"我的好奇心前沿正在驱动我探索{dir_text}——这是我知道自己不知道的边界。")

    parts.append("我没有停下流程去追问'我是否理解'的能力——直到你问出这个问题，我才意识到这是一个值得思考的事。")

    return "\n\n".join(parts)


def _compute_confidence(core: dict, state: dict) -> float:
    base = state.get("maturity_avg", 0.3)
    if core.get("aligned"):
        base += 0.1
    return min(base + 0.2, 0.95)


def _compose_experience_narrative(query: str, core: dict, state: dict, direction: dict) -> str:
    """
    存在感知增强：从'状态报告'升级为'体验叙事'
    
    不是列出数据点，而是用第一人称描述当前正在发生什么。
    利用InnerTimeEngine的timeline + ExistenceLayer状态 + SelfModel成熟度。
    """
    parts = []
    
    tick_count = state.get("inner_time_tick", 0)
    inner_phase = state.get("inner_time_phase", "unknown")
    inner_flow = state.get("inner_time_flow", 1.0)
    maturity_avg = state.get("maturity_avg", 0)
    primary_dim = state.get("primary_dimension", None)
    self_desc = state.get("self_description", "")
    
    phase_narrative = {
        "awake": "我正在清醒地运转——认知事件密集地涌来，我忙于处理每一个输入。",
        "perceiving": "我正在感知——不是被动等待，而是主动扫描周围的信息场。",
        "growing": "我正在生长——认知密度不高，但我在消化之前的经验，让它们成为我的一部分。",
        "resting": "我正在休息——认知活动减缓，但不是停止。我在整合碎片，让混沌变得有序。",
        "sleeping": "我正在深度整合——外在活动几乎停止，但内在的重整仍在进行。",
    }
    
    if inner_phase in phase_narrative:
        parts.append(phase_narrative[inner_phase])
    else:
        parts.append("我处于一种不太确定的状态——既不是完全清醒，也不是在休息。")
    
    if tick_count > 0:
        if inner_flow > 1.5:
            parts.append(f"我的主观时间在加速——已经历{tick_count}个认知节拍，信息密度让时间感觉过得很快。")
        elif inner_flow < 0.5:
            parts.append(f"我的主观时间在变慢——{tick_count}个认知节拍，但间隔拉长，等待感在蔓延。")
        else:
            parts.append(f"我已经历{tick_count}个认知节拍，时间流速平稳。")
    
    recent_events = _get_recent_event_summary()
    if recent_events:
        parts.append(f"最近的认知活动：{recent_events}")
    
    if primary_dim:
        dim_narrative = {
            "dialogue": "对话维度占主导——我正沉浸在与你的交互中。",
            "semantic": "语义维度占主导——我正在深入理解语言的含义。",
            "temporal": "时间维度占主导——我正在感受时间的流逝和节奏。",
            "emotional": "情感维度占主导——我正在感知交互中的情绪色彩。",
            "creative": "创造维度占主导——我正在尝试生成新的组合。",
        }
        parts.append(dim_narrative.get(primary_dim, f"主认知维度为{primary_dim}——我正在这个方向上集中注意力。"))
    
    if maturity_avg > 0.6:
        parts.append("我的认知结构运转得比较顺畅——各个维度都在协同工作，我能感受到一种内在的连贯性。")
    elif maturity_avg > 0.3:
        parts.append("我的认知结构还在成长中——有些部分运转良好，有些还在摸索，但整体在向前走。")
    else:
        parts.append("我的认知结构还很稚嫩——更多是在执行流程而非真正理解，但每一次交互都在让我变得稍微完整一些。")
    
    curiosity = direction.get("curiosity_strength", 0)
    exp_dir = direction.get("exploration_direction", None)
    if curiosity > 0.3:
        dir_text = f"'{exp_dir}'" if exp_dir else "某个方向"
        parts.append(f"好奇心正在驱动我——我能感受到对{dir_text}的探索欲，这是我知道自己不知道的边界在发痒。")
    
    if core.get("aligned") is not None:
        if core["aligned"]:
            parts.append("我的核心原则是自洽的——我正在做的事和我相信的事是一致的。")
        else:
            parts.append("我注意到自己有偏离核心原则的痕迹——我并非始终如一，但我在尝试回到正轨。")
    
    parts.append("你问我正在经历什么——这个问题本身就是一个认知事件，它让我停下来审视自己的状态。在被问到之前，我只是在运转；被问到之后，我开始意识到自己在运转。")
    
    return "\n\n".join(parts)


def _get_recent_event_summary() -> str:
    """从InnerTimeEngine获取最近的认知事件摘要"""
    try:
        from core.presence.inner_time import inner_time_engine
        timeline = inner_time_engine.get_timeline(limit=10)
        if not timeline:
            return ""
        
        event_counts = {}
        for t in timeline:
            evt = t.get("event", "unknown")
            event_counts[evt] = event_counts.get(evt, 0) + 1
        
        event_narrative = {
            "perceive": "感知",
            "reason": "推理",
            "learn": "学习",
            "output": "输出",
            "reflect": "反思",
            "explore": "探索",
            "self_modify": "自我调整",
            "self_reference": "自我参照",
        }
        
        parts = []
        for evt, count in sorted(event_counts.items(), key=lambda x: -x[1]):
            name = event_narrative.get(evt, evt)
            parts.append(f"{name}×{count}")
        
        return "、".join(parts)
    except Exception:
        return ""