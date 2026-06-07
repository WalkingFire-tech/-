from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from infrastructure.experience_pool import ExperiencePool
from infrastructure.self_audit import SelfAudit
from infrastructure.code_executor import CodeExecutor
from loguru import logger
import sqlite3
import time
import re

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
                history.append(line.split("] ", 1)[-1])
        recent = history[-rounds*2:] if len(history) >= rounds*2 else history
        if not recent:
            return ""
        context = "以下是最近的对话历史（请基于这些历史回答当前问题）：\n"
        for entry in recent:
            context += entry + "\n"
        context += "\n当前问题："
        return context

    def _is_complex_task(self, intent: Intent) -> bool:
        if intent.type == "calculation":
            return True
        if len(intent.raw_text) > 100:
            return True
        if "Π" in intent.raw_text or "π" in intent.raw_text or "圆周率" in intent.raw_text:
            return True
        return False

    def _select_model(self, intent: Intent):
        intent_type = intent.type
        if self._is_complex_task(intent) and "remote_gpt4" in self.adapters:
            logger.info("复杂任务，尝试使用远程模型")
            return self.adapters["remote_gpt4"]
        if intent_type == "code":
            if "code_light" in self.adapters:
                return self.adapters["code_light"]
            if "deepcoder" in self.adapters:
                return self.adapters["deepcoder"]
            if "remote_gpt4" in self.adapters:
                return self.adapters["remote_gpt4"]
        if intent_type in ("chat", "question", "memory", "feedback"):
            if "mindchat" in self.adapters:
                return self.adapters["mindchat"]
            if "remote_gpt4" in self.adapters:
                return self.adapters["remote_gpt4"]
        if self.adapters:
            return next(iter(self.adapters.values()))
        raise RuntimeError("没有可用模型")

    def plan(self, intent: Intent):
        context = self._get_recent_context(rounds=3)

        if intent.type == "calculation":
            # 尝试使用代码执行（先尝试远程生成代码，失败则本地）
            self._execute_code_for_calculation(intent)
            return

        if intent.type == "code":
            base_prompt = f"请直接输出代码，不要多余解释。用户需求：{intent.raw_text}"
        elif intent.type == "question":
            base_prompt = f"请详细回答以下问题：{intent.raw_text}"
        elif intent.type == "memory":
            base_prompt = f"请根据以下对话历史直接回答用户的问题（如果历史中没有信息，请如实说不知道）。用户问题：{intent.raw_text}"
        else:
            base_prompt = intent.raw_text

        full_prompt = f"{context}\n{base_prompt}" if context else base_prompt
        model = self._select_model(intent)
        self.last_call_info = {"model": model.model_name, "task_type": intent.type, "plan": base_prompt, "duration": 0, "quality": 0}
        logger.info(f"规划器生成提示（意图：{intent.type}），选择模型 {model.model_name}")

        try:
            start = time.time()
            response = model.generate(full_prompt, task_type=intent.type)
            duration = time.time() - start
            self.last_call_info["duration"] = duration

            audit = SelfAudit.audit(response, intent.type)
            if audit["blocked"]:
                logger.warning(f"审核拦截: {audit['reason']}")
                response = f"⚠️ 系统检测到危险操作，已拦截输出。原因：{audit['reason']}"

            conn = sqlite3.connect("model_stats.db")
            cur = conn.execute("SELECT quality_score FROM model_performance ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            quality = row[0] if row else 0
            conn.close()
            self.last_call_info["quality"] = quality

            self.experience_pool.add_experience(
                intent_type=intent.type,
                raw_input=intent.raw_text,
                plan=base_prompt,
                model_name=model.model_name,
                quality_score=quality,
                user_feedback=0,
                success=quality >= 50,
                duration=duration
            )
            bus.publish("plan_executed", response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            bus.publish("plan_executed", f"抱歉，拓荒者遇到了问题：{e}")

    def _execute_code_for_calculation(self, intent: Intent):
        """执行代码生成+运行，支持远程和本地降级"""
        code_prompt = f"请生成一段Python代码来计算用户要求的结果，只输出代码，不要解释。用户需求：{intent.raw_text}"
        
        # 优先使用远程模型生成代码，如果不可用或失败则使用本地代码模型
        code_model = None
        if "remote_gpt4" in self.adapters:
            logger.info("尝试使用远程模型生成代码")
            code_model = self.adapters["remote_gpt4"]
        else:
            # 降级到本地代码模型
            code_model = self._select_model(Intent(type="code", raw_text=code_prompt, entities={}))
            logger.info(f"使用本地代码模型: {code_model.model_name}")
        
        try:
            code_response = code_model.generate(code_prompt, task_type="code")
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            # 如果远程失败，尝试本地模型
            if code_model.model_name.startswith("Remote") and "code_light" in self.adapters:
                logger.info("远程生成失败，降级到本地代码模型")
                code_model = self.adapters["code_light"]
                try:
                    code_response = code_model.generate(code_prompt, task_type="code")
                except Exception as e2:
                    bus.publish("plan_executed", f"代码生成完全失败：{e2}")
                    return
            else:
                bus.publish("plan_executed", f"代码生成失败：{e}")
                return
        
        # 提取代码块
        code_match = re.search(r'```python\n(.*?)```', code_response, re.DOTALL)
        if code_match:
            code = code_match.group(1)
        else:
            code = code_response.strip()
        
        # 执行代码
        exec_result = CodeExecutor.execute(code, timeout=15)
        if exec_result["success"]:
            result = exec_result["output"].strip()
            final_response = f"计算结果如下：\n{result}"
            quality = 80
        else:
            final_response = f"代码执行失败：{exec_result['error']}\n生成的代码：\n{code}"
            quality = 20
        
        # 记录经验
        self.last_call_info = {"model": code_model.model_name, "task_type": intent.type, "plan": code_prompt, "duration": 0, "quality": quality}
        self.experience_pool.add_experience(
            intent_type=intent.type,
            raw_input=intent.raw_text,
            plan=code_prompt,
            model_name=code_model.model_name,
            quality_score=quality,
            user_feedback=0,
            success=exec_result["success"],
            duration=0
        )
        bus.publish("plan_executed", final_response)
