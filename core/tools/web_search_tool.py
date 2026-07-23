import asyncio
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class WebSearchTool(ToolInterface):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "隐身网络搜索：通过百度/Bing搜索获取实时信息，支持中英文"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "搜索查询", "required": True},
            "max_results": {"type": "integer", "description": "最大结果数", "default": 8},
        }

    @property
    def timeout(self) -> float:
        return 15.0

    @property
    def category(self) -> str:
        return "search"

    @property
    def priority(self) -> int:
        return 70

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        search_intents = {"factual", "knowledge", "news", "current_event", "definition",
                          "simple_query", "complex_query", "learning_trigger"}
        creative_keywords = ["写一首", "作诗", "写诗", "写个故事", "编一个", "创作",
                             "写一篇", "写一段", "来一首", "来一篇", "写歌", "作词",
                             "写小说", "写散文", "写童话"]
        if any(kw in query for kw in creative_keywords):
            return False
        return intent_type in search_intents or len(query) > 10

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 8)
        if not query:
            return ToolResult(success=False, error="查询不能为空", source=self.name)

        try:
            def _search():
                from infrastructure.stealth_search import search_web_stealthy
                return search_web_stealthy(query, max_results=max_results)
            results = await run_tool_async(_search, timeout=12)
        except Exception as e:
            try:
                def _search_baidu():
                    from infrastructure.stealth_search import search_baidu
                    return search_baidu(query, max_results=max_results)
                results = await run_tool_async(_search_baidu, timeout=10)
            except Exception as e2:
                return ToolResult(success=False, error=f"搜索失败: {e}; 降级也失败: {e2}",
                                  source=self.name)

        if not results:
            return ToolResult(success=False, error="未找到相关结果",
                              source=self.name, quality=10)

        snippets = []
        for r in results[:max_results]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            source_tag = r.get("source", "web")
            if snippet:
                snippets.append(f"[{source_tag}] {title}: {snippet}")
            elif title:
                snippets.append(f"[{source_tag}] {title}")

        combined = "\n".join(snippets)
        quality = min(80, 30 + len(results) * 8)
        return ToolResult(
            success=True, data=combined,
            source=f"隐身搜索({results[0].get('source', 'web')})",
            quality=quality,
            metadata={"result_count": len(results), "engine": results[0].get("source", "web")},
        )