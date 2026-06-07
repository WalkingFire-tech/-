import os
from pathlib import Path
from llama_cpp import Llama
from core.ports.llm_port import LLMPort
from loguru import logger

class LocalQwenAdapter(LLMPort):
    def __init__(self, model_path: str = None, n_ctx: int = 2048, n_threads: int = 4):
        if model_path is None:
            model_path = Path(__file__).parent.parent.parent / "models" / "qwen-1_8b-chat-q4_k_m.gguf"
            model_path = str(model_path)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        logger.info(f"加载本地 Qwen 模型: {model_path}")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False
        )
        self._model_name = "Qwen-1.8B-Chat (local)"
        logger.info("本地模型加载完成")
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def generate(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.create_chat_completion(
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 512),
            stop=["<|im_end|>", "<|endoftext|>"]
        )
        content = response["choices"][0]["message"]["content"]
        return content.strip()
