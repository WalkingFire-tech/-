import asyncio
from loguru import logger
from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
from infrastructure.database_manager import DatabaseManager


async def fetch_knowledge(query: str) -> dict:
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
                        pass
                    return result
        except asyncio.TimeoutError:
            logger.warning("知识库向量检索超时(10秒)")
        except Exception as e:
            logger.debug(f"知识库向量检索降级: {e}")
    
    try:
        loop = asyncio.get_running_loop()
        def _query_know():
            db = DatabaseManager.get("data/knowledge_store.db")

            conn = db._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query[:30]}%",))
            row = cursor.fetchone()
            conn.close()
            return row
        row = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_know), timeout=5)
        if row and len(row[0]) > 30:
            return {"source": "知识库", "response": row[0], "quality": 60}
    except Exception:
        pass
    return None