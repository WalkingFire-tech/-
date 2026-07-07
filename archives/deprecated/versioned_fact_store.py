"""
版本控制事实存储
支持知识版本追溯、覆盖机制、冲突解决
"""
import sqlite3
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class FactAssertion:
    """事实断言数据结构"""
    subject: str
    predicate: str
    object: str
    source: str
    confidence: float = 0.8
    is_seed: bool = False
    version: int = 1
    is_active: bool = True
    superseded_by: Optional[int] = None


class VersionedFactStore:
    """
    支持版本控制的事实存储
    
    核心能力：
    1. 追踪每个断言的历史版本
    2. 标记被覆盖的断言
    3. 查询任意时间点的知识状态
    4. 回滚到指定版本
    """
    
    def __init__(self, db_path: str = "data/alliance.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
    
    def _init_tables(self):
        """初始化表结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 读取迁移脚本并执行
            migration_path = Path(__file__).parent.parent / "migrations" / "004_versioned_fact_store.sql"
            if migration_path.exists():
                with open(migration_path, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
                logger.info(f"📚 版本控制事实库已初始化: {self.db_path}")
            else:
                # 直接创建表结构
                self._create_tables_directly(conn)
    
    def _create_tables_directly(self, conn):
        """直接创建表结构（备用）"""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fact_assertions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                question_hash TEXT NOT NULL,
                question TEXT,
                source TEXT NOT NULL,
                confidence REAL DEFAULT 0.8,
                is_seed BOOLEAN DEFAULT 0,
                version INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                superseded_by INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        conn.execute('CREATE INDEX IF NOT EXISTS idx_fact_qhash_active ON fact_assertions(question_hash, is_active)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_fact_subject_predicate ON fact_assertions(subject, predicate)')
        
        logger.info(f"📚 版本控制事实库已初始化: {self.db_path}")
    
    @staticmethod
    def _hash_question(question: str) -> str:
        """生成问题的哈希"""
        normalized = question.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def add_assertion(
        self,
        question: str,
        subject: str,
        predicate: str,
        obj: str,
        source: str = "manual",
        confidence: float = 0.8,
        is_seed: bool = False,
        override_strategy: str = "confidence"
    ) -> Tuple[int, str]:
        """
        添加断言，自动处理冲突和版本控制
        
        Args:
            question: 关联的问题
            subject: 主语
            predicate: 谓语
            obj: 宾语
            source: 来源 ('seed', 'correction', 'learning', 'external', 'manual')
            confidence: 置信度
            is_seed: 是否为种子数据
            override_strategy: 覆盖策略 ('confidence' | 'user' | 'keep')
        
        Returns:
            (assertion_id, action) 其中action为 'inserted', 'overridden', 'kept'
        """
        q_hash = self._hash_question(question)
        
        # 查找当前有效的相同断言
        existing = self._find_active_assertion(q_hash, subject, predicate)
        
        if existing is None:
            # 无冲突，直接插入
            new_id = self._insert_new_assertion(
                q_hash, question, subject, predicate, obj,
                source, confidence, is_seed
            )
            logger.info(f"✅ 新断言已插入: ({subject}, {predicate}, {obj})")
            return new_id, "inserted"
        
        # 存在冲突，决定是否覆盖
        should_override = self._resolve_conflict(existing, {
            'subject': subject,
            'predicate': predicate,
            'object': obj,
            'source': source,
            'confidence': confidence,
            'is_seed': is_seed
        }, override_strategy)
        
        if should_override:
            # 覆盖：旧版本标记为不活跃，插入新版本
            new_version = existing['version'] + 1
            
            # 插入新版本
            new_id = self._insert_new_assertion(
                q_hash, question, subject, predicate, obj,
                source, confidence, is_seed,
                version=new_version
            )
            
            # 标记旧版本被覆盖
            self._mark_as_superseded(existing['id'], new_id)
            
            # 记录纠错历史
            self._record_correction_history(
                q_hash, existing['id'], new_id,
                existing, obj, source
            )
            
            logger.info(
                f"🔄 断言覆盖: ({subject}, {predicate}, {existing['object']}) "
                f"→ ({subject}, {predicate}, {obj}) [版本{new_version}]"
            )
            return new_id, "overridden"
        else:
            logger.info(f"⏸️ 断言保留: ({subject}, {predicate}, {existing['object']})")
            return existing['id'], "kept"
    
    def _find_active_assertion(self, q_hash: str, subject: str, predicate: str) -> Optional[Dict]:
        """查找当前有效的断言"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT id, subject, predicate, object, source, confidence, version, is_seed
                FROM fact_assertions
                WHERE question_hash = ? 
                  AND subject = ? 
                  AND predicate = ? 
                  AND is_active = 1
                ORDER BY version DESC
                LIMIT 1
            """, (q_hash, subject, predicate)).fetchone()
            return dict(row) if row else None
    
    def _insert_new_assertion(
        self,
        q_hash: str,
        question: str,
        subject: str,
        predicate: str,
        obj: str,
        source: str,
        confidence: float,
        is_seed: bool,
        version: int = 1
    ) -> int:
        """插入新断言"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                INSERT INTO fact_assertions 
                (question_hash, question, subject, predicate, object, source, confidence, is_seed, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (q_hash, question, subject, predicate, obj, source, confidence, is_seed, version))
            return cur.lastrowid
    
    def _mark_as_superseded(self, old_id: int, new_id: int):
        """标记旧断言被覆盖"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE fact_assertions 
                SET is_active = 0, superseded_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_id, old_id))
    
    def _record_correction_history(
        self,
        q_hash: str,
        old_id: int,
        new_id: int,
        old_assertion: Dict,
        new_obj: str,
        source: str
    ):
        """记录纠错历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO correction_history
                (question_hash, old_assertion_id, new_assertion_id, old_content, new_content,
                 correction_source, confidence_before, confidence_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q_hash, old_id, new_id,
                f"({old_assertion['subject']}, {old_assertion['predicate']}, {old_assertion['object']})",
                f"({old_assertion['subject']}, {old_assertion['predicate']}, {new_obj})",
                source, old_assertion['confidence'], old_assertion.get('confidence', 0.8)
            ))
    
    def _resolve_conflict(self, existing: Dict, new: Dict, strategy: str) -> bool:
        """
        冲突解决策略
        返回 True 表示覆盖
        
        策略说明：
        - user: 用户纠错永远优先
        - confidence: 置信度高的优先
        - keep: 保留旧版本
        """
        if strategy == "user":
            # 用户纠错永远优先
            if new['source'] == 'correction':
                return True
            if existing['source'] == 'correction':
                return False
            return new['confidence'] > existing['confidence']
        
        elif strategy == "confidence":
            if new['confidence'] > existing['confidence']:
                return True
            elif new['confidence'] < existing['confidence']:
                return False
            else:
                # 置信度相等时，学习来源优先于种子
                if existing['is_seed'] and not new['is_seed']:
                    return True
                if new['is_seed'] and not existing['is_seed']:
                    return False
                return False
        
        elif strategy == "keep":
            return False
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def get_active_assertions(self, question: str) -> List[Dict]:
        """获取某个问题的所有当前有效断言"""
        q_hash = self._hash_question(question)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, subject, predicate, object, source, confidence, version, is_seed
                FROM fact_assertions
                WHERE question_hash = ? AND is_active = 1
                ORDER BY confidence DESC
            """, (q_hash,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_assertion_history(self, question: str, subject: str, predicate: str) -> List[Dict]:
        """获取某个断言的所有历史版本"""
        q_hash = self._hash_question(question)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT id, subject, predicate, object, source, confidence, version, is_active, 
                       superseded_by, created_at
                FROM fact_assertions
                WHERE question_hash = ? AND subject = ? AND predicate = ?
                ORDER BY version ASC
            """, (q_hash, subject, predicate)).fetchall()
            return [dict(row) for row in rows]
    
    def rollback_to_version(self, assertion_id: int, target_version: int) -> bool:
        """
        回滚到指定版本
        将目标版本设为活跃，新版本标记为不活跃
        """
        with sqlite3.connect(self.db_path) as conn:
            # 获取目标断言的信息
            row = conn.execute(
                'SELECT question_hash, subject, predicate FROM fact_assertions WHERE id = ?',
                (assertion_id,)
            ).fetchone()
            
            if not row:
                return False
            
            q_hash, subject, predicate = row
            
            # 将所有活跃版本标记为不活跃
            conn.execute("""
                UPDATE fact_assertions 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE question_hash = ? AND subject = ? AND predicate = ? AND is_active = 1
            """, (q_hash, subject, predicate))
            
            # 将目标版本标记为活跃
            conn.execute("""
                UPDATE fact_assertions 
                SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE question_hash = ? AND subject = ? AND predicate = ? AND version = ?
            """, (q_hash, subject, predicate, target_version))
            
            logger.info(f"⏪ 已回滚到版本 {target_version}")
            return True
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute('SELECT COUNT(*) FROM fact_assertions').fetchone()[0]
            active = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_active = 1').fetchone()[0]
            superseded = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_active = 0').fetchone()[0]
            seeds = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_seed = 1').fetchone()[0]
            
            return {
                'total': total,
                'active': active,
                'superseded': superseded,
                'seeds': seeds
            }