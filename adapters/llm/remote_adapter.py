import os
import time
from openai import OpenAI
from core.ports.llm_port import LLMPort
from loguru import logger

class RemoteAdapter(LLMPort):
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: str = None, base_url: str = None):
        self._model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未设置 OPENAI_API_KEY 环境变量")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        logger.info(f"远程适配器初始化，模型: {model_name}")

    @property
    def model_name(self) -> str:
        return f"remote/{self._model_name}"

    def generate(self, prompt: str, task_type: str = "chat", **kwargs) -> str:
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1024)
            )
            content = response.choices[0].message.content
            duration = time.time() - start_time
            # 记录调用统计（需要 ModelStats，但不在此处耦合，由 planner 统一记录）
            logger.info(f"远程调用成功: {self._model_name}, 耗时 {duration:.2f}s")
            return content.strip()
        except Exception as e:
            logger.error(f"远程API调用失败: {e}")
            raise
