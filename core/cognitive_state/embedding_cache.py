"""
经验池 embedding 预计算缓存 + CSS 列选择

核心理念（来自王虹 NeurIPS 2019 论文）：
- 列子集选择（Column Subset Selection）：从矩阵中选出代表性列
- 映射到经验池：选出语义覆盖最广的 K 条经验
- 在线检索时只需计算查询 embedding + 与 K 条预计算 embedding 比较

三层架构：
1. EmbeddingCache — 预计算并持久化经验的 embedding
2. CSSSelector — 从经验池选出代表性子集（贪心最大体积）
3. 集成到 CognitiveResidual._semantic_retrieve()
"""
import time
import hashlib
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class EmbeddingCache:
    """经验池 embedding 预计算缓存"""

    def __init__(self, db_path: str = "data/embedding_cache.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                experience_hash TEXT PRIMARY KEY,
                experience_text TEXT,
                embedding BLOB,
                dim INTEGER,
                created_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def _hash_text(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get(self, text: str) -> Optional[np.ndarray]:
        key = self._hash_text(text)
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cur = conn.execute(
                "SELECT embedding, dim FROM embedding_cache WHERE experience_hash = ?",
                (key,)
            )
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return np.frombuffer(row[0], dtype=np.float32).reshape(-1)
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return None

    def put(self, text: str, embedding: np.ndarray) -> None:
        key = self._hash_text(text)
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT OR REPLACE INTO embedding_cache (experience_hash, experience_text, embedding, dim, created_at) VALUES (?, ?, ?, ?, ?)",
                (key, text[:500], embedding.astype(np.float32).tobytes(), len(embedding), time.time())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"embedding缓存写入失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            row = conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()
            conn.close()
            return {"cached_count": row[0]}
        except Exception:
            return {"cached_count": 0}


class CSSSelector:
    """
    列子集选择器 — 从经验池选出语义覆盖最广的 K 条经验

    算法：贪心最大体积（Greedy Maximum Volume）
    每次选择与已选集合正交分量最大的经验，确保覆盖最广的语义空间。
    这比按 quality_score 排序更接近 CSS 的理论保证。
    """

    def __init__(self, cache: EmbeddingCache, subset_size: int = 30):
        self._cache = cache
        self._subset_size = subset_size
        self._selected_indices: List[int] = []
        self._selected_embeddings: List[np.ndarray] = []
        self._selected_texts: List[str] = []
        self._last_rebuild_time: float = 0
        self._rebuild_interval: float = 3600.0

    def get_subset(self, force_rebuild: bool = False) -> Tuple[List[str], List[np.ndarray]]:
        if not force_rebuild and self._selected_texts:
            if time.time() - self._last_rebuild_time < self._rebuild_interval:
                return self._selected_texts, self._selected_embeddings
        self._rebuild()
        return self._selected_texts, self._selected_embeddings

    def _rebuild(self) -> None:
        logger.info(f"🧮 CSS选择器: 重建代表性子集 (K={self._subset_size})")
        try:
            db = DatabaseManager.get("data/experience_pool.db")
            rows = db.query(
                "SELECT raw_input, response, quality_score FROM experiences ORDER BY quality_score DESC LIMIT 200"
            )
        except Exception as e:
            logger.warning(f"CSS选择器: 经验池读取失败: {e}")
            return

        if not rows:
            return

        candidates: List[Tuple[str, np.ndarray]] = []
        for row in rows:
            text = (row[0] or "")[:200]
            if not text:
                continue
            emb = self._cache.get(text)
            if emb is not None:
                candidates.append((text, emb))

        if len(candidates) < self._subset_size:
            self._selected_texts = [c[0] for c in candidates]
            self._selected_embeddings = [c[1] for c in candidates]
            self._last_rebuild_time = time.time()
            logger.info(f"🧮 CSS选择器: 缓存命中不足({len(candidates)}), 全部使用")
            return

        selected = self._greedy_select(candidates)

        self._selected_texts = [candidates[i][0] for i in selected]
        self._selected_embeddings = [candidates[i][1] for i in selected]
        self._last_rebuild_time = time.time()
        logger.info(f"🧮 CSS选择器: 从{len(candidates)}条中选出{len(selected)}条代表性经验")

    def _greedy_select(self, candidates: List[Tuple[str, np.ndarray]]) -> List[int]:
        """贪心最大体积选择"""
        K = min(self._subset_size, len(candidates))
        selected: List[int] = []
        residual_norms = np.array([
            np.linalg.norm(c[1]) for c in candidates
        ])

        first = int(np.argmax(residual_norms))
        selected.append(first)

        Q = candidates[first][1].reshape(1, -1)

        for _ in range(1, K):
            projections = np.zeros(len(candidates))
            for idx in range(len(candidates)):
                if idx in selected:
                    projections[idx] = -1.0
                    continue
                v = candidates[idx][1]
                proj = np.linalg.norm(v @ Q.T) / (np.linalg.norm(v) + 1e-8)
                projections[idx] = 1.0 - proj

            best = int(np.argmax(projections))
            if projections[best] <= 0.01:
                break
            selected.append(best)
            Q = np.vstack([Q, candidates[best][1].reshape(1, -1)])

        return selected

    def get_status(self) -> Dict[str, Any]:
        return {
            "subset_size": len(self._selected_texts),
            "target_size": self._subset_size,
            "last_rebuild": self._last_rebuild_time,
            "cache_stats": self._cache.get_stats(),
        }


def precompute_experience_embeddings(batch_size: int = 100, max_items: int = 500) -> int:
    """离线预计算经验池 embedding — 供 lifespan 启动时或定时任务调用"""
    logger.info(f"🧮 开始预计算经验池 embedding (batch={batch_size}, max={max_items})")
    cache = EmbeddingCache()
    stats = cache.get_stats()
    already_cached = stats["cached_count"]

    try:
        db = DatabaseManager.get("data/experience_pool.db")
        rows = db.query(
            "SELECT raw_input FROM experiences ORDER BY quality_score DESC LIMIT ?",
            (max_items,)
        )
    except Exception as e:
        logger.error(f"预计算: 经验池读取失败: {e}")
        return 0

    computed = 0
    failed = 0
    total_rows = 0
    for row in rows:
        total_rows += 1
        try:
            text = str(row[0] or "")[:200]
        except Exception:
            continue
        if not text or len(text) < 5:
            failed += 1
            continue
        cached = cache.get(text)
        if cached is not None:
            continue
        try:
            from core.shared_embedding import get_embeddings
            emb = get_embeddings([text])
            if emb is not None and hasattr(emb, '__len__') and len(emb) > 0:
                cache.put(text, emb[0])
                computed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            continue
        if computed >= batch_size:
            break

    logger.info(f"🧮 预计算完成: 新计算={computed}, 失败={failed}, 总行={total_rows}")
    return computed