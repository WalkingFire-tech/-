"""
工具注册表 - 薄代理层（已废弃）

已统一到 core/tool_registry.py，本模块保持向后兼容。
请直接使用 from core.tool_registry import tool_registry, ToolRegistry 等。

迁移说明：
- 核心注册表：core.tool_registry.ToolRegistry (单例: tool_registry)
- 工具执行器：core.tool_registry.ToolExecutor (单例: tool_executor)
- 旧版Tool适配：core.tool_registry.LegacyToolAdapter
- 本模块的 registry 变量指向 core.tool_registry.tool_registry
"""

import warnings

warnings.warn(
    "tools.registry 已废弃，请使用 core.tool_registry。将在下个版本移除。",
    DeprecationWarning,
    stacklevel=2,
)

from core.tool_registry import (
    ToolRegistry,
    ToolInterface,
    ToolResult,
    ToolExecutor,
    LegacyToolAdapter,
    tool_registry,
    tool_executor,
    register_builtin_tools,
    run_tool_sync,
    run_tool_async,
)

registry = tool_registry


def _reexport_base_classes():
    """延迟重导出 tools/base.py 的类，保持旧代码兼容"""
    try:
        from tools.base import Tool, ToolCategory, Parameter, ToolMetadata
        return Tool, ToolCategory, Parameter, ToolMetadata
    except ImportError:
        return None, None, None, None


Tool, ToolCategory, Parameter, ToolMetadata = _reexport_base_classes()
