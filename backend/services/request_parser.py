"""
请求解析器 — Stimulus解析 + 端口初始化
"""
from loguru import logger


def parse_stimulus(user_input, context: dict = None):
    """
    解析输入为CognitiveStimulus — 支持str和CognitiveStimulus双入口

    Returns:
        {
            "stimulus": CognitiveStimulus,
            "user_input": str,
            "context": dict,
            "stimulus_type": StimulusType,
            "stimulus_priority": float,
        }
    """
    from core.ports import CognitiveStimulus, StimulusType

    if isinstance(user_input, str):
        stimulus = CognitiveStimulus.from_user_message(user_input, context=context)
    elif hasattr(user_input, 'content') and hasattr(user_input, 'stimulus_type'):
        stimulus = user_input
    else:
        stimulus = CognitiveStimulus.from_user_message(str(user_input), context=context)

    _user_input = stimulus.content
    if context is None:
        context = stimulus.context
    context.setdefault('_stimulus_type', stimulus.stimulus_type.value)
    context.setdefault('_stimulus_priority', stimulus.priority)
    if stimulus.session_id:
        context.setdefault('_session_id', stimulus.session_id)

    return {
        "stimulus": stimulus,
        "user_input": _user_input,
        "context": context,
        "stimulus_type": stimulus.stimulus_type,
        "stimulus_priority": stimulus.priority,
    }


def initialize_ports(context: dict) -> dict:
    """
    初始化端口适配器 — 注入到context._ports

    Returns:
        _ports dict
    """
    _ports = {}
    try:
        from core.ports.adapters import (
            get_fact_store_port, get_vector_store_port, get_config_port,
            get_knowledge_port, get_experience_port, get_storage_port,
        )
        _ports["fact_store"] = get_fact_store_port()
        _ports["vector_store"] = get_vector_store_port()
        _ports["config"] = get_config_port()
        _ports["knowledge"] = get_knowledge_port()
        _ports["experience"] = get_experience_port()
        _ports["storage"] = get_storage_port()
        context.setdefault("_ports", _ports)
    except Exception:
        pass
    return _ports