import asyncio
from typing import Optional
from loguru import logger
from backend.services.path_handlers._shared import _fast_executor


def _get_fact_port():
    try:
        from core.ports.adapters import get_fact_store_port
        port = get_fact_store_port()
        if port.is_available():
            return port
    except Exception:
        pass
    return None


async def fetch_fact_assertions(query: str, ports: dict = None) -> Optional[dict]:
    """路径G：事实锚点查询 — 端口优先，基础设施降级"""
    try:
        fact_port = None
        if ports and ports.get("fact_store"):
            fact_port = ports["fact_store"]
        if fact_port is None:
            fact_port = _get_fact_port()
        if fact_port and fact_port.is_available():
            facts = await fact_port.search_by_keywords(query, limit=5)
        else:
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