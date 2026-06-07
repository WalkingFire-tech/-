import re
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from infrastructure.event_bus import bus

@dataclass
class Intent:
    type: str          # "chat", "code", "question", "memory", "feedback", "unknown"
    raw_text: str
    entities: dict

class IntentParser:
    """基于规则的意图解析器（不调用模型）"""
    
    def __init__(self):
        self.rules = {
            "code": re.compile(r"(写|生成|实现)(一段|一个|个)?代码", re.IGNORECASE),
            "question": re.compile(r"(什么是|为什么|怎么|如何|哪|谁|多少|解释)", re.IGNORECASE),
            "memory": re.compile(r"(记住|忘记|回忆|之前|刚才|聊过|说过|讲过|提到|我们.*什么)", re.IGNORECASE),
            "feedback": re.compile(r"^(\+1|-1|点赞|踩|好评|差评)", re.IGNORECASE),
        }
    
    def parse(self, user_input: str) -> Intent:
        intent_type = "chat"
        entities = {}
        
        for itype, pattern in self.rules.items():
            if pattern.search(user_input):
                intent_type = itype
                if itype == "feedback":
                    if "+1" in user_input or "点赞" in user_input:
                        entities["score"] = 1
                    elif "-1" in user_input or "踩" in user_input:
                        entities["score"] = -1
                break
        
        logger.info(f"解析意图: {intent_type} <- {user_input[:50]}")
        intent = Intent(type=intent_type, raw_text=user_input, entities=entities)
        bus.publish("intent_parsed", intent)
        return intent
