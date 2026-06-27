"""
工具模块

包含：
- base: 工具基类和接口定义
- registry: 工具注册表（单例）
- arbiter: 工具仲裁器（UCB1算法）
- math_calculator: 高级数学计算器
- web_search: 网络搜索工具
- file_operations: 文件操作工具集
- builtin: 内置工具集
- generator: 工具生成器
"""

from tools.base import Tool, ToolCategory, Parameter, ToolResult
from tools.registry import registry, ToolRegistry
from tools.arbiter import ToolArbiter, get_tool_arbiter

__all__ = [
    "Tool",
    "ToolCategory",
    "Parameter",
    "ToolResult",
    "registry",
    "ToolRegistry",
    "ToolArbiter",
    "get_tool_arbiter",
]