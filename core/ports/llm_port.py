from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMPort(ABC):
    """LLM 端口抽象：任何大语言模型适配器必须实现这个接口"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """根据提示生成回复"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回模型名称，用于日志和路由"""
        pass
