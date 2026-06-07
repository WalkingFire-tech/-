from pathlib import Path
from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from loguru import logger

class Planner:
    def __init__(self, llm_adapter: LLMPort, context_lines: int = 6):
        self.llm = llm_adapter
        self.context_lines = context_lines  # 取最近 N 行对话（每行一条日志）

    def _get_recent_context(self) -> str:
        """从 campfire_log.txt 中提取最近几轮对话作为上下文"""
        log_file = Path("campfire_log.txt")
        if not log_file.exists():
            return ""

        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 过滤出包含 [时间] 用户: 或 [时间] 拓荒者: 的行
        dialogue = []
        for line in lines:
            line = line.strip()
            if line.startswith("[") and ("用户:" in line or "拓荒者:" in line):
                # 去掉时间戳，只保留角色和内容
                content = line.split("] ", 1)[-1]
                dialogue.append(content)

        # 取最近 self.context_lines 条
        recent = dialogue[-self.context_lines:] if len(dialogue) > self.context_lines else dialogue
        if not recent:
            return ""

        # 格式化为易读的上下文
        context_str = "以下是最近的对话历史：\n" + "\n".join(recent) + "\n\n请基于以上历史回答当前问题。"
        return context_str

    def plan(self, intent: Intent):
        # 获取短期记忆上下文
        context = self._get_recent_context()
        base_prompt = intent.raw_text

        # 根据意图定制 prompt
        if intent.type == "code":
            system_hint = "请直接输出代码，不要多余解释。"
        elif intent.type == "question":
            system_hint = "请详细回答以下问题。"
        elif intent.type == "memory":
            system_hint = "用户想回顾之前的对话或记住信息。请基于已知信息回答。"
        else:
            system_hint = ""

        # 组合最终 prompt：上下文 + 系统提示 + 用户问题
        if context:
            full_prompt = f"{context}\n{system_hint}\n{base_prompt}"
        else:
            full_prompt = f"{system_hint}\n{base_prompt}" if system_hint else base_prompt

        logger.info(f"规划器生成提示（意图：{intent.type}），调用 {self.llm.model_name}")
        try:
            response = self.llm.generate(full_prompt)
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")
