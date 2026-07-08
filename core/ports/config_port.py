"""
Config 端口 — 配置管理的抽象接口

任何配置管理实现必须遵循此接口。
当前实现: infrastructure.config_manager.ConfigManager
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class ConfigPort(ABC):
    """配置管理端口"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        ...

    @abstractmethod
    def get_section(self, name: str) -> Dict:
        """获取配置段"""
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """配置管理是否可用"""
        ...