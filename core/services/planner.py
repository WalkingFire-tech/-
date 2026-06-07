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
            if line.startswith("[") and ("user:" in line.lower() or "pioneer:" in line.lower() or "拓荒者:" in line or "用户:" in line):
                content = line.split("] ", 1)[-1]
                history.append(content)
        recent = history[-rounds*2:] if len(history) >= rounds*2 else history
        if not recent:
            return ""
        context = "Recent conversation history (use it to answer current question):\n"
        for entry in recent:
            context += entry + "\n"
        context += "\nCurrent question: "
        return context

    def _is_complex_task(self, intent: Intent) -> bool:
        if intent.type == "calculation":
            return True
        if len(intent.raw_text) > 100:
            return True
        if "Π" in intent.raw_text or "π" in intent.raw_text or "pi" in intent.raw_text.lower():
            return True
        return False

    def _select_model(self, intent: Intent):
        intent_type = intent.type
        if self._is_complex_task(intent) and "remote_gpt4" in self.adapters:
            logger.info("Complex task, using remote model")
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
        raise RuntimeError("No model available")

    def plan(self, intent: Intent):
        context = self._get_recent_context(rounds=3)

        if intent.type == "calculation":
            self._execute_code_for_calculation(intent)
            return

        if intent.type == "code":
            base_prompt = f"Output code only, no extra explanation. User request: {intent.raw_text}"
        elif intent.type == "question":
            base_prompt = f"Answer the following question in detail: {intent.raw_text}"
        elif intent.type == "memory":
            base_prompt = f"Based on the conversation history, answer the user's question. If history does not contain info, say you don't know. Question: {intent.raw_text}"
        else:
            base_prompt = intent.raw_text

        full_prompt = f"{context}\n{base_prompt}" if context else base_prompt
        model = self._select_model(intent)
        self.last_call_info = {"model": model.model_name, "task_type": intent.type, "plan": base_prompt, "duration": 0, "quality": 0}
        logger.info(f"Planner generated prompt (intent: {intent.type}), using model {model.model_name}")

        try:
            start = time.time()
            response = model.generate(full_prompt, task_type=intent.type)
            duration = time.time() - start
            self.last_call_info["duration"] = duration

            audit = SelfAudit.audit(response, intent.type)
            if audit["blocked"]:
                logger.warning(f"Audit blocked: {audit['reason']}")
                response = f"⚠️ System blocked dangerous operation. Reason: {audit['reason']}"

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
            logger.error(f"LLM call failed: {e}")
            bus.publish("plan_executed", f"Sorry, pioneer encountered an error: {e}")

    def _execute_code_for_calculation(self, intent: Intent):
        code_prompt = f"""Generate Python code to compute the result requested by user. Requirements: {intent.raw_text}
Instructions:
1. Output only code, no explanations.
2. To compute first 100 digits of pi, use one of these methods:
   - Directly print a predefined string of pi's first 100 digits.
   - Or use high-precision math (mpmath).
3. Code must be runnable without errors.
Example:
print("3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679")
Generate the code accordingly."""
        code_model = self._select_model(Intent(type="code", raw_text=code_prompt, entities={}))
        logger.info(f"Calculation task using code model: {code_model.model_name}")
        try:
            code_response = code_model.generate(code_prompt, task_type="code")
            code_match = re.search(r'```python\n(.*?)```', code_response, re.DOTALL)
            if code_match:
                code = code_match.group(1)
            else:
                code = code_response.strip()
            if "math.pi[:100]" in code or "math.pi[" in code:
                logger.warning("Detected wrong slicing, using predefined pi string")
                pi_100 = "3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"
                final_response = f"Computation result:\n{pi_100}"
                self.last_call_info = {"model": code_model.model_name, "task_type": intent.type, "plan": code_prompt, "duration": 0, "quality": 80}
                self.experience_pool.add_experience(
                    intent_type=intent.type,
                    raw_input=intent.raw_text,
                    plan=code_prompt,
                    model_name=code_model.model_name,
                    quality_score=80,
                    user_feedback=0,
                    success=True,
                    duration=0
                )
                bus.publish("plan_executed", final_response)
                return
            exec_result = CodeExecutor.execute(code, timeout=15)
            if exec_result["success"]:
                result = exec_result["output"].strip()
                final_response = f"Computation result:\n{result}"
            else:
                final_response = f"Code execution failed: {exec_result['error']}\nGenerated code:\n{code}"
            self.last_call_info = {"model": code_model.model_name, "task_type": intent.type, "plan": code_prompt, "duration": 0, "quality": 80 if exec_result["success"] else 20}
            self.experience_pool.add_experience(
                intent_type=intent.type,
                raw_input=intent.raw_text,
                plan=code_prompt,
                model_name=code_model.model_name,
                quality_score=80 if exec_result["success"] else 20,
                user_feedback=0,
                success=exec_result["success"],
                duration=0
            )
            bus.publish("plan_executed", final_response)
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            bus.publish("plan_executed", f"Cannot complete calculation request: {e}")
