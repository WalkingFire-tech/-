"""
知识进化层 - 验证知识一致性，检测并解决冲突

对应六层架构的 L2 学习层 + L3 整合层扩展
职责：验证新知识与已有知识的一致性，检测并解决知识冲突
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib
import re
from pathlib import Path
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class KnowledgeVerification:
    """知识验证结果"""
    verification_id: str
    knowledge_id: str
    is_consistent: bool
    conflict_with: List[str]
    quality_score: float
    evidence_count: int
    verification_status: str
    timestamp: str


@dataclass
class KnowledgeConflict:
    """知识冲突记录"""
    conflict_id: str
    knowledge_id_a: str
    knowledge_id_b: str
    conflict_type: str
    resolution_status: str
    created_at: str
    resolved_at: Optional[str]
    resolution_note: Optional[str]


class KnowledgeEvolutionEngine:
    """
    知识进化引擎
    
    验证知识一致性，检测冲突，重构知识结构。
    """
    
    def __init__(self, db_path: str = "data/knowledge_evolution.db",
                 knowledge_db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self.knowledge_db_path = knowledge_db_path
        self._init_database()
        logger.info("📚 知识进化引擎已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS knowledge_verifications (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT,
                is_consistent INTEGER,
                conflict_with TEXT,
                quality_score REAL,
                evidence_count INTEGER,
                verification_status TEXT,
                timestamp TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_id ON knowledge_verifications(knowledge_id);
            CREATE TABLE IF NOT EXISTS knowledge_conflicts (
                id TEXT PRIMARY KEY,
                knowledge_id_a TEXT,
                knowledge_id_b TEXT,
                conflict_type TEXT,
                conflict_details TEXT,
                resolution_status TEXT,
                created_at TEXT,
                resolved_at TEXT,
                resolution_note TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_conflict_status ON knowledge_conflicts(resolution_status);
            CREATE TABLE IF NOT EXISTS knowledge_refinements (
                id TEXT PRIMARY KEY,
                original_knowledge_id TEXT,
                refined_content TEXT,
                refinement_reason TEXT,
                quality_improvement REAL,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS conflict_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                occurrence_count INTEGER,
                resolution_strategy TEXT,
                success_rate REAL,
                last_seen TEXT
            )
        ''')
    
    def verify_knowledge(self, knowledge_id: str, content: str, 
                         question: str = "") -> KnowledgeVerification:
        """
        验证一条知识
        
        Args:
            knowledge_id: 知识ID
            content: 知识内容
            question: 问题（可选）
        
        Returns:
            KnowledgeVerification
        """
        existing = self._get_all_knowledge()
        
        conflicts = self._detect_conflicts(knowledge_id, content, question, existing)
        
        quality_score = self._assess_quality(content, question)
        
        evidence_count = self._count_evidence(content)
        
        if conflicts:
            status = "conflicted"
            is_consistent = False
        elif quality_score < 0.5:
            status = "low_quality"
            is_consistent = True
        else:
            status = "verified"
            is_consistent = True
        
        verification_id = hashlib.md5(
            f"{knowledge_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        verification = KnowledgeVerification(
            verification_id=verification_id,
            knowledge_id=knowledge_id,
            is_consistent=is_consistent,
            conflict_with=conflicts,
            quality_score=quality_score,
            evidence_count=evidence_count,
            verification_status=status,
            timestamp=datetime.now().isoformat()
        )
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT OR REPLACE INTO knowledge_verifications
            (id, knowledge_id, is_consistent, conflict_with,
             quality_score, evidence_count, verification_status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            verification.verification_id,
            verification.knowledge_id,
            1 if verification.is_consistent else 0,
            json.dumps(verification.conflict_with),
            verification.quality_score,
            verification.evidence_count,
            verification.verification_status,
            verification.timestamp
        ), commit=True)
        
        if conflicts:
            for conflict_info in conflicts:
                if isinstance(conflict_info, dict):
                    other_id = conflict_info.get("id")
                    conflict_type = conflict_info.get("type", "semantic_conflict")
                    details = conflict_info.get("details", "")
                else:
                    other_id = conflict_info
                    conflict_type = "semantic_conflict"
                    details = ""
                
                conflict_id = hashlib.md5(
                    f"{knowledge_id}{other_id}{datetime.now().isoformat()}".encode()
                ).hexdigest()[:12]
                
                db.execute('''
                    INSERT OR IGNORE INTO knowledge_conflicts
                    (id, knowledge_id_a, knowledge_id_b, conflict_type,
                     conflict_details, resolution_status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conflict_id,
                    knowledge_id,
                    other_id,
                    conflict_type,
                    details,
                    "pending",
                    datetime.now().isoformat()
                ), commit=True)
                
                self._update_conflict_pattern(db, conflict_type)
        
        logger.warning(f"知识验证: {knowledge_id} -> {status} (质量={quality_score:.2f})")
        return verification
    
    def _get_all_knowledge(self) -> List[Dict]:
        """获取所有已有知识"""
        try:
            db = DatabaseManager.get(self.knowledge_db_path)
            
            row = db.query_one("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='knowledge_items'
            """)
            
            if not row:
                return []
            
            return [dict(row) for row in db.query("SELECT id, question, answer FROM knowledge_items")]
        except Exception as e:
            logger.error(f"获取知识失败: {e}")
            return []
    
    def _detect_conflicts(self, knowledge_id: str, content: str, 
                          question: str, existing: List[Dict]) -> List[Dict]:
        """
        检测知识冲突
        
        使用多种检测策略：
        1. 关键词重叠 + 否定词检测
        2. 语义相似度检测
        3. 事实矛盾检测
        4. 数值矛盾检测
        """
        conflicts = []
        content_lower = content.lower()
        
        keywords = self._extract_keywords(f"{question} {content}")
        
        content_numbers = self._extract_numbers(content)
        
        content_negations = self._detect_negations(content_lower)
        
        for other in existing:
            if other['id'] == knowledge_id:
                continue
            
            other_content = f"{other.get('question', '')} {other.get('answer', '')}"
            other_keywords = self._extract_keywords(other_content)
            
            overlap_score = self._calculate_keyword_overlap(keywords, other_keywords)
            
            if overlap_score > 0.3:
                other_negations = self._detect_negations(other_content.lower())
                
                if content_negations != other_negations and overlap_score > 0.4:
                    conflicts.append({
                        "id": other['id'],
                        "type": "negation_conflict",
                        "details": f"否定词不一致 (重叠={overlap_score:.2f})"
                    })
                    continue
            
            other_numbers = self._extract_numbers(other_content)
            number_conflict = self._check_number_conflict(content_numbers, other_numbers)
            
            if number_conflict and overlap_score > 0.2:
                conflicts.append({
                    "id": other['id'],
                    "type": "number_conflict",
                    "details": number_conflict
                })
                continue
            
            if overlap_score > 0.6:
                similarity_conflict = self._check_semantic_conflict(content, other_content)
                if similarity_conflict:
                    conflicts.append({
                        "id": other['id'],
                        "type": "semantic_conflict",
                        "details": similarity_conflict
                    })
        
        return conflicts[:5]
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词"""
        keywords = set()
        
        words = re.findall(r'[a-zA-Z\u4e00-\u9fa5]{2,}', text.lower())
        
        stopwords = {
            '的', '是', '在', '有', '和', '了', '不', '这', '那', '就', '也',
            '都', '会', '能', '要', '可以', '应该', '需要', '一个', '这个',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been'
        }
        
        keywords = {w for w in words if w not in stopwords and len(w) > 1}
        
        return keywords
    
    def _calculate_keyword_overlap(self, set1: set, set2: set) -> float:
        """计算关键词重叠度"""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_numbers(self, text: str) -> Dict[str, float]:
        """提取数值"""
        numbers = {}
        
        percent_matches = re.findall(r'(\w+)[是为]?(\d+(?:\.\d+)?)\s*%', text)
        for label, value in percent_matches:
            numbers[f"{label}_percent"] = float(value)
        
        count_matches = re.findall(r'(\w+)[是为]?(\d+)\s*(个|次|层|个)', text)
        for label, value, unit in count_matches:
            numbers[f"{label}_{unit}"] = float(value)
        
        simple_numbers = re.findall(r'\d+\.?\d*', text)
        if simple_numbers:
            numbers['values'] = [float(n) for n in simple_numbers[:5]]
        
        return numbers
    
    def _detect_negations(self, text: str) -> bool:
        """检测否定词"""
        neg_words = ["不", "不是", "非", "错误", "不可能", "并非", "无法", "不能", "没", "无"]
        return any(w in text for w in neg_words)
    
    def _check_number_conflict(self, nums1: Dict, nums2: Dict) -> Optional[str]:
        """检查数值冲突"""
        for key in nums1:
            if key in nums2 and key != 'values':
                if abs(nums1[key] - nums2[key]) > nums2[key] * 0.2:
                    return f"{key}: {nums1[key]} vs {nums2[key]}"
        
        if 'values' in nums1 and 'values' in nums2:
            for v1 in nums1['values']:
                for v2 in nums2['values']:
                    if v1 != 0 and v2 != 0:
                        ratio = abs(v1 - v2) / max(abs(v1), abs(v2))
                        if ratio > 0.5 and ratio < 0.9:
                            return f"数值差异: {v1} vs {v2}"
        
        return None
    
    def _check_semantic_conflict(self, text1: str, text2: str) -> Optional[str]:
        """检查语义冲突"""
        contradiction_patterns = [
            (r'必须', r'不必'),
            (r'一定', r'不一定'),
            (r'总是', r'有时'),
            (r'所有', r'有些'),
            (r'完全', r'部分')
        ]
        
        for pattern1, pattern2 in contradiction_patterns:
            if (re.search(pattern1, text1) and re.search(pattern2, text2)) or \
               (re.search(pattern2, text1) and re.search(pattern1, text2)):
                return f"矛盾: {pattern1} vs {pattern2}"
        
        return None
    
    def _assess_quality(self, content: str, question: str = "") -> float:
        """评估知识质量"""
        score = 0.2
        
        if len(content) > 50:
            score += 0.15
        if len(content) > 150:
            score += 0.15
        if len(content) > 500:
            score += 0.1
        
        if "\n" in content:
            score += 0.1
        if any(marker in content for marker in ["1.", "2.", "首先", "其次", "•", "-"]):
            score += 0.1
        if "```" in content:
            score += 0.05
        
        if question and len(question) > 5:
            score += 0.1
        
        punctuation = ["。", ".", "？", "!", "；", ";"]
        if any(p in content for p in punctuation):
            score += 0.05
        
        technical_words = ["系统", "架构", "机制", "理论", "模型", "方法", "过程", "原理"]
        if any(w in content for w in technical_words):
            score += 0.1
        
        return min(1.0, score)
    
    def _count_evidence(self, content: str) -> int:
        """计算证据数量"""
        evidence_count = 0
        
        if re.search(r'例如|比如|举例|案例', content):
            evidence_count += 1
        
        if re.search(r'根据|引用|来源|参考', content):
            evidence_count += 1
        
        if re.search(r'\d+\.?\d*%', content):
            evidence_count += 1
        
        if re.search(r'```|def |class ', content):
            evidence_count += 1
        
        return evidence_count
    
    def _update_conflict_pattern(self, db, conflict_type: str):
        """更新冲突模式统计"""
        pattern_id = hashlib.md5(conflict_type.encode()).hexdigest()[:8]
        
        row = db.query_one(
            "SELECT occurrence_count FROM conflict_patterns WHERE pattern_id = ?",
            (pattern_id,)
        )
        
        if row:
            db.execute('''
                UPDATE conflict_patterns
                SET occurrence_count = ?, last_seen = ?
                WHERE pattern_id = ?
            ''', (row[0] + 1, datetime.now().isoformat(), pattern_id), commit=True)
        else:
            db.execute('''
                INSERT INTO conflict_patterns
                (pattern_id, pattern_type, occurrence_count, resolution_strategy, success_rate, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (pattern_id, conflict_type, 1, "manual", 0.0, datetime.now().isoformat()), commit=True)
    
    def resolve_conflict(self, conflict_id: str, resolution: str, 
                         note: str = "") -> bool:
        """
        解决冲突
        
        Args:
            conflict_id: 冲突ID
            resolution: 解决方式 ('accept_a', 'accept_b', 'merge', 'ignore')
            note: 备注
        """
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE knowledge_conflicts
            SET resolution_status = ?, resolved_at = ?, resolution_note = ?
            WHERE id = ?
        ''', (resolution, datetime.now().isoformat(), note, conflict_id), commit=True)
        
        row = db.query_one(
            "SELECT conflict_type FROM knowledge_conflicts WHERE id = ?",
            (conflict_id,)
        )
        
        if row:
            conflict_type = row[0]
            pattern_id = hashlib.md5(conflict_type.encode()).hexdigest()[:8]
            
            pattern_row = db.query_one(
                "SELECT success_rate, occurrence_count FROM conflict_patterns WHERE pattern_id = ?",
                (pattern_id,)
            )
            
            if pattern_row:
                old_rate = pattern_row[0]
                count = pattern_row[1]
                success_increment = 1.0 if resolution != "ignore" else 0.0
                new_rate = (old_rate * count + success_increment) / (count + 1)
                
                db.execute('''
                    UPDATE conflict_patterns
                    SET success_rate = ?, resolution_strategy = ?
                    WHERE pattern_id = ?
                ''', (new_rate, resolution, pattern_id), commit=True)
        
        logger.info(f"冲突已解决: {conflict_id} -> {resolution}")
        return True
    
    def refine_knowledge(self, knowledge_id: str, refined_content: str,
                        reason: str) -> str:
        """
        重构知识
        
        Args:
            knowledge_id: 原知识ID
            refined_content: 重构后的内容
            reason: 重构原因
        
        Returns:
            refinement_id
        """
        refinement_id = hashlib.md5(
            f"{knowledge_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('''
            SELECT quality_score FROM knowledge_verifications
            WHERE knowledge_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (knowledge_id,))
        old_quality = row[0] if row else 0.5
        
        new_quality = self._assess_quality(refined_content)
        improvement = new_quality - old_quality
        
        db.execute('''
            INSERT INTO knowledge_refinements
            (id, original_knowledge_id, refined_content, refinement_reason,
             quality_improvement, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            refinement_id,
            knowledge_id,
            refined_content,
            reason,
            improvement,
            datetime.now().isoformat()
        ), commit=True)
        
        logger.info(f"知识重构: {knowledge_id} -> {refinement_id} (改进={improvement:+.2f})")
        return refinement_id
    
    def get_pending_conflicts(self) -> List[KnowledgeConflict]:
        """获取待处理的冲突"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT * FROM knowledge_conflicts
            WHERE resolution_status = 'pending'
            ORDER BY created_at DESC
        ''')
        
        conflicts = []
        for row in rows:
            conflicts.append(KnowledgeConflict(
                conflict_id=row['id'],
                knowledge_id_a=row['knowledge_id_a'],
                knowledge_id_b=row['knowledge_id_b'],
                conflict_type=row['conflict_type'],
                resolution_status=row['resolution_status'],
                created_at=row['created_at'],
                resolved_at=row['resolved_at'],
                resolution_note=row['resolution_note']
            ))
        return conflicts
    
    def get_verification_history(self, knowledge_id: str, limit: int = 10) -> List[Dict]:
        """获取知识的验证历史"""
        db = DatabaseManager.get(self.db_path)
        return [dict(row) for row in db.query('''
            SELECT * FROM knowledge_verifications
            WHERE knowledge_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (knowledge_id, limit))]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        db = DatabaseManager.get(self.db_path)
        
        total_verifications = db.query_one("SELECT COUNT(*) as total FROM knowledge_verifications")['total']
        
        by_status = [dict(row) for row in db.query('''
            SELECT verification_status, COUNT(*) as count
            FROM knowledge_verifications
            GROUP BY verification_status
        ''')]
        
        total_conflicts = db.query_one("SELECT COUNT(*) as total FROM knowledge_conflicts")['total']
        
        conflicts_by_status = [dict(row) for row in db.query('''
            SELECT resolution_status, COUNT(*) as count
            FROM knowledge_conflicts
            GROUP BY resolution_status
        ''')]
        
        conflict_patterns = [dict(row) for row in db.query('''
            SELECT pattern_type, occurrence_count, success_rate
            FROM conflict_patterns
            ORDER BY occurrence_count DESC
        ''')]
        
        return {
            "total_verifications": total_verifications,
            "verifications_by_status": by_status,
            "total_conflicts": total_conflicts,
            "conflicts_by_status": conflicts_by_status,
            "conflict_patterns": conflict_patterns
        }
    
    def get_evolution_report(self) -> Dict:
        """获取进化报告"""
        stats = self.get_statistics()
        pending = self.get_pending_conflicts()
        
        recommendations = []
        
        if len(pending) > 5:
            recommendations.append({
                "type": "conflict_backlog",
                "message": f"有 {len(pending)} 个待处理冲突",
                "priority": "high",
                "action": "review_conflicts"
            })
        
        if stats["conflict_patterns"]:
            frequent_patterns = [
                p for p in stats["conflict_patterns"]
                if p["occurrence_count"] > 3
            ]
            if frequent_patterns:
                recommendations.append({
                    "type": "pattern_analysis",
                    "message": f"发现 {len(frequent_patterns)} 个高频冲突模式",
                    "priority": "medium",
                    "action": "analyze_patterns"
                })
        
        return {
            "statistics": stats,
            "pending_conflicts": len(pending),
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }


_knowledge_evolution_engine: Optional[KnowledgeEvolutionEngine] = None


def get_knowledge_evolution_engine() -> KnowledgeEvolutionEngine:
    """获取知识进化引擎单例"""
    global _knowledge_evolution_engine
    if _knowledge_evolution_engine is None:
        _knowledge_evolution_engine = KnowledgeEvolutionEngine()
    return _knowledge_evolution_engine
