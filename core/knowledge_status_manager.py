"""
知识状态管理器 - 实现延迟确认和状态分级

知识状态：
- pending: 待验证（用户点赞但未通过系统验证）
- verified: 已验证（通过系统多维度验证）
- confirmed: 已确认（多次验证或权威来源）
- deprecated: 已废弃（发现冲突或错误）
"""

from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class KnowledgeStatus(Enum):
    """知识状态"""
    PENDING = "pending"          # 待验证
    VERIFIED = "verified"        # 已验证
    CONFIRMED = "confirmed"      # 已确认
    DEPRECATED = "deprecated"    # 已废弃


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: int
    question: str
    answer: str
    status: KnowledgeStatus
    confidence: float
    verification_count: int
    last_verified: datetime
    sources: List[str]
    conflicts: List[int]


class KnowledgeStatusManager:
    """
    知识状态管理器
    
    管理知识的生命周期和状态转换。
    """
    
    def __init__(self, db_path: str = "data/knowledge_status.db"):
        self.db_path = Path(db_path)
        self._init_db()
        
        logger.info("📊 知识状态管理器已初始化")
    
    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    confidence REAL DEFAULT 0.5,
                    verification_count INTEGER DEFAULT 0,
                    last_verified TIMESTAMP,
                    sources TEXT,
                    conflicts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON knowledge_status(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_question ON knowledge_status(question)
            """)
            
            conn.commit()
    
    def add_knowledge(
        self,
        question: str,
        answer: str,
        status: KnowledgeStatus = KnowledgeStatus.PENDING,
        confidence: float = 0.5,
        source: str = "unknown"
    ) -> int:
        """
        添加知识（默认为待验证状态）
        
        Args:
            question: 问题
            answer: 回答
            status: 初始状态
            confidence: 置信度
            source: 来源
        
        Returns:
            知识ID
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                INSERT INTO knowledge_status 
                (question, answer, status, confidence, sources, last_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                question,
                answer,
                status.value,
                confidence,
                f'["{source}"]',
                datetime.now().isoformat()
            ))
            
            knowledge_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"添加知识: {question[:30]}... (状态={status.value}, ID={knowledge_id})")
            
            return knowledge_id
    
    def verify_knowledge(
        self,
        knowledge_id: int,
        verification_result: Dict
    ) -> KnowledgeStatus:
        """
        验证知识（状态转换）
        
        Args:
            knowledge_id: 知识ID
            verification_result: 验证结果
        
        Returns:
            新状态
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取当前状态
            cursor.execute("""
                SELECT status, verification_count, confidence
                FROM knowledge_status WHERE id = ?
            """, (knowledge_id,))
            
            row = cursor.fetchone()
            if not row:
                return KnowledgeStatus.PENDING
            
            current_status = KnowledgeStatus(row['status'])
            verification_count = row['verification_count']
            current_confidence = row['confidence']
            
            # 计算新置信度
            new_confidence = self._update_confidence(
                current_confidence,
                verification_result
            )
            
            # 决定新状态
            new_status = self._determine_status(
                current_status,
                new_confidence,
                verification_count + 1,
                verification_result
            )
            
            # 更新数据库
            conn.execute("""
                UPDATE knowledge_status
                SET status = ?,
                    confidence = ?,
                    verification_count = verification_count + 1,
                    last_verified = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                new_status.value,
                new_confidence,
                datetime.now().isoformat(),
                knowledge_id
            ))
            
            conn.commit()
            
            logger.info(
                f"知识验证: ID={knowledge_id}, "
                f"状态={current_status.value}→{new_status.value}, "
                f"置信度={current_confidence:.2f}→{new_confidence:.2f}"
            )
            
            return new_status
    
    def _update_confidence(
        self,
        current: float,
        verification: Dict
    ) -> float:
        """更新置信度"""
        # 验证结果的影响
        if verification.get("consistent", True):
            delta = 0.1
        else:
            delta = -0.2
        
        # 来源可信度
        source_weight = {
            "system_evaluated": 0.15,
            "user_feedback_positive": 0.05,
            "user_feedback_negative": -0.1,
            "cross_validation": 0.2,
            "authority_source": 0.3
        }
        
        source = verification.get("source", "unknown")
        delta += source_weight.get(source, 0)
        
        return max(0.0, min(1.0, current + delta))
    
    def _determine_status(
        self,
        current: KnowledgeStatus,
        confidence: float,
        verification_count: int,
        verification: Dict
    ) -> KnowledgeStatus:
        """决定新状态"""
        # 发现冲突 → 废弃
        if not verification.get("consistent", True):
            return KnowledgeStatus.DEPRECATED
        
        # 置信度很高 + 多次验证 → 确认
        if confidence >= 0.85 and verification_count >= 3:
            return KnowledgeStatus.CONFIRMED
        
        # 置信度较高 + 至少一次验证 → 已验证
        if confidence >= 0.7 and verification_count >= 1:
            return KnowledgeStatus.VERIFIED
        
        # 其他情况保持待验证
        return KnowledgeStatus.PENDING
    
    def get_knowledge_by_status(
        self,
        status: KnowledgeStatus,
        limit: int = 10
    ) -> List[Dict]:
        """按状态获取知识"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM knowledge_status
                WHERE status = ?
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?
            """, (status.value, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def deprecate_conflicting(
        self,
        knowledge_id: int,
        conflict_with: int,
        reason: str
    ):
        """废弃冲突的知识"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                UPDATE knowledge_status
                SET status = ?,
                    conflicts = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                KnowledgeStatus.DEPRECATED.value,
                f'[{conflict_with}]',
                knowledge_id
            ))
            
            conn.commit()
            
            logger.warning(f"废弃知识: ID={knowledge_id}, 原因={reason}")


status_manager = KnowledgeStatusManager()