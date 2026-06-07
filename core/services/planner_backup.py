from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from loguru import logger

class Planner:
    """规划器：根据意图决定如何调用LLM"""
    
    def __init__(self, llm_adapter: LLMPort):
        self.llm = llm_adapter
    
    def plan(self, intent: Intent):
        """生成一个简单的计划：直接让 LLM 回答"""
        # 构建提示
        if intent.type == "code":
            prompt = f"请直接输出代码，不要多余解释。用户需求：{intent.raw_text}"
        elif intent.type == "question":
            prompt = f"请详细回答以下问题：{intent.raw_text}"
        else:
            prompt = intent.raw_text
        
        logger.info(f"规划器生成提示，准备调用 {self.llm.model_name}")
        
        # 实际调用 LLM（这里不处理异步，后面可以改进）
        try:
            response = self.llm.generate(prompt)
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")
