import asyncio
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class FactCheckTool(ToolInterface):
    @property
    def name(self) -> str:
        return "fact_check"

    @property
    def description(self) -> str:
        return "事实核查：从事实锚点库中检索已验证的事实断言，支持否定检测"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "待核查的问题或陈述", "required": True},
        }

    @property
    def timeout(self) -> float:
        return 5.0

    @property
    def category(self) -> str:
        return "verification"

    @property
    def priority(self) -> int:
        return 65

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        verify_intents = {"factual", "verification", "fact_check"}
        return intent_type in verify_intents or len(query) > 5

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="查询不能为空", source=self.name)

        try:
            def _query_facts():
                from infrastructure.fact_store import fact_store
                a = fact_store.get_assertions(query)
                n = fact_store.get_negations(query)
                k = fact_store.search_by_keywords(query, limit=5)
                return a, n, k
            result = await run_tool_async(_query_facts, timeout=8)
            if result is None:
                return ToolResult(success=False, error="事实查询超时",
                                  source=self.name, quality=10)
            assertions, negations, keyword_results = result
        except Exception as e:
            return ToolResult(success=False, error=f"事实查询失败: {e}",
                              source=self.name, quality=10)

        parts = []
        if assertions:
            for a in assertions[:3]:
                s = a.get("subject", "")
                p = a.get("predicate", "")
                o = a.get("object", "")
                c = a.get("confidence", 0)
                parts.append(f"✓ {s} {p} {o} (置信度:{c:.0%})")

        if negations:
            for n in negations[:2]:
                s = n.get("subject", "")
                p = n.get("predicate", "")
                o = n.get("object", "")
                parts.append(f"✗ 否定: {s} {p} {o}")

        if keyword_results:
            for kr in keyword_results[:3]:
                if kr.get("subject"):
                    parts.append(f"◆ {kr['subject']} {kr.get('predicate', '')} {kr.get('object', '')}")

        if not parts:
            return ToolResult(success=False, error="未找到相关事实锚点",
                              source=self.name, quality=10)

        combined = "\n".join(parts)
        quality = min(85, 40 + len(assertions) * 15 + len(keyword_results) * 5)
        if negations:
            quality = min(90, quality + 10)

        return ToolResult(
            success=True, data=combined,
            source="事实锚点",
            quality=quality,
            metadata={
                "assertion_count": len(assertions),
                "negation_count": len(negations),
                "keyword_count": len(keyword_results),
            },
        )