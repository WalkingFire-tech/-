"""
LLM适配器模块

提供各种大语言模型的适配接口。
"""

from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
try:
    from .local_qwen_adapter import LocalQwenAdapter
except ImportError:
    LocalQwenAdapter = None
from .mock_adapter import MockAdapter
from .remote_adapter import RemoteAdapter
try:
    from .lora_adapter import LoRAAdapter
except ImportError:
    LoRAAdapter = None

__all__ = [
    'OllamaAdapter',
    'OpenAIAdapter',
    'LocalQwenAdapter',
    'MockAdapter',
    'RemoteAdapter',
    'LoRAAdapter',
]