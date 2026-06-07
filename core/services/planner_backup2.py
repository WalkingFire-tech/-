from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from loguru import logger

class Planner:
    def __init__(self, llm_adapter: LLMPort):
        self.llm = llm_adapter

    def plan(self, intent: Intent):
        # 根据意图定制 prompt
        if intent.type == "code":
            prompt = f"请直接输出代码，不要多余解释。用户需求：{intent.raw_text}"
        elif intent.type == "question":
            prompt = f"请详细回答以下问题：{intent.raw_text}"
        elif intent.type == "memory":
            prompt = f"用户想回顾之前的对话或记住信息。请基于已知信息回答：{intent.raw_text}"
        else:
            prompt = intent.raw_text   # chat 或其他

        logger.info(f"规划器生成提示（意图：{intent.type}），调用 {self.llm.model_name}")
        try:
            response = self.llm.generate(prompt)
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")
