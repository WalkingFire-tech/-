import os
from openai import OpenAI
from core.ports.llm_port import LLMPort
from loguru import logger

class OpenAIAdapter(LLMPort):
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 OPENAI_API_KEY 环境变量")
        self.client = OpenAI(api_key=self.api_key)
        self._model_name = model
    
    @property
    def model_name(self) -> str:
        return f"OpenAI/{self._model_name}"
    
    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API 错误: {e}")
            raise
