import asyncio
from loguru import logger
from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
from core.ports.adapters import get_storage_port


def _get_vector_port():
    try:
        from core.ports.adapters import get_vector_store_port
        port = get_vector_store_port()
        if port.is_available():
            return port
    except Exception as e:
        logger.warning(f"操作降级跳过: {e}")
    return None


async def fetch_knowledge(query: str, ports: dict = None) -> dict:
    vector_port = None
    if ports and ports.get("vector_store"):
        vector_port = ports["vector_store"]
    if vector_port is None:
        vector_port = _get_vector_port()
    if vector_port and vector_port.is_available():
        try:
            results = await vector_port.search(query, k=3, threshold=0.3)
            if results:
                best = results[0]
                text = best.get("text", "")
                prob = best.get("probability", 0)
                if text and len(text) > 30:
                    return {"source": "知识库(向量/端口)", "response": text, "quality": min(int(prob * 100), 90),
                            "retrieval_probability": prob, "retrieval_entropy": best.get("query_entropy", 0.5)}
        except Exception as e:
            logger.debug(f"端口向量检索跳过: {e}")
    if _check_vector_available():
        try:
            from infrastructure.vector_retriever import vector_retriever
            loop = asyncio.get_running_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: vector_retriever.search_similar(query, k=3, threshold=0.3)),
                timeout=10
            )
            if results:
                best = results[0]
                text = best.get("text", "")
                prob = best.get("probability", 0)
                if text and len(text) > 30:
                    result = {"source": "知识库(向量)", "response": text, "quality": min(int(prob * 100), 90),
                              "retrieval_probability": prob, "retrieval_entropy": best.get("query_entropy", 0.5)}
                    try:
                        from core.dynamic_probability_field import dynamic_probability_field
                        if dynamic_probability_field._candidates:
                            dynamic_probability_field.update({
                                "type": "support", "confidence": prob,
                                "source": "知识库(向量)", "content": text[:300],
                            })
                    except Exception:
                        logger.warning("操作降级跳过")
                    return result
        except asyncio.TimeoutError:
            logger.warning("知识库向量检索超时(10秒)")
        except Exception as e:
            logger.warning(f"知识库向量检索降级: {e}")
    
    try:
        loop = asyncio.get_running_loop()
        def _query_know():
            db = get_storage_port("data/knowledge_store.db")

            safe_query = query[:200]
            row = db.query_one("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{safe_query}%",))
            if row:
                return row
            keywords = [w for w in safe_query.replace("，", " ").replace("。", " ").replace("？", " ").replace("、", " ").split() if len(w) >= 2]
            if keywords:
                conditions = " OR ".join(["content LIKE ?" for _ in keywords[:5]])
                params = [f"%{kw}%" for kw in keywords[:5]]
                row = db.query_one(f"SELECT content FROM knowledge WHERE {conditions} LIMIT 1", tuple(params))
            return row
        row = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_know), timeout=5)
        if row and len(row[0]) > 30:
            return {"source": "知识库", "response": row[0], "quality": 60}
    except Exception:
        logger.warning("操作降级跳过")
    return None