import asyncio
import re
from loguru import logger
from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
from core.ports.adapters import get_storage_port


def _extract_keywords(query: str, max_kw: int = 8) -> list:
    _stop_pattern = re.compile(r'什么是|如何|为什么|是不是|能不能|有没有|好不好|说一下|讲一下|请问|告诉|知道|帮忙|帮助|解释|描述|可以|能够')
    cleaned = _stop_pattern.sub(' ', query)
    cleaned = re.sub(r'[？?！!。，,、；;：:""''（）()\[\]【】\s]+', ' ', cleaned)
    segments = re.split(r'\s+', cleaned.strip())
    tokens = []
    _meaningless_2g = {"什么", "怎么", "如何", "为什么", "可以", "能够", "告诉", "知道", "的话", "的话", "一个", "这个", "那个", "就是", "不是", "没有", "已经", "我们", "他们", "因为", "所以", "但是", "如果", "虽然", "而且", "或者", "以及", "之后", "之前", "关于", "通过", "进行", "使用", "需要", "应该", "可能", "已经", "还是", "什么"}
    for seg in segments:
        if not seg:
            continue
        if re.match(r'^[a-zA-Z0-9]{1,}$', seg):
            tokens.append(seg)
        else:
            cn_chars = re.findall(r'[\u4e00-\u9fff]+', seg)
            for chunk in cn_chars:
                if len(chunk) >= 4:
                    tokens.append(chunk[:6])
                if len(chunk) >= 3:
                    for i in range(len(chunk) - 2):
                        g3 = chunk[i:i+3]
                        if not any(s in g3 for s in _meaningless_2g):
                            tokens.append(g3)
                for i in range(len(chunk) - 1):
                    g2 = chunk[i:i+2]
                    if g2 not in _meaningless_2g and not g2.startswith("的") and not g2.endswith("的"):
                        tokens.append(g2)
            for m in re.finditer(r'[a-zA-Z0-9]{2,}', seg):
                tokens.append(m.group())
    seen = set()
    unique = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:max_kw]


def _build_keyword_sql(keywords: list) -> tuple:
    if not keywords:
        return "", []
    conditions = " OR ".join(["raw_input LIKE ?" for _ in keywords])
    params = [f"%{kw}%" for kw in keywords]
    return conditions, params


def _decay_order() -> str:
    """经验池排序：quality_score * 时间衰减因子，7天半衰期"""
    return "quality_score * EXP(-0.1 * (julianday('now') - julianday(timestamp))) DESC"


_EXCLUDED_INTENT_TYPES = ("autonomous_reflection", "metacognitive_background", "background_collect")


def _intent_filter() -> str:
    """排除系统自言自语类型的经验"""
    excludes = ", ".join(f"'{t}'" for t in _EXCLUDED_INTENT_TYPES)
    return f"intent_type NOT IN ({excludes})"


def get_last_response(query: str) -> str:
    """获取最近一次交互的回复（用于质疑检测）"""
    try:
        db = get_storage_port("data/experience_pool.db")
        rows = db.query("SELECT response FROM experiences ORDER BY timestamp DESC LIMIT 1")
        if rows and rows[0][0] and len(rows[0][0]) > 20:
            return rows[0][0]
    except Exception as e:
        logger.error(f"获取上一轮回复失败: {e}")
    return ""


def _get_experience_port():
    try:
        from core.ports.adapters import get_experience_port
        port = get_experience_port()
        if port.is_available():
            return port
    except Exception as e:
        logger.warning(f"操作降级跳过: {e}")
    return None


async def fetch_experience(query: str, ports: dict = None) -> dict:
    exp_port = None
    if ports and ports.get("experience"):
        exp_port = ports["experience"]
    if exp_port is None:
        exp_port = _get_experience_port()
    if exp_port and exp_port.is_available():
        try:
            results = await exp_port.search(query, top_k=3)
            if results:
                best = results[0]
                text = best.get("response", "") or best.get("text", "")
                prob = best.get("probability", best.get("quality_score", 0) / 100.0)
                if text and len(text) > 30:
                    return {"source": "经验池(端口)", "response": text, "quality": min(int(prob * 100), 95),
                            "retrieval_probability": prob}
        except Exception as e:
            logger.debug(f"端口经验检索跳过: {e}")
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
                        logger.warning("操作降级跳过")
                    return result
        except asyncio.TimeoutError:
            logger.warning("向量检索超时(10秒)")
        except Exception as e:
            logger.warning(f"向量检索降级: {e}")
    
    try:
        loop = asyncio.get_running_loop()
        def _query_exp():
            db = get_storage_port("data/experience_pool.db")
            kws = _extract_keywords(query)
            if kws:
                cond, params = _build_keyword_sql(kws)
                rows = db.query(
                    f"SELECT response, quality_score FROM experiences WHERE {cond} AND {_intent_filter()} ORDER BY {_decay_order()} LIMIT 5",
                    tuple(params)
                )
            else:
                rows = db.query(f"SELECT response, quality_score FROM experiences WHERE raw_input LIKE ? AND {_intent_filter()} ORDER BY {_decay_order()} LIMIT 3", (f"%{query[:20]}%",))
            return rows
        rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_exp), timeout=5)
        if rows:
            relevant = [(r, r[1] or 50) for r in rows if r[0] and len(r[0]) > 30 and _keyword_overlap(query, r[0] or "")]
            if relevant:
                best = max(relevant, key=lambda x: x[1])
                result = {"source": "经验池", "response": best[0][0], "quality": best[1]}
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
                    logger.warning("操作降级跳过")
                return result
    except Exception:
        logger.warning("操作降级跳过")
    return None


def _keyword_overlap(query_text: str, candidate_text: str, min_ratio: float = 0.10) -> bool:
    """检查查询与候选文本的关键词重叠率，低于阈值视为不相关"""
    q_kws = set(_extract_keywords(query_text, max_kw=16))
    c_kws = set(_extract_keywords(candidate_text, max_kw=16))
    if not q_kws:
        return True
    overlap = len(q_kws & c_kws)
    return overlap / len(q_kws) >= min_ratio


def get_experience_context(query: str) -> str:
    """从经验池检索相似问题的历史回复，作为Ollama的上下文注入"""
    try:
        db = get_storage_port("data/experience_pool.db")
        kws = _extract_keywords(query)
        if kws:
            cond, params = _build_keyword_sql(kws)
            rows = db.query(
                f"SELECT raw_input, response, quality_score FROM experiences WHERE {cond} AND {_intent_filter()} ORDER BY {_decay_order()} LIMIT 10",
                tuple(params)
            )
        else:
            rows = db.query(
                f"SELECT raw_input, response, quality_score FROM experiences WHERE raw_input LIKE ? AND {_intent_filter()} ORDER BY {_decay_order()} LIMIT 5",
                (f"%{query[:20]}%",)
            )
        if rows:
            context_parts = []
            for row in rows:
                if row[1] and len(row[1]) > 30 and (row[2] or 0) >= 50:
                    if _keyword_overlap(query, row[0] or ""):
                        context_parts.append(f"之前对类似问题「{row[0][:40]}」的回答：{row[1][:200]}")
                        if len(context_parts) >= 3:
                            break
            if context_parts:
                return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"经验池上下文检索失败: {e}")
    return ""