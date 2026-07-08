"""
知识注入系统 - 从失败中学习
当模型因知识缺失而失败时，将正确答案存入知识库，下次直接检索
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
import hashlib
from infrastructure.database_manager import DatabaseManager


class KnowledgeInjector:
    """知识注入器 - 经验复用的核心"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        
        logger.info("知识注入器已初始化")
    
    def _init_db(self):
        """初始化知识库"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_hash TEXT UNIQUE,
                question TEXT,
                answer TEXT,
                source TEXT,
                intent_type TEXT,
                quality_score REAL,
                access_count INTEGER,
                last_accessed TEXT,
                created_at TEXT,
                metadata TEXT
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_question_hash ON knowledge_items(question_hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_intent_type ON knowledge_items(intent_type)')
    
    def _hash_question(self, question: str) -> str:
        """问题哈希（用于快速查找）"""
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def inject_knowledge(
        self,
        question: str,
        answer: str,
        source: str = "user_provided",
        intent_type: str = "unknown",
        metadata: Dict = None
    ) -> bool:
        """注入知识（从失败中学习）
        
        Args:
            question: 问题
            answer: 正确答案
            source: 知识来源（user_provided/tool_generated/web_search）
            intent_type: 意图类型
            metadata: 额外元数据
        
        Returns:
            是否成功
        """
        try:
            question_hash = self._hash_question(question)
            
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            conn.execute('''
                INSERT OR REPLACE INTO knowledge_items
                (question_hash, question, answer, source, intent_type,
                 quality_score, access_count, last_accessed, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_hash,
                question,
                answer,
                source,
                intent_type,
                100.0,  # 初始质量分满分
                0,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            
            logger.info(f"知识注入成功: {question[:50]}... (来源: {source})")
            return True
            
        except Exception as e:
            logger.error(f"知识注入失败: {e}")
            return False
    
    def retrieve_knowledge(
        self,
        question: str,
        intent_type: str = None,
        min_quality: float = 50.0
    ) -> Optional[Tuple[str, float]]:
        """检索知识（经验复用）
        
        Args:
            question: 问题
            intent_type: 意图类型（可选）
            min_quality: 最低质量分
        
        Returns:
            (答案, 置信度) 或 None
        """
        try:
            question_hash = self._hash_question(question)
            
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            if intent_type:
                cur = conn.execute('''
                    SELECT answer, quality_score, access_count
                    FROM knowledge_items
                    WHERE question_hash = ? AND intent_type = ? AND quality_score >= ?
                ''', (question_hash, intent_type, min_quality))
            else:
                cur = conn.execute('''
                    SELECT answer, quality_score, access_count
                    FROM knowledge_items
                    WHERE question_hash = ? AND quality_score >= ?
                ''', (question_hash, min_quality))
            
            row = cur.fetchone()
            
            if row:
                answer, quality, access_count = row
                
                # 更新访问计数
                conn.execute('''
                    UPDATE knowledge_items
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE question_hash = ?
                ''', (datetime.now().isoformat(), question_hash))
                
                # 置信度随访问次数提升（贝叶斯更新）
                confidence = min(0.95, 0.5 + access_count * 0.05)
                
                logger.info(f"知识检索成功: {question[:50]}... (置信度: {confidence:.2f})")
                return (answer, confidence)
            
            return None
            
        except Exception as e:
            logger.error(f"知识检索失败: {e}")
            return None
    
    def search_similar(
        self,
        question: str,
        limit: int = 5
    ) -> List[Dict]:
        """搜索相似问题（模糊匹配）
        
        Args:
            question: 问题
            limit: 返回数量
        
        Returns:
            相似问题列表
        """
        try:
            keywords = question.lower().split()[:5]
            
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            results = []
            
            for keyword in keywords:
                cur = conn.execute('''
                    SELECT question, answer, quality_score, source
                    FROM knowledge_items
                    WHERE question LIKE ? AND quality_score >= 50
                    ORDER BY quality_score DESC, access_count DESC
                    LIMIT ?
                ''', (f'%{keyword}%', limit))
                
                for row in cur.fetchall():
                    results.append({
                        "question": row[0],
                        "answer": row[1],
                        "quality": row[2],
                        "source": row[3]
                    })
            
            # 去重
            seen = set()
            unique_results = []
            for r in results:
                if r['question'] not in seen:
                    seen.add(r['question'])
                    unique_results.append(r)
            
            return unique_results[:limit]
                
        except Exception as e:
            logger.error(f"相似搜索失败: {e}")
            return []
    
    def update_quality(
        self,
        question: str,
        quality_delta: float
    ):
        """更新知识质量（用户反馈）
        
        Args:
            question: 问题
            quality_delta: 质量变化（+10 或 -10）
        """
        try:
            question_hash = self._hash_question(question)
            
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            conn.execute('''
                UPDATE knowledge_items
                SET quality_score = MAX(0, MIN(100, quality_score + ?))
                WHERE question_hash = ?
            ''', (quality_delta, question_hash))
            
            logger.debug(f"知识质量更新: {question[:30]}... ({quality_delta:+.1f})")
            
        except Exception as e:
            logger.error(f"质量更新失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            cur = conn.execute('SELECT COUNT(*) FROM knowledge_items')
            total = cur.fetchone()[0]
            
            cur = conn.execute('SELECT AVG(quality_score) FROM knowledge_items')
            avg_quality = cur.fetchone()[0] or 0
            
            cur = conn.execute('''
                SELECT source, COUNT(*) 
                FROM knowledge_items 
                GROUP BY source
            ''')
            by_source = dict(cur.fetchall())
            
            return {
                "total_knowledge": total,
                "avg_quality": round(avg_quality, 2),
                "by_source": by_source
            }
                
        except Exception as e:
            logger.error(f"统计获取失败: {e}")
            return {}


knowledge_injector = KnowledgeInjector()
