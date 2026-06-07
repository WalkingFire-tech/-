from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from loguru import logger

class Planner:
    def __init__(self, adapters: dict):
        self.adapters = adapters
        self.logger = CampfireLogger()
        self.stats = ModelStats()

    def _get_recent_context(self, rounds: int = 3) -> str:
        try:
            with open("campfire_log.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return ""

        history = []
        for line in lines:
            line = line.strip()
            if line.startswith("[") and ("用户:" in line or "拓荒者:" in line):
                content = line.split("] ", 1)[-1]
                history.append(content)

        recent = history[-rounds*2:] if len(history) >= rounds*2 else history
        if not recent:
            return ""

        context = "以下是最近的对话历史（请基于这些历史回答当前问题）：\n"
        for entry in recent:
            context += entry + "\n"
        context += "\n当前问题："
        return context

    def _select_model(self, intent_type: str):
        # 优先使用统计库选择最佳模型
        best_model_name = self.stats.get_best_model_for_task(intent_type, speed_weight=0.3, quality_weight=0.7)
        if best_model_name and best_model_name in self.adapters:
            logger.info(f"统计库推荐模型: {best_model_name} for {intent_type}")
            return self.adapters[best_model_name]

        # 降级：硬编码规则（统计库样本不足时）
        if intent_type == "code":
            if "code_light" in self.adapters:
                return self.adapters["code_light"]
            elif "deepcoder" in self.adapters:
                return self.adapters["deepcoder"]
        elif intent_type in ("chat", "question", "memory", "feedback"):
            if "mindchat" in self.adapters:
                return self.adapters["mindchat"]

        # 最终降级
        if self.adapters:
            return next(iter(self.adapters.values()))
        else:
            raise RuntimeError("没有可用的模型适配器")

    def plan(self, intent: Intent):
        context = self._get_recent_context(rounds=3)

        if intent.type == "code":
            base_prompt = f"请直接输出代码，不要多余解释。用户需求：{intent.raw_text}"
        elif intent.type == "question":
            base_prompt = f"请详细回答以下问题：{intent.raw_text}"
        elif intent.type == "memory":
            base_prompt = f"请根据以下对话历史直接回答用户的问题（如果历史中没有信息，请如实说不知道）。用户问题：{intent.raw_text}"
        else:
            base_prompt = intent.raw_text

        full_prompt = f"{context}\n{base_prompt}" if context else base_prompt

        model = self._select_model(intent.type)
        logger.info(f"规划器生成提示（意图：{intent.type}），选择模型 {model.model_name}")

        try:
            response = model.generate(full_prompt, task_type=intent.type)
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")
