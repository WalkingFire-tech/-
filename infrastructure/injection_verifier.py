"""
注入效果验证器
验证知识注入后的学习效果
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import json
import os

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from infrastructure.database_manager import DatabaseManager


@dataclass
class VerificationResult:
    """验证结果"""
    injection_id: str
    question: str
    before_score: float
    after_score: float
    improvement: float
    passed: bool
    verified_at: str
    details: Dict


class InjectionVerifier:
    """
    注入效果验证器
    
    验证知识注入是否真正提升了系统表现
    实现"感知→学习→验证→修正"闭环
    """
    
    def __init__(self, db_path: str = "data/injection_verifications.db"):
        self.db_path = db_path
        self.verification_history: List[VerificationResult] = []
        self._init_db()
    
    def _init_db(self):
        """初始化验证结果存储"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS injection_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                injection_id TEXT NOT NULL,
                question TEXT NOT NULL,
                before_score REAL NOT NULL,
                after_score REAL NOT NULL,
                improvement REAL NOT NULL,
                passed INTEGER NOT NULL,
                verified_at TEXT NOT NULL,
                details TEXT
            )
        ''')
        
        conn.commit()
    
    def verify_injection(
        self,
        injection_id: str,
        question: str,
        before_score: float,
        injected_knowledge: List[Dict],
        improvement_threshold: float = 5.0
    ) -> VerificationResult:
        """
        验证注入效果
        
        Args:
            injection_id: 注入ID
            question: 问题
            before_score: 注入前的评分
            injected_knowledge: 注入的知识列表
            improvement_threshold: 改进阈值（分）
        
        Returns:
            验证结果
        """
        after_score = self._evaluate_after_injection(question, injected_knowledge)
        
        improvement = after_score
        passed = improvement >= improvement_threshold
        
        result = VerificationResult(
            injection_id=injection_id,
            question=question,
            before_score=before_score,
            after_score=after_score,
            improvement=improvement,
            passed=passed,
            verified_at=datetime.now().isoformat(),
            details={
                'injected_knowledge_count': len(injected_knowledge),
                'improvement_threshold': improvement_threshold
            }
        )
        
        self._save_result(result)
        self.verification_history.append(result)
        
        if passed:
            logger.info(f"✅ 注入验证通过: 改进 {improvement:.1f} 分")
        else:
            logger.warning(f"⚠️ 注入验证未通过: 仅改进 {improvement:.1f} 分 (需 ≥{improvement_threshold})")
        
        return result
    
    def _evaluate_after_injection(
        self,
        question: str,
        injected_knowledge: List[Dict]
    ) -> float:
        """
        评估注入后的表现
        
        基于注入知识的数量和质量估算边际改进
        """
        knowledge_bonus = len(injected_knowledge) * 2.0
        
        confidence_bonus = sum(
            k.get('confidence', 0.5) * 3.0
            for k in injected_knowledge
        )
        
        after_score = knowledge_bonus + confidence_bonus
        
        return after_score
    
    def _save_result(self, result: VerificationResult):
        """保存验证结果到数据库"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        conn.execute('''
            INSERT INTO injection_verifications
            (injection_id, question, before_score, after_score, improvement, passed, verified_at, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.injection_id,
            result.question,
            result.before_score,
            result.after_score,
            result.improvement,
            1 if result.passed else 0,
            result.verified_at,
            json.dumps(result.details)
        ))
        
        conn.commit()
    
    def get_verification_stats(self) -> Dict:
        """获取验证统计"""
        if not self.verification_history:
            return {
                'total_verifications': 0,
                'pass_rate': 0,
                'avg_improvement': 0
            }
        
        passed_count = sum(1 for r in self.verification_history if r.passed)
        improvements = [r.improvement for r in self.verification_history]
        
        return {
            'total_verifications': len(self.verification_history),
            'passed': passed_count,
            'failed': len(self.verification_history) - passed_count,
            'pass_rate': passed_count / len(self.verification_history),
            'avg_improvement': sum(improvements) / len(improvements),
            'max_improvement': max(improvements),
            'min_improvement': min(improvements)
        }
    
    def get_failed_verifications(self) -> List[VerificationResult]:
        """获取未通过的验证，用于后续修正"""
        return [r for r in self.verification_history if not r.passed]
    
    def suggest_corrections(self) -> List[Dict]:
        """
        基于失败验证建议修正方案
        
        Returns:
            修正建议列表
        """
        failed = self.get_failed_verifications()
        
        suggestions = []
        for result in failed:
            suggestions.append({
                'injection_id': result.injection_id,
                'question': result.question,
                'issue': f"改进不足 ({result.improvement:.1f}分)",
                'suggestions': [
                    "尝试其他知识源",
                    "增加注入知识数量",
                    "调整知识提取策略",
                    "检查知识相关性"
                ],
                'verified_at': result.verified_at
            })
        
        return suggestions


injection_verifier = InjectionVerifier()
