"""
知识注入验证闭环
实现完整的"注入→验证→修正"流程
"""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class KnowledgeVerificationLoop:
    """
    知识验证闭环
    
    完整流程：
    1. 注入前评估（记录基准）
    2. 执行知识注入
    3. 注入后评估
    4. 验证效果（改进是否达标）
    5. 未达标则触发修正
    """
    
    def __init__(self, db_path: str = "data/verification_loop.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化验证数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        # 验证循环记录表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS verification_loops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id TEXT UNIQUE NOT NULL,
                question TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                conn.commit()
                
                -- 注入前
                before_score REAL,
                before_confidence REAL,
                before_knowledge_count INTEGER,
                
                -- 注入
                injection_source TEXT,
                injected_knowledge_count INTEGER,
                injection_details TEXT,
                
                -- 注入后
                after_score REAL,
                after_confidence REAL,
                after_knowledge_count INTEGER,
                
                -- 验证
                improvement REAL,
                passed INTEGER,
                threshold REAL,
                
                -- 修正
                needs_correction INTEGER DEFAULT 0,
                correction_actions TEXT,
                correction_result TEXT,
                
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        conn.commit()
        logger.info(f"🔄 知识验证闭环已初始化: {self.db_path}")
    
    def start_verification_loop(
        self,
        question: str,
        before_score: float,
        before_confidence: float,
        before_knowledge_count: int = 0
    ) -> str:
        """
        开始验证循环
        
        Args:
            question: 问题
            before_score: 注入前评分
            before_confidence: 注入前置信度
            before_knowledge_count: 注入前知识数量
        
        Returns:
            循环ID
        """
        loop_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            INSERT INTO verification_loops
            (loop_id, question, timestamp, before_score, before_confidence, 
             before_knowledge_count, status)
            VALUES (?, ?, ?, ?, ?, ?, 'injecting')
        ''', (
            loop_id, question, datetime.now().isoformat(),
            before_score, before_confidence, before_knowledge_count
        ))
        conn.commit()
        
        logger.info(f"🔄 开始验证循环: {loop_id} - {question[:50]}...")
        return loop_id
    
    def record_injection(
        self,
        loop_id: str,
        injection_source: str,
        injected_knowledge: List[Dict]
    ):
        """
        记录注入过程
        
        Args:
            loop_id: 循环ID
            injection_source: 注入来源
            injected_knowledge: 注入的知识列表
        """
        import json
        
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            UPDATE verification_loops
            SET injection_source = ?,
                injected_knowledge_count = ?,
                injection_details = ?,
                status = 'verifying'
            WHERE loop_id = ?
        ''', (
            injection_source,
            len(injected_knowledge),
            json.dumps(injected_knowledge[:5], ensure_ascii=False),  # 只存前5条
            loop_id
        ))
        conn.commit()
        
        logger.info(f"💉 记录注入: {len(injected_knowledge)}条知识来自{injection_source}")
    
    def complete_verification(
        self,
        loop_id: str,
        after_score: float,
        after_confidence: float,
        after_knowledge_count: int,
        threshold: float = 5.0
    ) -> Dict:
        """
        完成验证
        
        Args:
            loop_id: 循环ID
            after_score: 注入后评分
            after_confidence: 注入后置信度
            after_knowledge_count: 注入后知识数量
            threshold: 改进阈值
        
        Returns:
            验证结果
        """
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        cursor = conn.execute(
            'SELECT * FROM verification_loops WHERE loop_id = ?',
            (loop_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return {'error': '循环不存在'}
        
        before_score = row['before_score']
        
        improvement = after_score - before_score
        passed = improvement >= threshold
        needs_correction = 0 if passed else 1
        
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            UPDATE verification_loops
            SET after_score = ?,
                after_confidence = ?,
                after_knowledge_count = ?,
                improvement = ?,
                passed = ?,
                threshold = ?,
                needs_correction = ?,
                status = 'completed'
            WHERE loop_id = ?
        ''', (
            after_score, after_confidence, after_knowledge_count,
            improvement, 1 if passed else 0, threshold,
            needs_correction, loop_id
        ))
        conn.commit()
        
        result = {
            'loop_id': loop_id,
            'before_score': before_score,
            'after_score': after_score,
            'improvement': improvement,
            'passed': passed,
            'threshold': threshold,
            'needs_correction': needs_correction
        }
        
        if passed:
            logger.info(f"✅ 验证通过: 改进{improvement:.1f}分 (≥{threshold})")
        else:
            logger.warning(f"⚠️ 验证未通过: 仅改进{improvement:.1f}分 (<{threshold})，需要修正")
        
        return result
    
    def get_correction_candidates(self) -> List[Dict]:
        """获取需要修正的验证循环"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        cursor = conn.execute('''
            SELECT * FROM verification_loops
            WHERE needs_correction = 1 AND correction_result IS NULL
            ORDER BY timestamp DESC
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def apply_correction(
        self,
        loop_id: str,
        correction_actions: List[str],
        correction_result: str
    ):
        """
        应用修正
        
        Args:
            loop_id: 循环ID
            correction_actions: 修正动作列表
            correction_result: 修正结果
        """
        import json
        
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            UPDATE verification_loops
            SET correction_actions = ?,
                correction_result = ?,
                status = 'corrected'
            WHERE loop_id = ?
        ''', (
            json.dumps(correction_actions, ensure_ascii=False),
            correction_result,
            loop_id
        ))
        conn.commit()
        
        logger.info(f"🔧 应用修正: {correction_result}")
    
    def get_statistics(self) -> Dict:
        """获取验证统计"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        total = conn.execute(
            'SELECT COUNT(*) FROM verification_loops'
        ).fetchone()[0]
        
        passed = conn.execute(
            'SELECT COUNT(*) FROM verification_loops WHERE passed = 1'
        ).fetchone()[0]
        
        corrected = conn.execute(
            'SELECT COUNT(*) FROM verification_loops WHERE status = "corrected"'
        ).fetchone()[0]
        
        avg_improvement = conn.execute(
            'SELECT AVG(improvement) FROM verification_loops WHERE improvement IS NOT NULL'
        ).fetchone()[0] or 0
        
        return {
            'total_loops': total,
            'passed': passed,
            'failed': total - passed,
            'corrected': corrected,
            'pass_rate': passed / max(1, total),
            'avg_improvement': avg_improvement
        }


knowledge_verification_loop = KnowledgeVerificationLoop()
