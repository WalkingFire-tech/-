import asyncio
from datetime import datetime
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult


class DateTimeTool(ToolInterface):
    @property
    def name(self) -> str:
        return "datetime"

    @property
    def description(self) -> str:
        return "日期时间查询：获取当前时间、日期、星期"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "时间相关查询", "required": True},
        }

    @property
    def timeout(self) -> float:
        return 3.0

    @property
    def category(self) -> str:
        return "time"

    @property
    def priority(self) -> int:
        return 95

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        time_keywords = [
            "几点", "时间", "现在几点", "当前时间", "几点了", "什么时候",
            "日期", "今天几号", "星期几", "几月几号", "今天是", "现在时间",
            "what time", "current time", "date today", "what day",
        ]
        return any(kw in query.lower() for kw in time_keywords) or intent_type == "time"

    async def execute(self, **kwargs) -> ToolResult:
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday = weekdays[now.weekday()]
        result = (
            f"现在是 {now.strftime('%Y年%m月%d日')} {weekday} "
            f"{now.strftime('%H时%M分%S秒')}"
        )
        return ToolResult(
            success=True,
            data=result,
            source="日期时间",
            quality=98,
            metadata={"task_type": "time_query", "timestamp": now.timestamp()},
        )