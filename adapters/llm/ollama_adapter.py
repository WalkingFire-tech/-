import requests
import time
from core.ports.llm_port import LLMPort
from infrastructure.model_stats import ModelStats
from infrastructure.quality_evaluator import QualityEvaluator
from loguru import logger

class OllamaAdapter(LLMPort):
    _stats = ModelStats()

    def __init__(self, model_name: str = "mindchat", base_url: str = "http://localhost:11434"):
        self._model_name = model_name
        self.base_url = base_url
        logger.info(f"Ollama 适配器初始化，模型: {model_name}")

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str, task_type: str = "chat", **kwargs) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 512),
            }
        }
        start_time = time.time()
        success = False
        response_text = ""
        quality_score = 0
        try:
            response = requests.post(url, json=payload, timeout=kwargs.get("timeout", 120))
            response.raise_for_status()
            data = response.json()
            response_text = data["response"].strip()
            success = True
            # 自动评估质量
            quality_score = QualityEvaluator.evaluate(response_text, task_type)
            logger.info(f"质量评估: {quality_score}/100 for {task_type}")
            return response_text
        except Exception as e:
            logger.error(f"Ollama 请求失败: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self._stats.record_call(
                model_name=self._model_name,
                task_type=task_type,
                duration=duration,
                success=success,
                user_feedback=None,
                input_tokens=len(prompt),
                output_tokens=len(response_text),
                quality_score=quality_score
            )
            logger.debug(f"记录统计: {self._model_name}, {task_type}, 耗时 {duration:.2f}s, 质量 {quality_score}")
