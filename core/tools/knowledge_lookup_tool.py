import asyncio
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class KnowledgeLookupTool(ToolInterface):
    @property
    def name(self) -> str:
        return "knowledge_lookup"

    @property
    def description(self) -> str:
        return "知识库查询：从本地知识库检索相关知识条目"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "查询问题", "required": True},
        }

    @property
    def timeout(self) -> float:
        return 8.0

    @property
    def category(self) -> str:
        return "knowledge"

    @property
    def priority(self) -> int:
        return 60

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        knowledge_intents = {"knowledge", "factual", "definition", "explanation"}
        return intent_type in knowledge_intents or len(query) > 5

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="查询不能为空", source=self.name)

        results = []

        try:
            def _search_experience():
                from infrastructure.smart_experience_pool import smart_experience_pool
                return smart_experience_pool.search(query, top_k=3)
            exp_results = await run_tool_async(_search_experience, timeout=5)
            if exp_results:
                for exp in exp_results:
                    if isinstance(exp, dict) and exp.get("response"):
                        results.append(exp)
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from infrastructure.database_manager import DatabaseManager
            def _search_kb():
                db = DatabaseManager.get("data/knowledge_store.db", timeout=3)
                try:
                    rows = db.query(
                        "SELECT answer, source, quality_score FROM knowledge_items "
                        "WHERE question LIKE ? OR answer LIKE ? ORDER BY quality_score DESC LIMIT 5",
                        (f"%{query}%", f"%{query}%")
                    )
                    return [dict(zip(["content", "source", "quality"], row))
                            for row in rows]
                finally:
                    pass

            kb_results = await run_tool_async(_search_kb, timeout=5)
            if kb_results:
                for item in kb_results:
                    results.append({
                        "response": item["content"],
                        "source": f"知识库({item.get('source', 'unknown')})",
                        "quality": item.get("quality", 50),
                    })
        except Exception:
            logger.warning("操作降级跳过")

        if not results:
            return ToolResult(success=False, error="知识库中未找到相关信息",
                              source=self.name, quality=10)

        best = max(results, key=lambda r: r.get("quality", 0))
        quality = min(80, best.get("quality", 40))
        return ToolResult(
            success=True, data=best["response"],
            source=best.get("source", "知识库"),
            quality=quality,
            metadata={"total_found": len(results)},
        )