import requests
import json
from core.ports.llm_port import LLMPort
from loguru import logger

class OllamaAdapter(LLMPort):
    def __init__(self, model_name: str = "mindchat", base_url: str = "http://localhost:11434"):
        self._model_name = model_name
        self.base_url = base_url
        logger.info(f"Ollama 适配器初始化，模型: {model_name}")

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str, **kwargs) -> str:
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
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data["response"].strip()
        except Exception as e:
            logger.error(f"Ollama 请求失败: {e}")
            raise
