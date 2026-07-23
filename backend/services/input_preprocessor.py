from loguru import logger


def get_intent_domain_keywords(intent_type, user_input):
    kw = {}
    if intent_type == "hardware":
        kw.update({"system": 0.9, "cmd": 0.8, "powershell": 0.8, "command": 0.8, "process": 0.6, "resource": 0.7, "fix": 0.7, "diagnose": 0.7, "self": 0.5, "manage": 0.6, "gpu": 0.7, "memory": 0.6, "cpu": 0.6})
    elif intent_type == "map":
        kw.update({"map": 1.0, "coordinate": 0.9, "location": 0.9, "navigate": 0.8, "gps": 0.8, "marker": 0.7, "latitude": 0.9, "longitude": 0.9})
    elif intent_type == "weather":
        kw.update({"weather": 1.0, "temperature": 0.9, "forecast": 0.8, "rain": 0.8, "wind": 0.6, "humidity": 0.7})
    elif intent_type == "simple_query":
        kw.update({"是什么": 0.6, "为什么": 0.6, "怎么": 0.6, "如何": 0.6, "可以": 0.5, "会": 0.4, "能": 0.4, "吗": 0.3, "呢": 0.3, "什么": 0.5, "多少": 0.5, "哪个": 0.5, "是否": 0.5, "原因": 0.5, "方法": 0.5})
    _text = (user_input or "")[:200]
    for word in _text.replace("?", " ").replace("？", " ").replace(",", " ").split():
        w = word.strip().lower()
        if len(w) >= 2:
            kw[w] = kw.get(w, 0.25)
    for i in range(0, min(len(_text), 20), 2):
        _bigram = _text[i:i+2].strip()
        if len(_bigram) == 2 and any('\u4e00' <= c <= '\u9fff' for c in _bigram):
            kw[_bigram] = kw.get(_bigram, 0.3)
    return kw


def compute_relevance(text, domain_keywords):
    if not text or not domain_keywords:
        return 0.5
    tl = (text or "").lower()[:500]
    score, matched = 0.0, 0
    for kw, w in domain_keywords.items():
        if kw.lower() in tl:
            score += w
            matched += 1
    if matched == 0:
        return 0.05
    return min(score / max(len(domain_keywords), 1) * (1 + matched * 0.1), 1.0)


def feature_enabled(flag_name: str, default: bool = True) -> bool:
    try:
        from infrastructure.config_manager import config_manager
        flags = config_manager.get("feature_flags", {})
        return flags.get(flag_name, default)
    except Exception:
        return default


def build_fallback_dispatch(raw_intent: str, raw_conf: float) -> dict:
    intent_type = raw_intent
    route = "fast" if raw_intent in ("greeting", "confirmation") else "slow"
    confidence = raw_conf
    return {"intent_type": intent_type, "route": route, "confidence": confidence, "field_context": {}, "execution_plan": {"tasks": []}}


def solve_history_query(history: list, user_input: str) -> str:
    if not history:
        return ""
    for msg in reversed(history[-6:]):
        if msg.get("role") == "assistant" and msg.get("content"):
            content = msg["content"]
            if len(content) > 30 and len(content) < 2000:
                return content
    return ""


def generate_smart_reply(query: str, intent_type: str) -> str:
    return "__NEED_DYNAMIC_REPLY__"


def generate_meaningful_fallback(query: str, attempts: list) -> str:
    return "__NEED_DYNAMIC_FALLBACK__"