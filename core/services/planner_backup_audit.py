from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from infrastructure.experience_pool import ExperiencePool
from loguru import logger

class Planner:
    def __init__(self, adapters: dict):
        self.adapters = adapters
        self.logger = CampfireLogger()
        self.stats = ModelStats()
        self.experience_pool = ExperiencePool()
        self.last_call_info = {"model": None, "task_type": None, "plan": None, "duration": 0.0, "quality": 0}

    def get_last_call_info(self):
        return self.last_call_info

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
        best_model_name = self.stats.get_best_model_for_task(intent_type, speed_weight=0.3, quality_weight=0.7)
        if best_model_name and best_model_name in self.adapters:
            logger.info(f"统计库推荐模型: {best_model_name} for {intent_type}")
            return self.adapters[best_model_name]

        if intent_type == "code":
            if "code_light" in self.adapters:
                return self.adapters["code_light"]
            elif "deepcoder" in self.adapters:
                return self.adapters["deepcoder"]
        elif intent_type in ("chat", "question", "memory", "feedback"):
            if "mindchat" in self.adapters:
                return self.adapters["mindchat"]

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
        self.last_call_info["model"] = model.model_name
        self.last_call_info["task_type"] = intent.type
        self.last_call_info["plan"] = base_prompt  # 简化计划存储
        logger.info(f"规划器生成提示（意图：{intent.type}），选择模型 {model.model_name}")

        try:
            import time
            start_time = time.time()
            response = model.generate(full_prompt, task_type=intent.type)
            duration = time.time() - start_time
            self.last_call_info["duration"] = duration
            # 从记录中获取质量评分（已在 adapter 中存储）
            # 这里需要从统计库最新记录获取质量，暂用默认值
            quality = 0
            # 简化：直接从 model.stats 获取最近一条记录的质量
            conn = sqlite3.connect("model_stats.db")
            cur = conn.execute("SELECT quality_score FROM model_performance ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                quality = row[0] or 0
            conn.close()
            self.last_call_info["quality"] = quality

            # 存储经验（暂时将成功标记为 quality>=50）
            success = quality >= 50
            self.experience_pool.add_experience(
                intent_type=intent.type,
                raw_input=intent.raw_text,
                plan=base_prompt,
                model_name=model.model_name,
                quality_score=quality,
                user_feedback=0,  # 初始0，后面反馈会更新
                success=success,
                duration=duration
            )
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")
