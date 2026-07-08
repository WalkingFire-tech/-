"""
领域知识学习器 - 语义驱动版

核心设计：
1. 所有领域知识存储在知识库中，代码零硬编码
2. 使用语义嵌入进行领域匹配（不依赖关键词）
3. 学习机制：用户纠正 → 提取语义 → 存入知识库
4. 兼容降级：无嵌入模型时使用知识库关键词查询
"""

import json
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from infrastructure.database_manager import DatabaseManager


class DomainKnowledgeLearner:
    """
    语义驱动的领域知识学习器
    
    不写死任何关键词，所有知识从数据库动态加载。
    """

    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self._embedding_model = None
        self._embedding_available = False
        
        Path(self.db_path).parent.mkdir(exist_ok=True)
        self._init_database()
        self._init_embedding()
        
        logger.info("📚 语义领域学习器已初始化")

    def _init_database(self):
        """初始化数据库"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS domain_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE,
                semantic_vector TEXT,
                sample_queries TEXT,
                confidence REAL,
                occurrences INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS type_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT,
                target_type TEXT,
                similarity REAL,
                confidence REAL,
                created_at TEXT
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                correct_domain TEXT,
                wrong_domain TEXT,
                confidence REAL,
                learned_at TEXT
            )
        ''')

    def _init_embedding(self):
        """初始化语义嵌入模型（延迟加载）"""
        try:
            import os
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            from sentence_transformers import SentenceTransformer
            import numpy as np

            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._embedding_available = True
            logger.info("✅ 语义嵌入模型已加载")
        except ImportError:
            logger.warning("⚠️ sentence_transformers 未安装，使用降级模式")
            self._embedding_available = False
        except Exception as e:
            logger.warning(f"⚠️ 嵌入模型加载失败: {e}")
            self._embedding_available = False

    def detect_domain(self, query: str) -> Tuple[Optional[str], float]:
        """
        检测查询所属领域（语义驱动）
        
        Returns:
            (domain, confidence) 或 (None, 0.0)
        """
        if self._embedding_available:
            result = self._detect_by_semantic(query)
            if result and result[1] > 0.55:
                return result

        return self._detect_by_keyword(query)

    def _detect_by_semantic(self, query: str) -> Tuple[Optional[str], float]:
        """使用语义向量进行领域匹配"""
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            query_vec = self._embedding_model.encode(query)

            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            cursor = conn.execute(
                "SELECT domain, semantic_vector FROM domain_knowledge WHERE semantic_vector IS NOT NULL"
            )
            rows = cursor.fetchall()

            if not rows:
                return None, 0.0

            best_domain = None
            best_score = 0.0

            for domain, vector_json in rows:
                domain_vec = np.array(json.loads(vector_json))
                score = cosine_similarity([query_vec], [domain_vec])[0][0]
                if score > best_score:
                    best_score = score
                    best_domain = domain

            return best_domain, float(best_score)

        except Exception as e:
            logger.debug(f"语义匹配失败: {e}")
            return None, 0.0

    def _detect_by_keyword(self, query: str) -> Tuple[Optional[str], float]:
        """关键词降级匹配（从知识库查询）"""
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            cursor = conn.execute(
                "SELECT domain, sample_queries FROM domain_knowledge"
            )
            rows = cursor.fetchall()

            query_lower = query.lower()
            best_domain = None
            best_score = 0.0

            for domain, sample_queries_json in rows:
                if not sample_queries_json:
                    continue
                sample_queries = json.loads(sample_queries_json)
                for sample in sample_queries:
                    if sample.lower() in query_lower:
                        score = len(sample) / max(len(query), 1)
                        if score > best_score:
                            best_score = min(score * 2, 0.7)
                            best_domain = domain

            return best_domain, best_score

        except Exception as e:
            logger.debug(f"关键词匹配失败: {e}")
            return None, 0.0

    def learn_from_correction(
        self,
        query: str,
        correct_domain: str,
        wrong_domain: Optional[str] = None,
        confidence: float = 0.7
    ):
        """
        从用户纠正中学习（语义驱动）

        Args:
            query: 用户查询
            correct_domain: 正确的领域
            wrong_domain: 错误的领域（可选）
            confidence: 置信度
        """
        vector_json = None
        if self._embedding_available:
            try:
                import numpy as np
                vec = self._embedding_model.encode(query)
                vector_json = json.dumps(vec.tolist())
            except Exception as e:
                logger.warning(f"向量生成失败: {e}")

        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        cursor = conn.execute(
            "SELECT id, semantic_vector, sample_queries, occurrences FROM domain_knowledge WHERE domain = ?",
            (correct_domain,)
        )
        row = cursor.fetchone()

        if row:
            existing_queries = json.loads(row[2]) if row[2] else []
            if query not in existing_queries:
                existing_queries.append(query)
            if len(existing_queries) > 20:
                existing_queries = existing_queries[-20:]

            conn.execute('''
                UPDATE domain_knowledge
                SET semantic_vector = ?,
                    sample_queries = ?,
                    occurrences = occurrences + 1,
                    confidence = ?,
                    updated_at = ?
                WHERE domain = ?
            ''', (
                vector_json or row[1],
                json.dumps(existing_queries, ensure_ascii=False),
                min(1.0, confidence + 0.05 * row[3]),
                datetime.now().isoformat(),
                correct_domain
            ))
        else:
            conn.execute('''
                INSERT INTO domain_knowledge
                (domain, semantic_vector, sample_queries, confidence, occurrences, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                correct_domain,
                vector_json,
                json.dumps([query], ensure_ascii=False),
                confidence,
                1,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

        conn.execute('''
            INSERT INTO learning_history
            (query, correct_domain, wrong_domain, confidence, learned_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            query,
            correct_domain,
            wrong_domain,
            confidence,
            datetime.now().isoformat()
        ))

        conn.commit()

        logger.info(f"📚 学习: '{query[:30]}...' → {correct_domain} (置信度: {confidence:.2f})")

    def get_domain_stats(self) -> Dict:
        """获取领域统计"""
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            cursor = conn.execute('''
                SELECT domain, occurrences, confidence, updated_at
                FROM domain_knowledge
                ORDER BY occurrences DESC
            ''')
            domains = cursor.fetchall()

            cursor = conn.execute("SELECT COUNT(*) FROM learning_history")
            total_learned = cursor.fetchone()[0]

            return {
                "total_domains": len(domains),
                "total_learned": total_learned,
                "domains": [
                    {"domain": d[0], "occurrences": d[1], "confidence": d[2], "updated": d[3]}
                    for d in domains[:10]
                ]
            }
        except Exception as e:
            logger.error(f"获取领域统计失败: {e}")
            return {"total_domains": 0, "total_learned": 0, "domains": []}

    def get_learning_history(self, limit: int = 20) -> List[Dict]:
        """获取学习历史"""
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            cursor = conn.execute('''
                SELECT query, correct_domain, wrong_domain, confidence, learned_at
                FROM learning_history
                ORDER BY learned_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取学习历史失败: {e}")
            return []


domain_learner = DomainKnowledgeLearner()
