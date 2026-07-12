"""
代码文件提取器 - 提取关键结构
"""

from pathlib import Path
from typing import Optional, List
import re
from loguru import logger

from .base import ContentExtractor


class CodeExtractor(ContentExtractor):
    """代码文件专用提取器（提取关键结构）"""
    
    def __init__(self, max_size_mb: int = 5):
        """
        Args:
            max_size_mb: 最大文件大小（MB）
        """
        self.max_size_mb = max_size_mb
        self.supported_extensions = {
            '.py', '.js', '.ts', '.java', '.go', '.rs', 
            '.c', '.cpp', '.h', '.hpp', '.cs', '.swift',
            '.kt', '.scala', '.rb', '.php'
        }
    
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions
    
    def extract(self, file_path: Path) -> Optional[str]:
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_size_mb * 1024 * 1024:
                logger.warning(f"文件过大，跳过: {file_path}")
                return None
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            lines = content.split('\n')
            extracted = []
            comment_count = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                
                if self._is_structure_line(stripped, file_path.suffix):
                    extracted.append(stripped)
                elif self._is_comment(stripped, file_path.suffix):
                    if comment_count < 20:
                        extracted.append(stripped)
                        comment_count += 1
            
            return '\n'.join(extracted) if extracted else None
            
        except Exception as e:
            logger.error(f"代码提取失败 {file_path}: {e}")
            return None
    
    def _is_structure_line(self, line: str, suffix: str) -> bool:
        """判断是否为结构行（函数、类、导入等）"""
        suffix = suffix.lower()
        
        if suffix == '.py':
            return bool(re.match(r'^(def|class|import|from|async\s+def)\s', line))
        
        elif suffix in {'.js', '.ts', '.jsx', '.tsx'}:
            return bool(re.match(
                r'^(function|class|export|import|const\s+\w+\s*=\s*\(?.*\)?\s*=>?|async\s+function)',
                line
            ))
        
        elif suffix == '.java':
            return bool(re.match(
                r'^(public|private|protected|class|interface|enum|import|package)\s',
                line
            ))
        
        elif suffix == '.go':
            return bool(re.match(r'^(func|type|import|package|var|const)\s', line))
        
        elif suffix == '.rs':
            return bool(re.match(r'^(fn|struct|enum|impl|use|mod|pub)\s', line))
        
        elif suffix in {'.c', '.cpp', '.h', '.hpp'}:
            return bool(re.match(
                r'^(class|struct|enum|namespace|template|typedef|#include|#define)',
                line
            ))
        
        else:
            return bool(re.match(r'^(function|class|def|import|export)\s', line))
    
    def _is_comment(self, line: str, suffix: str) -> bool:
        """判断是否为注释"""
        suffix = suffix.lower()
        
        if suffix == '.py':
            return line.startswith('#') or line.startswith('"""') or line.startswith("'''")
        
        elif suffix in {'.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp'}:
            return line.startswith('//') or line.startswith('/*') or line.startswith('*')
        
        else:
            return line.startswith('#') or line.startswith('//')
    
    def get_supported_extensions(self) -> List[str]:
        return list(self.supported_extensions)
    
    def get_name(self) -> str:
        return "CodeExtractor"