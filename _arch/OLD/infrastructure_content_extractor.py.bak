"""
内容提取器 - 支持多种文件格式
可扩展的解析器框架
"""
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Callable
from datetime import datetime
from loguru import logger

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PREVIEW_SIZE = 1 * 1024 * 1024  # 1MB预览
ALLOWED_EXTENSIONS = {
    '.txt', '.md', '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs',
    '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.csv', '.tsv',
    '.sh', '.bat', '.ps1', '.sql', '.r', '.m', '.swift', '.kt', '.scala'
}


class ContentExtractor:
    """内容提取器"""
    
    def __init__(self, allowed_base_dir: Optional[Path] = None):
        self.allowed_base_dir = allowed_base_dir or Path.cwd()
        self.extractors = {
            '.txt': self._extract_text,
            '.md': self._extract_text,
            '.py': self._extract_code,
            '.js': self._extract_code,
            '.ts': self._extract_code,
            '.java': self._extract_code,
            '.cpp': self._extract_code,
            '.c': self._extract_code,
            '.go': self._extract_code,
            '.rs': self._extract_code,
            '.html': self._extract_html,
            '.css': self._extract_text,
            '.json': self._extract_json,
            '.xml': self._extract_text,
            '.yaml': self._extract_text,
            '.yml': self._extract_text,
            '.csv': self._extract_csv,
            '.tsv': self._extract_csv,
        }
        
        logger.info(f"内容提取器初始化,支持{len(self.extractors)}种格式,沙盒目录: {self.allowed_base_dir}")
    
    def _validate_path(self, path: Path) -> Path:
        """验证路径安全性"""
        resolved = path.resolve()
        
        if not resolved.is_relative_to(self.allowed_base_dir.resolve()):
            raise PermissionError(f"路径越权: {path} 不在沙盒目录 {self.allowed_base_dir} 内")
        
        if resolved.is_symlink():
            raise PermissionError(f"禁止符号链接: {path}")
        
        if not resolved.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        
        if not resolved.is_file():
            raise ValueError(f"不是文件: {path}")
        
        file_size = resolved.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"文件过大: {file_size}字节，超过限制 {MAX_FILE_SIZE}字节")
        
        return resolved
    
    def extract(self, file_path: str) -> Tuple[str, Dict]:
        """提取文件内容"""
        path = Path(file_path)
        
        try:
            validated_path = self._validate_path(path)
        except Exception as e:
            logger.error(f"路径验证失败: {e}")
            return "", {"error": str(e), "filename": path.name}
        
        ext = validated_path.suffix.lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            logger.warning(f"不支持的扩展名: {ext}")
            return "", {"error": f"不支持的文件类型: {ext}", "filename": validated_path.name}
        
        metadata = self._get_basic_metadata(validated_path)
        
        if ext in self.extractors:
            try:
                content, extra_meta = self.extractors[ext](validated_path)
                metadata.update(extra_meta)
                return content, metadata
            except Exception as e:
                logger.error(f"提取失败: {e}")
                return f"[提取失败: {str(e)}]", metadata
        else:
            return self._extract_text(validated_path)
    
    def _get_basic_metadata(self, path: Path) -> Dict:
        """获取基础元数据"""
        stat = path.stat()
        return {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    
    def _extract_text(self, path: Path) -> Tuple[str, Dict]:
        """提取纯文本"""
        file_size = path.stat().st_size
        
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    if file_size > MAX_PREVIEW_SIZE:
                        content = f.read(MAX_PREVIEW_SIZE)
                        logger.warning(f"文件过大，仅读取前{MAX_PREVIEW_SIZE}字节")
                    else:
                        content = f.read()
                
                lines = content.split('\n')
                return content, {
                    "encoding": encoding,
                    "lines": len(lines),
                    "chars": len(content),
                    "words": len(content.split()),
                    "truncated": file_size > MAX_PREVIEW_SIZE
                }
            except UnicodeDecodeError:
                continue
        
        raise ValueError("无法解码文件")
    
    def _extract_code(self, path: Path) -> Tuple[str, Dict]:
        """提取代码文件"""
        content, meta = self._extract_text(path)
        
        # 分析代码结构
        lines = content.split('\n')
        
        # 统计代码、注释、空行
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#') or stripped.startswith('//'):
                comment_lines += 1
            else:
                code_lines += 1
        
        # 提取函数/类定义
        functions = []
        classes = []
        
        for i, line in enumerate(lines, 1):
            # Python函数
            if re.match(r'\s*def\s+\w+', line):
                match = re.search(r'def\s+(\w+)', line)
                if match:
                    functions.append({"name": match.group(1), "line": i})
            
            # Python类
            if re.match(r'\s*class\s+\w+', line):
                match = re.search(r'class\s+(\w+)', line)
                if match:
                    classes.append({"name": match.group(1), "line": i})
        
        meta.update({
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "blank_lines": blank_lines,
            "functions": functions[:10],  # 最多10个
            "classes": classes[:10],
            "function_count": len(functions),
            "class_count": len(classes)
        })
        
        return content, meta
    
    def _extract_html(self, path: Path) -> Tuple[str, Dict]:
        """提取HTML文件"""
        content, meta = self._extract_text(path)
        
        # 提取标题
        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        title = title_match.group(1) if title_match else None
        
        # 提取链接数
        links = len(re.findall(r'<a\s+', content, re.IGNORECASE))
        
        # 提取图片数
        images = len(re.findall(r'<img\s+', content, re.IGNORECASE))
        
        meta.update({
            "title": title,
            "links": links,
            "images": images
        })
        
        return content, meta
    
    def _extract_json(self, path: Path) -> Tuple[str, Dict]:
        """提取JSON文件"""
        import json
        
        content, meta = self._extract_text(path)
        
        try:
            data = json.loads(content)
            
            # 分析JSON结构
            if isinstance(data, dict):
                meta["json_type"] = "object"
                meta["keys"] = list(data.keys())[:20]
                meta["key_count"] = len(data)
            elif isinstance(data, list):
                meta["json_type"] = "array"
                meta["length"] = len(data)
            else:
                meta["json_type"] = "primitive"
        
        except json.JSONDecodeError:
            meta["json_valid"] = False
        
        return content, meta
    
    def _extract_csv(self, path: Path) -> Tuple[str, Dict]:
        """提取CSV/TSV文件"""
        content, meta = self._extract_text(path)
        
        lines = content.strip().split('\n')
        
        if lines:
            # 分析列数
            delimiter = '\t' if path.suffix == '.tsv' else ','
            first_line = lines[0]
            columns = first_line.split(delimiter)
            
            meta.update({
                "rows": len(lines) - 1,  # 减去表头
                "columns": len(columns),
                "headers": columns[:20],
                "delimiter": "tab" if delimiter == '\t' else "comma"
            })
        
        return content, meta
    
    def register_extractor(self, extension: str, extractor_func: Callable, allow_override: bool = False):
        """注册自定义提取器
        
        Args:
            extension: 文件扩展名
            extractor_func: 提取函数
            allow_override: 是否允许覆盖已存在的提取器
        """
        import inspect
        
        if not extension.startswith('.'):
            raise ValueError(f"扩展名必须以点开头: {extension}")
        
        if not callable(extractor_func):
            raise TypeError("extractor_func必须是可调用对象")
        
        if extension in self.extractors and not allow_override:
            raise ValueError(f"提取器已存在: {extension}，使用allow_override=True覆盖")
        
        sig = inspect.signature(extractor_func)
        if len(sig.parameters) < 1:
            raise TypeError("extractor_func必须接受至少一个参数（Path对象）")
        
        self.extractors[extension] = extractor_func
        logger.info(f"注册提取器: {extension}")
    
    def get_supported_extensions(self) -> list:
        """获取支持的扩展名"""
        return list(self.extractors.keys())

# 全局实例（使用当前工作目录作为沙盒）
content_extractor = ContentExtractor(allowed_base_dir=Path.cwd())