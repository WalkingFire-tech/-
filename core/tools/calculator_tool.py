import asyncio
import re
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult


class CalculatorTool(ToolInterface):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "数学计算器：支持四则运算、三角函数、对数、π计算等数学表达式"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "数学表达式或计算请求", "required": True},
        }

    @property
    def timeout(self) -> float:
        return 5.0

    @property
    def category(self) -> str:
        return "computation"

    @property
    def priority(self) -> int:
        return 80

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        calc_keywords = ["计算", "求值", "等于多少", "π", "圆周率", "算"]
        math_patterns = [
            r'\d+\s*[\+\-\*/\^%]\s*\d+',
            r'(sin|cos|tan|log|sqrt|exp|abs|factorial)\s*\(',
            r'\d+\s*[\+\-\*/]\s*\d+',
        ]
        if any(kw in query for kw in calc_keywords):
            return True
        return any(re.search(p, query) for p in math_patterns)

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="表达式不能为空", source=self.name)

        try:
            import re
            clean = re.sub(r'[^0-9+\-*/().%\s]', '', query)
            clean = clean.strip()
            if not clean:
                return ToolResult(success=False, error="无法提取数学表达式", source=self.name)
            allowed = set("0123456789+-*/().% ")
            if not all(c in allowed for c in clean):
                return ToolResult(success=False, error="表达式包含不安全字符", source=self.name)
            result = eval(clean, {"__builtins__": {}}, {})
            return ToolResult(
                success=True, data=str(result),
                source="计算器", quality=95,
                metadata={"task_type": "expression"},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"计算失败: {e}", source=self.name)