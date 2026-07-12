import asyncio
from typing import Optional
from loguru import logger
from backend.services.path_handlers._shared import _fast_executor


async def fetch_fact_assertions(query: str) -> Optional[dict]:
    """路径G：事实锚点查询"""
    try:
        from infrastructure.fact_store import fact_store
        loop = asyncio.get_running_loop()
        facts = await asyncio.wait_for(
            loop.run_in_executor(_fast_executor, lambda: fact_store.search_by_keywords(query, limit=5)),
            timeout=5
        )
        if facts:
            parts = []
            for fa in facts:
                parts.append(f"{fa['subject']} {fa['predicate']} {fa['object']} (置信度{fa['confidence']:.0%})")
            return {"source": "事实锚点", "response": "【事实锚点】\n" + "\n".join(f"- {p}" for p in parts), "quality": 70}
    except Exception as e:
        logger.error(f"事实锚点查询异常: {e}")
    return None