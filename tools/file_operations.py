"""
文件操作工具集 - 文件和文件夹处理工具
包括文件写入、搜索、批量处理等
"""
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
from tools.base import Tool, ToolCategory, Parameter, ToolResult


def sanitize_path(file_path: str, base_dir: Path = None) -> Path:
    """
    公共路径沙盒验证函数
    
    Args:
        file_path: 待验证的路径
        base_dir: 沙盒根目录，默认为 data/workspace
    
    Returns:
        验证后的安全路径
    """
    base_dir = base_dir or Path("data/workspace").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    
    path = Path(file_path).resolve()
    
    try:
        if path.is_relative_to(base_dir):
            return path
    except AttributeError:
        if str(path).startswith(str(base_dir)):
            return path
    
    logger.warning(f"路径越权，强制使用workspace目录: {file_path}")
    return base_dir / Path(file_path).name


class BaseFileTool(Tool):
    """文件工具基类，提供公共路径验证"""
    
    BASE_DIR = Path("data/workspace").resolve()
    
    def _sanitize_path(self, file_path: str) -> Path:
        """路径沙盒验证"""
        return sanitize_path(file_path, self.BASE_DIR)


class FileWriterTool(BaseFileTool):
    """文件写入工具"""
    
    @property
    def name(self) -> str:
        return "file_writer"
    
    @property
    def description(self) -> str:
        return "写入内容到文件,支持创建、追加、覆盖模式"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="file_path",
                type="str",
                description="文件路径",
                required=True
            ),
            Parameter(
                name="content",
                type="str",
                description="要写入的内容",
                required=True
            ),
            Parameter(
                name="mode",
                type="str",
                description="写入模式: write(覆盖), append(追加)",
                required=False,
                default="write",
                choices=["write", "append"]
            ),
            Parameter(
                name="encoding",
                type="str",
                description="文件编码",
                required=False,
                default="utf-8"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        mode = kwargs.get("mode", "write")
        encoding = kwargs.get("encoding", "utf-8")
        
        try:
            path = self._sanitize_path(file_path)
            
            path.parent.mkdir(parents=True, exist_ok=True)
            
            write_mode = 'w' if mode == "write" else 'a'
            
            with open(path, write_mode, encoding=encoding) as f:
                f.write(content)
            
            return ToolResult(
                success=True,
                output=f"成功写入文件: {path.name}",
                metadata={
                    "file_path": str(path),
                    "mode": mode,
                    "size": len(content.encode(encoding))
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class FileSearchTool(BaseFileTool):
    """文件搜索工具"""
    
    @property
    def name(self) -> str:
        return "file_search"
    
    @property
    def description(self) -> str:
        return "在文件或文件夹中搜索内容,支持正则表达式"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="path",
                type="str",
                description="文件或文件夹路径",
                required=True
            ),
            Parameter(
                name="pattern",
                type="str",
                description="搜索模式(支持正则表达式)",
                required=True
            ),
            Parameter(
                name="recursive",
                type="bool",
                description="是否递归搜索子文件夹",
                required=False,
                default=True
            ),
            Parameter(
                name="file_pattern",
                type="str",
                description="文件名模式(如 *.py)",
                required=False,
                default="*"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path")
        pattern = kwargs.get("pattern")
        recursive = kwargs.get("recursive", True)
        file_pattern = kwargs.get("file_pattern", "*")
        
        try:
            search_path = self._sanitize_path(path)
            regex = re.compile(pattern, re.IGNORECASE)
            
            results = []
            
            if search_path.is_file():
                files = [search_path]
            else:
                if recursive:
                    files = search_path.rglob(file_pattern)
                else:
                    files = search_path.glob(file_pattern)
                files = [f for f in files if f.is_file()]
            
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.strip()
                                })
                                
                                if len(results) >= 100:
                                    logger.warning("搜索结果达到上限100条")
                                    break
                
                except Exception as e:
                    logger.warning(f"无法读取文件 {file_path}: {e}")
                
                if len(results) >= 100:
                    break
            
            return ToolResult(
                success=True,
                output=results,
                metadata={
                    "pattern": pattern,
                    "total_matches": len(results),
                    "files_searched": len(files)
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class FileBatchProcessorTool(BaseFileTool):
    """文件批量处理工具"""
    
    @property
    def name(self) -> str:
        return "file_batch_processor"
    
    @property
    def description(self) -> str:
        return "批量处理文件夹中的文件,支持过滤和操作"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="folder_path",
                type="str",
                description="文件夹路径",
                required=True
            ),
            Parameter(
                name="operation",
                type="str",
                description="操作类型: list, count, size, delete_empty",
                required=True,
                choices=["list", "count", "size", "delete_empty"]
            ),
            Parameter(
                name="file_pattern",
                type="str",
                description="文件名模式(如 *.py)",
                required=False,
                default="*"
            ),
            Parameter(
                name="recursive",
                type="bool",
                description="是否递归处理子文件夹",
                required=False,
                default=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        folder_path = kwargs.get("folder_path")
        operation = kwargs.get("operation")
        file_pattern = kwargs.get("file_pattern", "*")
        recursive = kwargs.get("recursive", True)
        
        try:
            folder = self._sanitize_path(folder_path)
            
            if not folder.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"不是文件夹: {folder_path}"
                )
            
            if recursive:
                files = list(folder.rglob(file_pattern))
            else:
                files = list(folder.glob(file_pattern))
            
            files = [f for f in files if f.is_file()]
            
            if operation == "list":
                result = [
                    {
                        "path": str(f),
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    }
                    for f in files
                ]
                
                return ToolResult(
                    success=True,
                    output=result,
                    metadata={"total_files": len(files)}
                )
            
            elif operation == "count":
                ext_count = {}
                for f in files:
                    ext = f.suffix.lower()
                    ext_count[ext] = ext_count.get(ext, 0) + 1
                
                return ToolResult(
                    success=True,
                    output=ext_count,
                    metadata={"total_files": len(files)}
                )
            
            elif operation == "size":
                total_size = sum(f.stat().st_size for f in files)
                
                return ToolResult(
                    success=True,
                    output={
                        "total_size": total_size,
                        "total_size_mb": total_size / (1024 * 1024),
                        "file_count": len(files),
                        "avg_size": total_size / len(files) if files else 0
                    }
                )
            
            elif operation == "delete_empty":
                deleted = []
                for f in files:
                    if f.stat().st_size == 0:
                        f.unlink()
                        deleted.append(str(f))
                
                return ToolResult(
                    success=True,
                    output=f"删除了{len(deleted)}个空文件",
                    metadata={"deleted_files": deleted}
                )
            
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"未知操作: {operation}"
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class FileRenameTool(BaseFileTool):
    """文件重命名工具"""
    
    @property
    def name(self) -> str:
        return "file_rename"
    
    @property
    def description(self) -> str:
        return "重命名文件或批量重命名"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="source",
                type="str",
                description="源文件路径",
                required=True
            ),
            Parameter(
                name="target",
                type="str",
                description="目标文件名或路径",
                required=True
            ),
            Parameter(
                name="overwrite",
                type="bool",
                description="是否覆盖已存在的文件",
                required=False,
                default=False
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        source = kwargs.get("source")
        target = kwargs.get("target")
        overwrite = kwargs.get("overwrite", False)
        
        try:
            source_path = self._sanitize_path(source)
            
            if not source_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"源文件不存在: {source}"
                )
            
            target_path = self._sanitize_path(target)
            
            if not target_path.is_absolute():
                target_path = source_path.parent / target
            
            if target_path.exists() and not overwrite:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"目标文件已存在: {target_path}"
                )
            
            source_path.rename(target_path)
            
            return ToolResult(
                success=True,
                output=f"重命名成功: {source_path.name} -> {target_path.name}",
                metadata={
                    "source": str(source_path),
                    "target": str(target_path)
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class FileCopyTool(BaseFileTool):
    """文件复制工具"""
    
    @property
    def name(self) -> str:
        return "file_copy"
    
    @property
    def description(self) -> str:
        return "复制文件或文件夹"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="source",
                type="str",
                description="源文件或文件夹路径",
                required=True
            ),
            Parameter(
                name="target",
                type="str",
                description="目标路径",
                required=True
            ),
            Parameter(
                name="overwrite",
                type="bool",
                description="是否覆盖已存在的文件",
                required=False,
                default=False
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        source = kwargs.get("source")
        target = kwargs.get("target")
        overwrite = kwargs.get("overwrite", False)
        
        try:
            source_path = self._sanitize_path(source)
            target_path = self._sanitize_path(target)
            
            if not source_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"源路径不存在: {source}"
                )
            
            if target_path.exists():
                if not overwrite:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"目标路径已存在: {target}，需设置overwrite=True"
                    )
                
                logger.warning(f"覆盖目标路径: {target_path}")
            
            if source_path.is_file():
                if target_path.exists() and overwrite:
                    target_path.unlink()
                shutil.copy2(source_path, target_path)
                operation = "文件"
            else:
                if target_path.exists() and overwrite:
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
                operation = "文件夹"
            
            return ToolResult(
                success=True,
                output=f"{operation}复制成功",
                metadata={
                    "source": str(source_path),
                    "target": str(target_path),
                    "overwrite": overwrite
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


def register_file_tools():
    """注册文件操作工具"""
    from core.tool_registry import tool_registry as registry
    
    tools = [
        FileWriterTool(),
        FileSearchTool(),
        FileBatchProcessorTool(),
        FileRenameTool(),
        FileCopyTool()
    ]
    
    for tool in tools:
        registry.register(tool)
    
    logger.info(f"注册{len(tools)}个文件操作工具")