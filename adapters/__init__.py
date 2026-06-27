"""
适配器层 (Adapters Layer)

提供外部系统接口适配，包括LLM、UI和输入适配器。
"""

from .llm.ollama_adapter import OllamaAdapter
from .llm.openai_adapter import OpenAIAdapter
from .llm.local_qwen_adapter import LocalQwenAdapter
from .llm.mock_adapter import MockAdapter
from .llm.remote_adapter import RemoteAdapter
from .llm.lora_adapter import LoRAAdapter
from .ui.cli_ui import EnhancedCliUI
from .input.file_adapter import FileAdapter
from .input.folder_processor import FolderBatchProcessor

__all__ = [
    'OllamaAdapter',
    'OpenAIAdapter',
    'LocalQwenAdapter',
    'MockAdapter',
    'RemoteAdapter',
    'LoRAAdapter',
    'EnhancedCliUI',
    'FileAdapter',
    'FolderBatchProcessor',
]