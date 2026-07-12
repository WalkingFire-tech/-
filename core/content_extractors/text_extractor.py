"""
文本文件提取器 - 支持多种编码
"""

from pathlib import Path
from typing import Optional, List
from loguru import logger

from .base import ContentExtractor


class TextExtractor(ContentExtractor):
    """纯文本文件提取器"""
    
    def __init__(self, max_size_mb: int = 10):
        """
        Args:
            max_size_mb: 最大文件大小（MB）
        """
        self.max_size_mb = max_size_mb
        self.supported_extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml',
            '.rst', '.js', '.html', '.css', '.ts', '.jsx', '.tsx',
            '.xml', '.ini', '.cfg', '.toml', '.sh', '.bat',
            '.csv', '.log', '.env', '.gitignore', '.sql',
            '.java', '.go', '.rs', '.c', '.cpp', '.h', '.hpp',
            '.vue', '.svelte', '.dart', '.kt', '.scala'
        }
    
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions
    
    def extract(self, file_path: Path) -> Optional[str]:
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_size_mb * 1024 * 1024:
                logger.warning(f"文件过大，跳过: {file_path}")
                return None
            
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings:
                try:
                    content = file_path.read_text(encoding=encoding)
                    return content
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"读取失败 {file_path} ({encoding}): {e}")
                    continue
            
            logger.warning(f"无法解码文件: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"文本提取失败 {file_path}: {e}")
            return None
    
    def get_supported_extensions(self) -> List[str]:
        return list(self.supported_extensions)
    
    def get_name(self) -> str:
        return "TextExtractor"