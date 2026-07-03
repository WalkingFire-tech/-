import asyncio
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class CodeExecutorTool(ToolInterface):
    @property
    def name(self) -> str:
        return "code_executor"

    @property
    def description(self) -> str:
        return "代码执行沙箱：安全执行Python代码，支持Docker/RestrictedPython/子进程"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "Python代码", "required": True},
            "timeout": {"type": "integer", "description": "超时秒数", "default": 10},
            "method": {"type": "string", "description": "执行方法(auto/docker/restricted/subprocess)", "default": "auto"},
        }

    @property
    def timeout(self) -> float:
        return 12.0

    @property
    def category(self) -> str:
        return "computation"

    @property
    def priority(self) -> int:
        return 40

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        code_indicators = ["def ", "import ", "print(", "class ", "for ", "while "]
        return any(ind in query for ind in code_indicators)

    async def execute(self, **kwargs) -> ToolResult:
        code = kwargs.get("query", "")
        timeout = kwargs.get("timeout", 10)
        method = kwargs.get("method", "auto")
        if not code:
            return ToolResult(success=False, error="代码不能为空", source=self.name)

        try:
            def _exec_code():
                from infrastructure.code_executor import CodeExecutor
                return CodeExecutor.execute(code, timeout=timeout, method=method)
            result = await run_tool_async(_exec_code, timeout=12)
        except Exception as e:
            return ToolResult(success=False, error=f"代码执行失败: {e}", source=self.name)

        if result and result.get("success"):
            return ToolResult(
                success=True, data=result.get("output", ""),
                source=f"代码沙箱({result.get('method', 'unknown')})",
                quality=70,
                metadata={"method": result.get("method", "unknown")},
            )
        else:
            return ToolResult(
                success=False, error=(result or {}).get("error", "执行失败"),
                source=self.name, quality=10,
                metadata={"method": (result or {}).get("method", "unknown")},
            )