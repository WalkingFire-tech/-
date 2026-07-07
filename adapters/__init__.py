"""
适配器层 (Adapters Layer)

提供外部系统接口适配，包括LLM、UI和输入适配器。
"""

from .llm.ollama_adapter import OllamaAdapter
from .llm.openai_adapter import OpenAIAdapter
try:
    from .llm.local_qwen_adapter import LocalQwenAdapter
except ImportError:
    LocalQwenAdapter = None
from .llm.mock_adapter import MockAdapter
from .llm.remote_adapter import RemoteAdapter
try:
    from .llm.lora_adapter import LoRAAdapter
except ImportError:
    LoRAAdapter = None
try:
    from .ui.cli_ui import EnhancedCliUI
except ImportError:
    EnhancedCliUI = None
try:
    from .input.file_adapter import FileAdapter
except ImportError:
    FileAdapter = None
try:
    from .input.folder_processor import FolderBatchProcessor
except ImportError:
    FolderBatchProcessor = None

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