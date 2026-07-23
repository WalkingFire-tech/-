"""
知识晋升管道 - 扩展L5进化层，管理知识从捕获到存储的完整流程
"""

from typing import Dict, List
from datetime import datetime
import json
import hashlib
from enum import Enum
from pathlib import Path
from core.ports.adapters import get_storage_port


class KnowledgeStatus(Enum):
    RAW = "raw"
    VERIFIED = "verified"
    GOLDEN = "golden"
    REJECTED = "rejected"
    POSTPONED = "postponed"


class KnowledgePromotionPipeline:
    """知识晋升管道"""
    
    def __init__(self, db_path: str = "data/knowledge_pipeline.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db = get_storage_port(str(self.db_path))
        db.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_candidates (
                id TEXT PRIMARY KEY,
                content TEXT,
                source TEXT,
                status TEXT,
                validation_score REAL,
                validation_details TEXT,
                related_signals TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS golden_tests (
                id TEXT PRIMARY KEY,
                question TEXT,
                ideal_answer TEXT,
                source TEXT,
                confidence REAL,
                created_at TEXT
            )
        """)
    
    def add_candidate(self, content: str, source: str, signals: List[Dict]) -> str:
        """添加候选知识"""
        candidate_id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        db = get_storage_port(str(self.db_path))
        db.execute("""
            INSERT INTO knowledge_candidates
            (id, content, source, status, related_signals, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id, content, source, KnowledgeStatus.RAW.value,
            json.dumps(signals, ensure_ascii=False),
            datetime.now().isoformat(), datetime.now().isoformat()
        ), commit=True)
        
        return candidate_id
    
    def promote_to_verified(self, candidate_id: str, validation: Dict) -> bool:
        """晋升为已验证"""
        db = get_storage_port(str(self.db_path))
        db.execute("""
            UPDATE knowledge_candidates
            SET status = ?, validation_score = ?, validation_details = ?, updated_at = ?
            WHERE id = ?
        """, (
            KnowledgeStatus.VERIFIED.value,
            validation.get("score", 0.0),
            json.dumps(validation, ensure_ascii=False),
            datetime.now().isoformat(), candidate_id
        ), commit=True)
        return True
    
    def promote_to_golden(self, candidate_id: str, question: str, ideal_answer: str) -> bool:
        """
        晋升为黄金知识
        
        黄金知识标准：
        1. 验证得分 >= 0.85
        2. 至少3次独立验证通过
        3. 无冲突警告
        4. 用户反馈正面或中性
        
        Args:
            candidate_id: 候选ID
            question: 标准化问题
            ideal_answer: 理想答案
        
        Returns:
            bool: 是否成功晋升
        """
        db = get_storage_port(str(self.db_path))
        
        candidate = db.query_one(
            "SELECT * FROM knowledge_candidates WHERE id = ?",
            (candidate_id,)
        )
        
        if not candidate:
            logger.warning(f"候选知识不存在: {candidate_id}")
            return False
        
        candidate_dict = dict(candidate)
        
        validation_score = candidate_dict.get("validation_score", 0.0)
        if validation_score < 0.85:
            logger.info(f"验证得分不足({validation_score:.2f})，无法晋升为黄金知识")
            return False
        
        validation_details = json.loads(candidate_dict.get("validation_details", "{}"))
        verification_count = validation_details.get("verification_count", 0)
        if verification_count < 3:
            logger.info(f"验证次数不足({verification_count})，需要至少3次独立验证")
            return False
        
        warnings = validation_details.get("warnings", [])
        conflict_warnings = [w for w in warnings if "冲突" in w or "冲突" in w]
        if conflict_warnings:
            logger.warning(f"存在冲突警告: {conflict_warnings}")
            return False
        
        golden_id = hashlib.md5(f"{question}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        db.execute("""
            INSERT INTO golden_tests
            (id, question, ideal_answer, source, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            golden_id, question, ideal_answer,
            candidate_dict.get("source", "unknown"),
            validation_score,
            datetime.now().isoformat()
        ))
        
        db.execute("""
            UPDATE knowledge_candidates
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (KnowledgeStatus.GOLDEN.value, datetime.now().isoformat(), candidate_id), commit=True)
        
        logger.success(f"✨ 知识晋升为黄金: {golden_id}")
        return True
    
    def reject_candidate(self, candidate_id: str, reason: str, details: Dict = None) -> bool:
        """
        拒绝候选知识
        
        拒绝原因分类：
        1. quality_issue - 质量不达标
        2. conflict - 与现有知识冲突
        3. user_negative - 用户明确反对
        4. outdated - 信息过时
        5. duplicate - 重复知识
        
        Args:
            candidate_id: 候选ID
            reason: 拒绝原因
            details: 详细信息
        
        Returns:
            bool: 是否成功拒绝
        """
        db = get_storage_port(str(self.db_path))
        
        if not db.query_one("SELECT id FROM knowledge_candidates WHERE id = ?", (candidate_id,)):
            logger.warning(f"候选知识不存在: {candidate_id}")
            return False
        
        rejection_record = {
            "reason": reason,
            "details": details or {},
            "rejected_at": datetime.now().isoformat()
        }
        
        db.execute("""
            UPDATE knowledge_candidates
            SET status = ?, validation_details = ?, updated_at = ?
            WHERE id = ?
        """, (
            KnowledgeStatus.REJECTED.value,
            json.dumps(rejection_record, ensure_ascii=False),
            datetime.now().isoformat(),
            candidate_id
        ), commit=True)
        
        logger.info(f"❌ 知识已拒绝: {candidate_id} - 原因: {reason}")
        return True
    
    def postpone_candidate(self, candidate_id: str, postpone_reason: str, review_after_days: int = 7) -> bool:
        """
        延迟处理候选知识
        
        延迟场景：
        1. 需要更多信息验证
        2. 等待用户反馈确认
        3. 等待冲突知识解决
        4. 需要专家审核
        
        Args:
            candidate_id: 候选ID
            postpone_reason: 延迟原因
            review_after_days: 多少天后重新审核
        
        Returns:
            bool: 是否成功延迟
        """
        db = get_storage_port(str(self.db_path))
        
        if not db.query_one("SELECT id FROM knowledge_candidates WHERE id = ?", (candidate_id,)):
            logger.warning(f"候选知识不存在: {candidate_id}")
            return False
        
        from datetime import timedelta
        review_date = (datetime.now() + timedelta(days=review_after_days)).isoformat()
        
        postpone_record = {
            "postpone_reason": postpone_reason,
            "postponed_at": datetime.now().isoformat(),
            "review_date": review_date,
            "review_after_days": review_after_days
        }
        
        db.execute("""
            UPDATE knowledge_candidates
            SET status = ?, validation_details = ?, updated_at = ?
            WHERE id = ?
        """, (
            KnowledgeStatus.POSTPONED.value,
            json.dumps(postpone_record, ensure_ascii=False),
            datetime.now().isoformat(),
            candidate_id
        ), commit=True)
        
        logger.info(f"⏸️ 知识已延迟: {candidate_id} - {review_after_days}天后审核")
        return True
    
    def auto_promote_eligible_candidates(self) -> Dict[str, int]:
        """
        自动晋升符合条件的候选知识
        
        自动晋升条件：
        1. 状态为VERIFIED
        2. 验证得分 >= 0.85
        3. 创建时间 >= 24小时（避免冲动注入）
        4. 无未处理的冲突警告
        
        Returns:
            Dict[str, int]: 处理结果统计
        """
        stats = {
            "promoted": 0,
            "postponed": 0,
            "rejected": 0,
            "skipped": 0
        }
        
        db = get_storage_port(str(self.db_path))
        
        candidates = db.query("""
            SELECT * FROM knowledge_candidates
            WHERE status = ?
            AND validation_score >= 0.85
            ORDER BY validation_score DESC
        """, (KnowledgeStatus.VERIFIED.value,))
        
        for candidate in candidates:
            candidate_dict = dict(candidate)
            candidate_id = candidate_dict["id"]
            
            created_at = datetime.fromisoformat(candidate_dict["created_at"])
            hours_since_creation = (datetime.now() - created_at).total_seconds() / 3600
            
            if hours_since_creation < 24:
                logger.debug(f"候选{candidate_id}创建不足24小时，跳过")
                stats["skipped"] += 1
                continue
            
            validation_details = json.loads(candidate_dict.get("validation_details", "{}"))
            warnings = validation_details.get("warnings", [])
            has_conflict = any("冲突" in w or "conflict" in w.lower() for w in warnings)
            
            if has_conflict:
                self.postpone_candidate(
                    candidate_id,
                    "存在未解决的冲突警告",
                    review_after_days=3
                )
                stats["postponed"] += 1
                continue
            
            content = candidate_dict.get("content", "")
            if len(content) < 50:
                self.reject_candidate(
                    candidate_id,
                    "quality_issue",
                    {"detail": "内容过短，质量不达标"}
                )
                stats["rejected"] += 1
                continue
            
            success = self.promote_to_golden(
                candidate_id,
                content[:100],
                content
            )
            
            if success:
                stats["promoted"] += 1
            else:
                stats["skipped"] += 1
        
        logger.info(f"自动晋升完成: {stats}")
        return stats
    
    def get_golden_tests(self) -> List[Dict]:
        """
        获取黄金测试集
        
        返回所有黄金知识，用于：
        1. 系统自测试
        2. 质量基准
        3. 回答参考
        """
        db = get_storage_port(str(self.db_path))
        return [dict(row) for row in db.query("SELECT * FROM golden_tests ORDER BY created_at DESC")]
    
    def get_pending_reviews(self) -> List[Dict]:
        """
        获取待审核的延迟知识
        
        返回所有到达审核时间的POSTPONED知识
        """
        db = get_storage_port(str(self.db_path))
        
        rows = db.query("""
            SELECT * FROM knowledge_candidates
            WHERE status = ?
            ORDER BY updated_at ASC
        """, (KnowledgeStatus.POSTPONED.value,))
        
        pending = []
        now = datetime.now()
        
        for row in rows:
            candidate = dict(row)
            details = json.loads(candidate.get("validation_details", "{}"))
            review_date_str = details.get("review_date")
            
            if review_date_str:
                review_date = datetime.fromisoformat(review_date_str)
                if now >= review_date:
                    pending.append(candidate)
        
        return pending
    
    def get_statistics(self) -> Dict:
        """
        获取管道统计信息
        
        返回各状态的知识数量和平均得分
        """
        db = get_storage_port(str(self.db_path))
        stats = {}
        
        for status in KnowledgeStatus:
            row = db.query_one(
                "SELECT COUNT(*), AVG(validation_score) FROM knowledge_candidates WHERE status = ?",
                (status.value,)
            )
            count, avg_score = row[0], row[1]
            stats[status.value] = {
                "count": count,
                "avg_score": avg_score or 0.0
            }
        
        row = db.query_one("SELECT COUNT(*) FROM golden_tests")
        stats["golden_count"] = row[0]
        
        return stats


try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


knowledge_pipeline = KnowledgePromotionPipeline()