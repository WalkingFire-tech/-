"""
内置工具集 - 系统自带的基础工具
包括代码执行、计算、文件操作等
"""
import subprocess
import tempfile
import os
import re
import math
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
from tools.base import Tool, ToolCategory, Parameter, ToolResult


class CodeExecutionTool(Tool):
    """代码执行工具 - 委托给infrastructure.code_executor统一实现"""
    
    @property
    def name(self) -> str:
        return "code_executor"
    
    @property
    def description(self) -> str:
        return "安全执行Python代码,支持Docker/RestrictedPython/子进程多层沙箱"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CODE
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="code",
                type="str",
                description="要执行的Python代码",
                required=True
            ),
            Parameter(
                name="timeout",
                type="int",
                description="超时时间(秒)",
                required=False,
                default=10
            ),
            Parameter(
                name="method",
                type="str",
                description="执行方法(auto/docker/restricted/subprocess)",
                required=False,
                default="auto"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        code = kwargs.get("code")
        timeout = kwargs.get("timeout", 10)
        method = kwargs.get("method", "auto")
        
        if not code:
            return ToolResult(success=False, output=None, error="代码不能为空")
        
        try:
            from infrastructure.code_executor import CodeExecutor
            result = CodeExecutor.execute(code, timeout=timeout, method=method)
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"代码执行失败: {e}")
        
        if result and result.get("success"):
            return ToolResult(
                success=True,
                output=result.get("output", ""),
                metadata={"method": result.get("method", "unknown")}
            )
        else:
            return ToolResult(
                success=False,
                output=None,
                error=(result or {}).get("error", "执行失败"),
                metadata={"method": (result or {}).get("method", "unknown")}
            )


class CalculatorTool(Tool):
    """数学计算工具"""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "执行数学计算,支持基础运算、三角函数、对数等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CALCULATION
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="expression",
                type="str",
                description="数学表达式,如 '2+3*4', 'sin(pi/2)'",
                required=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        expression = kwargs.get("expression")
        
        safe_dict = {
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'log': math.log, 'log10': math.log10, 'exp': math.exp,
            'pi': math.pi, 'e': math.e,
            'floor': math.floor, 'ceil': math.ceil
        }
        
        DANGEROUS = ['__', 'import', 'eval', 'exec', 'compile', 'open', 'file', 
                     'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr']
        for danger in DANGEROUS:
            if danger in expression:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"表达式包含危险字符: {danger}"
                )
        
        try:
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            
            return ToolResult(
                success=True,
                output=result,
                metadata={"expression": expression}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"计算错误: {str(e)}"
            )


class FileReaderTool(Tool):
    """文件读取工具"""
    
    BASE_DIR = Path("data/workspace").resolve()
    
    @property
    def name(self) -> str:
        return "file_reader"
    
    @property
    def description(self) -> str:
        return "读取文本文件内容"
    
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
                name="encoding",
                type="str",
                description="文件编码",
                required=False,
                default="utf-8"
            ),
            Parameter(
                name="max_lines",
                type="int",
                description="最大读取行数",
                required=False,
                default=1000
            )
        ]
    
    def _sanitize_path(self, file_path: str) -> Path:
        """路径沙盒验证"""
        resolved = Path(file_path).resolve()
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        if not resolved.is_relative_to(self.BASE_DIR):
            logger.warning(f"路径越权，拒绝访问: {file_path}")
            raise PermissionError(f"路径越权: {file_path}")
        
        return resolved
    
    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        encoding = kwargs.get("encoding", "utf-8")
        max_lines = kwargs.get("max_lines", 1000)
        
        try:
            path = self._sanitize_path(file_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"文件不存在: {file_path}"
                )
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"不是文件: {file_path}"
                )
            
            with open(path, 'r', encoding=encoding) as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
            
            content = ''.join(lines)
            
            return ToolResult(
                success=True,
                output=content,
                metadata={
                    "file_path": str(path),
                    "lines_read": len(lines),
                    "total_size": path.stat().st_size
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class TextExtractorTool(Tool):
    """文本提取工具"""
    
    @property
    def name(self) -> str:
        return "text_extractor"
    
    @property
    def description(self) -> str:
        return "从文本中提取特定模式(日期、邮箱、URL等)"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.EXTRACTION
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="text",
                type="str",
                description="要分析的文本",
                required=True
            ),
            Parameter(
                name="pattern",
                type="str",
                description="提取模式: date, email, url, phone, number",
                required=True,
                choices=["date", "email", "url", "phone", "number", "chinese"]
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        text = kwargs.get("text")
        pattern_type = kwargs.get("pattern")
        
        patterns = {
            "date": r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}',
            "email": r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            "url": r'https?://[^\s]+',
            "phone": r'\b1[3-9]\d{9}\b',
            "number": r'\b\d+\.?\d*\b',
            "chinese": r'[\u4e00-\u9fa5]+'
        }
        
        if pattern_type not in patterns:
            return ToolResult(
                success=False,
                output=None,
                error=f"不支持的模式: {pattern_type}"
            )
        
        try:
            pattern = patterns[pattern_type]
            matches = re.findall(pattern, text)
            
            return ToolResult(
                success=True,
                output=matches,
                metadata={
                    "pattern": pattern_type,
                    "count": len(matches)
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class DateTimeTool(Tool):
    """日期时间工具"""
    
    @property
    def name(self) -> str:
        return "datetime_tool"
    
    @property
    def description(self) -> str:
        return "获取当前时间、格式化时间、计算时间差"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CALCULATION
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="operation",
                type="str",
                description="操作类型: now, format, diff",
                required=True,
                choices=["now", "format", "diff"]
            ),
            Parameter(
                name="format_str",
                type="str",
                description="时间格式字符串",
                required=False,
                default="%Y-%m-%d %H:%M:%S"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs.get("operation")
        format_str = kwargs.get("format_str", "%Y-%m-%d %H:%M:%S")
        
        try:
            if operation == "now":
                now = datetime.now()
                return ToolResult(
                    success=True,
                    output=now.strftime(format_str),
                    metadata={"timestamp": now.timestamp()}
                )
            
            elif operation == "format":
                # 这里可以扩展更多格式化选项
                now = datetime.now()
                return ToolResult(
                    success=True,
                    output=now.strftime(format_str)
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


def register_builtin_tools():
    """注册所有内置工具"""
    from core.tool_registry import tool_registry as registry
    
    tools = [
        CodeExecutionTool(),
        CalculatorTool(),
        FileReaderTool(),
        TextExtractorTool(),
        DateTimeTool()
    ]
    
    for tool in tools:
        registry.register(tool)
    
    try:
        from tools.file_operations import register_file_tools
        register_file_tools()
    except Exception as e:
        logger.warning(f"注册文件工具失败: {e}")
    
    try:
        from tools.math_calculator import math_calculator_tool
        registry.register(math_calculator_tool, overwrite=True)
        logger.info("高级数学计算器工具已注册")
    except Exception as e:
        logger.warning(f"注册数学计算器失败: {e}")
    
    try:
        from tools.web_search import WebSearchTool, QuickSearchTool
        registry.register(WebSearchTool(), overwrite=True)
        registry.register(QuickSearchTool(), overwrite=True)
        logger.info("网络搜索工具已注册")
    except Exception as e:
        logger.warning(f"注册网络搜索工具失败: {e}")
    
    logger.info(f"注册{len(tools)}个内置工具")