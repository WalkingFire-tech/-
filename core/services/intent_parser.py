import re
from dataclasses import dataclass
from loguru import logger
from infrastructure.event_bus import bus

@dataclass
class Intent:
    type: str
    raw_text: str
    entities: dict

class IntentParser:
    def __init__(self):
        self.rules = {
            "code": re.compile(r"代码|写.*代码|生成.*代码|编程|实现|算法|冒泡|快速|递归|函数", re.IGNORECASE),
            "question": re.compile(r"(什么是|为什么|怎么|如何|哪|谁|多少|解释)", re.IGNORECASE),
            "memory": re.compile(r"(记住|忘记|回忆|之前|刚才|聊过|说过)", re.IGNORECASE),
            "feedback": re.compile(r"^(\+1|-1|点赞|踩|好评|差评)", re.IGNORECASE),
            "calculation": re.compile(r"(Π|π|圆周率|前\s*\d+\s*位|输出.*数值|计算.*值|给出.*结果)", re.IGNORECASE),
        }

    def parse(self, user_input: str) -> Intent:
        intent_type = "chat"
        entities = {}
        for itype, pat in self.rules.items():
            if pat.search(user_input):
                intent_type = itype
                if itype == "feedback":
                    entities["score"] = 1 if ("+1" in user_input or "点赞" in user_input) else -1
                break
        logger.info(f"解析意图: {intent_type} <- {user_input[:50]}")
        intent = Intent(type=intent_type, raw_text=user_input, entities=entities)
        bus.publish("intent_parsed", intent)
        return intent
