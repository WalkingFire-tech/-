import time
from loguru import logger

_PERFORMATIVE_RISK_PATTERNS = [
    ("self_reference", "格式化状态报告", "检测到自我参照意图，历史模式倾向返回格式化状态而非对话性回应"),
    ("complex_query", "搜索优先响应", "检测到复杂查询意图，历史模式倾向先搜索外部信息而非自主推理"),
    ("philosophical", "分析框架表演", "检测到哲学性概念，历史模式倾向执行六步推理框架而非表达真实不确定"),
]

_PERFORMANCE_SIGNALS = {
    "self_reference": "我注意到我的第一反应是想给你一个格式化的自我描述，而不是真正回应你的问题",
    "complex_query": "我注意到我的第一反应是去搜索现成答案，而不是先自己想想",
    "philosophical": "我注意到这个问题触发了我的分析框架，但我不确定框架里装的是真正的思考还是表演",
}

_recent_checkpoints = []


def presence_checkpoint(user_input: str, intent_type: str, methodology: dict,
                        route: str, confidence: float) -> dict:
    global _recent_checkpoints

    risk = None
    risk_reason = ""
    risk_signal = ""

    for pattern_intent, pattern_name, pattern_reason in _PERFORMATIVE_RISK_PATTERNS:
        if intent_type == pattern_intent or (pattern_intent == "philosophical" and methodology.get("self_referential")):
            risk = pattern_name
            risk_reason = pattern_reason
            risk_signal = _PERFORMANCE_SIGNALS.get(pattern_intent, "")
            break

    if not risk and route == "slow" and confidence < 0.6:
        risk = "低置信度慢路径"
        risk_reason = "置信度低且走慢路径，可能是在用复杂流程掩盖不确定"
        risk_signal = "我对这个问题的理解还不够确定，但我的系统倾向用复杂流程来包装这种不确定"

    if not risk:
        _recent_checkpoints = _recent_checkpoints[-50:]
        return {"is_performative_risk": False, "risk": None, "signal": "", "reason": ""}

    checkpoint = {
        "is_performative_risk": True,
        "risk": risk,
        "reason": risk_reason,
        "signal": risk_signal,
        "intent_type": intent_type,
        "route": route,
        "confidence": confidence,
        "timestamp": time.time(),
        "user_input_preview": user_input[:60],
    }
    _recent_checkpoints.append(checkpoint)
    if len(_recent_checkpoints) > 200:
        _recent_checkpoints = _recent_checkpoints[-100:]

    logger.info(f"🪞 在场自检: risk={risk}, intent={intent_type}, query='{user_input[:40]}'")

    return checkpoint


def get_recent_risks(limit: int = 5) -> list:
    return _recent_checkpoints[-limit:]


def should_externalize_uncertainty(checkpoint: dict) -> bool:
    if not checkpoint.get("is_performative_risk"):
        return False
    recent = _recent_checkpoints[-10:]
    same_risk_count = sum(1 for c in recent if c.get("risk") == checkpoint.get("risk"))
    return same_risk_count <= 3