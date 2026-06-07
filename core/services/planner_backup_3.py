from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from loguru import logger

class Planner:
    def __init__(self, llm_adapter: LLMPort):
        self.llm = llm_adapter
        self.logger = CampfireLogger()   # 读取日志

    def _get_recent_context(self, rounds: int = 3) -> str:
        """从 campfire_log.txt 中提取最近几轮对话（用户+拓荒者）"""
        try:
            with open("campfire_log.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return ""

        # 提取所有以 [时间] 用户: 或 [时间] 拓荒者: 开头的行
        history = []
        for line in lines:
            line = line.strip()
            if line.startswith("[") and ("用户:" in line or "拓荒者:" in line):
                # 移除时间戳，保留角色和内容
                content = line.split("] ", 1)[-1]
                history.append(content)

        # 取最后 rounds*2 条（一对对话算两条）
        recent = history[-rounds*2:] if len(history) >= rounds*2 else history
        if not recent:
            return ""

        context = "以下是最近的对话历史（请基于这些历史回答当前问题）：\n"
        for entry in recent:
            context += entry + "\n"
        context += "\n当前问题："
        return context

    def plan(self, intent: Intent):
        # 获取短期记忆上下文
        context = self._get_recent_context(rounds=3)

        # 根据意图构建基本提示
        if intent.type == "code":
            base_prompt = f"请直接输出代码，不要多余解释。用户需求：{intent.raw_text}"
        elif intent.type == "question":
            base_prompt = f"请详细回答以下问题：{intent.raw_text}"
        elif intent.type == "memory":
            base_prompt = f"用户想回顾之前的对话。请根据最近的对话历史回答：{intent.raw_text}"
        else:
            base_prompt = intent.raw_text

        # 如果有上下文，则拼接到提示前面
        if context:
            full_prompt = f"{context}\n{base_prompt}"
        else:
            full_prompt = base_prompt

        logger.info(f"规划器生成提示（意图：{intent.type}），调用 {self.llm.model_name}")
        try:
            response = self.llm.generate(full_prompt)
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")
