import asyncio
from loguru import logger
from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
from infrastructure.database_manager import DatabaseManager


def get_last_response(query: str) -> str:
    """获取最近一次交互的回复（用于质疑检测）"""
    try:
        db = DatabaseManager.get("data/experience_pool.db")
        rows = db.query("SELECT response FROM experiences ORDER BY timestamp DESC LIMIT 1")
        if rows and rows[0][0] and len(rows[0][0]) > 20:
            return rows[0][0]
    except Exception as e:
        logger.debug(f"获取上一轮回复失败: {e}")
    return ""


async def fetch_experience(query: str) -> dict:
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
                    result = {"source": "经验池(向量)", "response": text, "quality": min(int(prob * 100), 95),
                              "retrieval_probability": prob, "retrieval_entropy": best.get("query_entropy", 0.5)}
                    try:
                        from core.dynamic_probability_field import dynamic_probability_field
                        if dynamic_probability_field._candidates:
                            dynamic_probability_field.update({
                                "type": "support", "confidence": prob,
                                "source": "经验池(向量)", "content": text[:300],
                            })
                    except Exception:
                        pass
                    return result
        except asyncio.TimeoutError:
            logger.warning("向量检索超时(10秒)")
        except Exception as e:
            logger.debug(f"向量检索降级: {e}")
    
    try:
        loop = asyncio.get_running_loop()
        def _query_exp():
            db = DatabaseManager.get("data/experience_pool.db")
            rows = db.query("SELECT response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY timestamp DESC LIMIT 3", (f"%{query[:20]}%",))
            return rows
        rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_exp), timeout=5)
        if rows:
            best = max(rows, key=lambda r: r[1] if r[1] else 50)
            if best[0] and len(best[0]) > 30:
                result = {"source": "经验池", "response": best[0], "quality": best[1] or 50}
                try:
                    from core.trajectory_evolution import trajectory_store
                    similar_trajs = trajectory_store.find_similar_trajectories(query, min_fitness=60, limit=1)
                    if similar_trajs:
                        best_traj = similar_trajs[0]
                        traj_steps = best_traj.get('steps', [])
                        if traj_steps:
                            successful_phases = [s['phase'] for s in traj_steps if s.get('success')]
                            if successful_phases:
                                result["trajectory_hint"] = f"历史最优路径: {'→'.join(successful_phases[:6])}"
                except Exception:
                    pass
                return result
    except Exception:
        pass
    return None


def get_experience_context(query: str) -> str:
    """从经验池检索相似问题的历史回复，作为Ollama的上下文注入"""
    try:
        db = DatabaseManager.get("data/experience_pool.db")
        rows = db.query(
            "SELECT raw_input, response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY quality_score DESC, timestamp DESC LIMIT 2",
            (f"%{query[:20]}%",)
        )
        if rows:
            context_parts = []
            for row in rows:
                if row[1] and len(row[1]) > 30 and (row[2] or 0) >= 50:
                    context_parts.append(f"之前对类似问题「{row[0][:40]}」的回答：{row[1][:200]}")
            if context_parts:
                return "\n".join(context_parts)
    except Exception as e:
        logger.debug(f"经验池上下文检索失败: {e}")
    return ""