"""
LLM适配器模块

提供各种大语言模型的适配接口。
"""

from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .local_qwen_adapter import LocalQwenAdapter
from .mock_adapter import MockAdapter
from .remote_adapter import RemoteAdapter
from .lora_adapter import LoRAAdapter

__all__ = [
    'OllamaAdapter',
    'OpenAIAdapter',
    'LocalQwenAdapter',
    'MockAdapter',
    'RemoteAdapter',
    'LoRAAdapter',
]