"""
内容提取器基类 - 统一接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List


class ContentExtractor(ABC):
    """文件内容提取器接口"""
    
    @abstractmethod
    def extract(self, file_path: Path) -> Optional[str]:
        """
        提取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 提取的文本内容
            '': 空文件或无文本内容（扫描件）
            None: 提取失败或不支持
        """
        pass
    
    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """
        判断是否支持该文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持
        """
        pass
    
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名列表
        
        Returns:
            List[str]: 扩展名列表，如 ['.pdf', '.txt']
        """
        return []
    
    def get_name(self) -> str:
        """
        获取提取器名称
        
        Returns:
            str: 提取器名称
        """
        return self.__class__.__name__