"""
输入适配器模块

提供文件和文件夹处理适配接口。
"""

from .file_adapter import FileAdapter
from .folder_processor import FolderProcessor

__all__ = [
    'FileAdapter',
    'FolderProcessor',
]