"""
事实断言存储层 V2
支持版本控制、置信度衰减、覆盖机制

核心理念：所有知识皆可被质疑，包括种子数据
"""
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class Assertion:
    """事实断言数据结构"""
    id: int
    question_hash: str
    subject: str
    predicate: str
    object: str
    source: str
    confidence: float
    is_seed: bool
    is_overridden: bool
    overridden_by: Optional[int]
    created_at: str
    last_used: str
    use_count: int


class FactStoreV2:
    """
    事实断言存储器 V2
    
    支持版本控制、置信度衰减、覆盖机制
    """
    
    def __init__(self, db_path: str = "data/fact_assertions_v2.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"📚 事实锚点库V2已初始化: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # 主断言表（增强版 - 支持版本控制）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fact_assertions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_hash TEXT NOT NULL,
                    question TEXT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    source TEXT DEFAULT 'manual',
                    confidence REAL DEFAULT 0.9,
                    is_seed BOOLEAN DEFAULT 0,
                    is_overridden BOOLEAN DEFAULT 0,
                    overridden_by INTEGER,
                    version INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 0,
                    decay_factor REAL DEFAULT 1.0
                )
            ''')
            
            # 索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_question_hash ON fact_assertions(question_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_subject ON fact_assertions(subject)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_source ON fact_assertions(source)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_overridden ON fact_assertions(is_overridden)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_active ON fact_assertions(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_subject_predicate ON fact_assertions(subject, predicate)')
            
            # 纠错历史表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS correction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_hash TEXT NOT NULL,
                    old_assertion_id INTEGER,
                    new_assertion_id INTEGER,
                    old_content TEXT,
                    new_content TEXT,
                    correction_source TEXT,
                    confidence_before REAL,
                    confidence_after REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (old_assertion_id) REFERENCES fact_assertions(id),
                    FOREIGN KEY (new_assertion_id) REFERENCES fact_assertions(id)
                )
            ''')
            
            # 置信度衰减日志
            conn.execute('''
                CREATE TABLE IF NOT EXISTS confidence_decay_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assertion_id INTEGER,
                    old_confidence REAL,
                    new_confidence REAL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    @staticmethod
    def hash_question(question: str) -> str:
        """生成问题的MD5哈希"""
        return hashlib.md5(question.encode('utf-8')).hexdigest()
    
    def add_assertion(
        self,
        question: str,
        subject: str,
        predicate: str,
        obj: str,
        source: str = "manual",
        confidence: float = 0.9,
        is_seed: bool = False
    ) -> int:
        """
        添加事实断言（支持覆盖机制）
        
        Args:
            question: 关联的问题
            subject: 主语
            predicate: 谓语
            obj: 宾语
            source: 来源标识
            confidence: 置信度
            is_seed: 是否为种子数据
        
        Returns:
            插入的记录ID
        """
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            # 检查是否存在相同(subject, predicate)的断言
            cursor = conn.execute('''
                SELECT id, object, confidence, source, is_overridden
                FROM fact_assertions
                WHERE question_hash = ? AND subject = ? AND predicate = ? AND is_overridden = 0
                ORDER BY confidence DESC
                LIMIT 1
            ''', (question_hash, subject, predicate))
            
            existing = cursor.fetchone()
            
            if existing:
                existing_id, existing_obj, existing_conf, existing_source, is_overridden = existing
                
                # 如果新断言置信度更高，或来自更权威来源，则覆盖
                should_override = self._should_override(
                    existing_conf, existing_source, confidence, source
                )
                
                if should_override and obj != existing_obj:
                    # 标记旧断言为被覆盖
                    conn.execute('''
                        UPDATE fact_assertions
                        SET is_overridden = 1
                        WHERE id = ?
                    ''', (existing_id,))
                    
                    logger.info(
                        f"🔄 断言覆盖: ({subject}, {predicate}, {existing_obj}) "
                        f"→ ({subject}, {predicate}, {obj})"
                    )
            
            # 插入新断言
            cursor = conn.execute('''
                INSERT INTO fact_assertions 
                (question_hash, subject, predicate, object, source, confidence, is_seed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_hash, subject, predicate, obj, source, confidence, is_seed))
            
            assertion_id = cursor.lastrowid
            
            # 如果覆盖了旧断言，记录纠错历史
            if existing and should_override and obj != existing_obj:
                conn.execute('''
                    INSERT INTO correction_history
                    (question_hash, old_assertion_id, new_assertion_id, old_content, new_content,
                     correction_source, confidence_before, confidence_after)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (question_hash, existing_id, assertion_id,
                      f"({subject}, {predicate}, {existing_obj})",
                      f"({subject}, {predicate}, {obj})",
                      source, existing_conf, confidence))
            
            conn.commit()
        
        logger.info(f"✅ 添加断言: ({subject}, {predicate}, {obj}) <- {source} (conf={confidence:.2f}, seed={is_seed})")
        return assertion_id
    
    def _should_override(
        self,
        existing_conf: float,
        existing_source: str,
        new_conf: float,
        new_source: str
    ) -> bool:
        """
        判断是否应该覆盖
        
        规则：
        1. 用户纠错 > 种子数据
        2. 置信度更高 > 置信度更低
        3. 外部学习 > 手动输入
        """
        # 来源优先级
        source_priority = {
            'user_correction': 100,
            'user_correction_detailed': 95,
            'correction': 90,
            'wiki': 80,
            'learning': 70,
            'manual': 60,
            'seed': 50,
            'manual_seed': 40
        }
        
        existing_priority = source_priority.get(existing_source, 50)
        new_priority = source_priority.get(new_source, 50)
        
        # 新来源优先级更高
        if new_priority > existing_priority:
            return True
        
        # 来源相同，置信度更高
        if new_priority == existing_priority and new_conf > existing_conf:
            return True
        
        return False
    
    def get_assertions(self, question: str, include_overridden: bool = False) -> List[Dict]:
        """获取问题关联的所有事实断言（排除被覆盖的）"""
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if include_overridden:
                cursor = conn.execute('''
                    SELECT id, subject, predicate, object, source, confidence, 
                           is_seed, is_overridden, overridden_by, created_at, last_used, use_count
                    FROM fact_assertions
                    WHERE question_hash = ?
                    ORDER BY confidence DESC, created_at DESC
                ''', (question_hash,))
            else:
                cursor = conn.execute('''
                    SELECT id, subject, predicate, object, source, confidence, 
                           is_seed, is_overridden, overridden_by, created_at, last_used, use_count
                    FROM fact_assertions
                    WHERE question_hash = ? AND is_overridden = 0
                    ORDER BY confidence DESC, created_at DESC
                ''', (question_hash,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def apply_decay(self, days_unused: int = 30, decay_rate: float = 0.95):
        """
        应用置信度衰减
        
        对长时间未使用的断言降低置信度
        """
        cutoff_date = (datetime.now() - timedelta(days=days_unused)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 查找需要衰减的断言
            cursor = conn.execute('''
                SELECT id, confidence, last_used, use_count
                FROM fact_assertions
                WHERE last_used < ? AND is_overridden = 0 AND is_seed = 0
            ''', (cutoff_date,))
            
            to_decay = cursor.fetchall()
            
            for assertion_id, old_conf, last_used, use_count in to_decay:
                # 根据使用次数调整衰减幅度
                adjusted_rate = decay_rate ** (1 + use_count * 0.1)
                new_conf = old_conf * adjusted_rate
                
                # 更新置信度
                conn.execute('''
                    UPDATE fact_assertions
                    SET confidence = ?, decay_factor = ?
                    WHERE id = ?
                ''', (new_conf, adjusted_rate, assertion_id))
                
                # 记录衰减日志
                conn.execute('''
                    INSERT INTO confidence_decay_log
                    (assertion_id, old_confidence, new_confidence, reason)
                    VALUES (?, ?, ?, ?)
                ''', (assertion_id, old_conf, new_conf, f"未使用超过{days_unused}天"))
            
            conn.commit()
        
        if to_decay:
            logger.info(f"📉 应用置信度衰减: {len(to_decay)}条断言")
    
    def mark_used(self, assertion_id: int):
        """标记断言被使用"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE fact_assertions
                SET last_used = ?, use_count = use_count + 1
                WHERE id = ?
            ''', (datetime.now().isoformat(), assertion_id))
            conn.commit()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute('SELECT COUNT(*) FROM fact_assertions').fetchone()[0]
            seeds = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_seed = 1').fetchone()[0]
            overridden = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_overridden = 1').fetchone()[0]
            active = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_overridden = 0').fetchone()[0]
            corrections = conn.execute('SELECT COUNT(*) FROM correction_history').fetchone()[0]
            
            # 按来源统计
            cursor = conn.execute('''
                SELECT source, COUNT(*) as count, AVG(confidence) as avg_conf
                FROM fact_assertions
                GROUP BY source
                ORDER BY count DESC
            ''')
            by_source = {row[0]: {'count': row[1], 'avg_conf': row[2]} for row in cursor.fetchall()}
            
            return {
                'total': total,
                'seeds': seeds,
                'overridden': overridden,
                'active': active,
                'corrections': corrections,
                'by_source': by_source
            }
    
    def get_assertion_history(self, question: str, subject: str, predicate: str) -> List[Dict]:
        """获取某个三元组的所有历史版本"""
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT id, subject, predicate, object, source, confidence, 
                       version, is_active, is_overridden, overridden_by, created_at
                FROM fact_assertions
                WHERE question_hash = ? AND subject = ? AND predicate = ?
                ORDER BY version ASC
            ''', (question_hash, subject, predicate))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def resolve_conflict(
        self,
        existing: Dict,
        new: Dict,
        strategy: str = "confidence"
    ) -> bool:
        """
        根据策略判断是否用新断言覆盖旧断言
        
        Args:
            existing: 现有断言
            new: 新断言
            strategy: 策略 ('confidence' | 'user' | 'keep')
        
        Returns:
            True 表示覆盖
        """
        if strategy == "keep":
            return False
        
        if strategy == "user":
            # 用户纠错永远覆盖
            if new.get('source') == 'user_correction' or new.get('source') == 'correction':
                return True
            elif existing.get('source') in ['user_correction', 'correction']:
                return False
            else:
                # 都不是纠错，按置信度
                return new.get('confidence', 0) > existing.get('confidence', 0)
        
        if strategy == "confidence":
            # 高置信度覆盖低置信度
            new_conf = new.get('confidence', 0)
            existing_conf = existing.get('confidence', 0)
            
            if new_conf > existing_conf:
                return True
            elif new_conf < existing_conf:
                return False
            else:
                # 置信度相等，判断是否为种子
                if new.get('is_seed') and not existing.get('is_seed'):
                    return False  # 种子不覆盖已学习的
                elif existing.get('is_seed') and not new.get('is_seed'):
                    return True   # 新学习覆盖种子
                else:
                    return False  # 相等则保留旧
        
        return False


fact_store_v2 = FactStoreV2()