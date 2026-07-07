def generate_smart_reply(query: str, intent_type: str) -> str:
    """动态智能回复——不使用写死模板，而是返回标记让调用方走模型推理"""
    return "__NEED_DYNAMIC_REPLY__"


def fetch_rule(query: str, intent_type: str) -> dict:
    response = generate_smart_reply(query, intent_type)
    if response == "__NEED_DYNAMIC_REPLY__":
        return {"source": "规则推理", "response": "", "quality": 0}
    return {"source": "规则推理", "response": response, "quality": 30}