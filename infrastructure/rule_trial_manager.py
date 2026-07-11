"""
规则试用期管理器
新规则先进入trial状态，在真实请求中验证效果后再激活
"""
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class RuleTrialManager:
    """规则试用期管理器"""
    
    def __init__(self, db_path: str = "data/learning_rules.db"):
        self.db_path = db_path
        
        # 试用期配置
        self.trial_threshold = 5  # 试用5次
        self.success_ratio = 0.6  # 成功率>=60%才激活
        
        logger.info("规则试用期管理器已初始化")
    
    def create_trial_rule(self, condition: str, action: str, 
                         confidence: float, source: str = "induction") -> int:
        """创建试用期规则
        
        Args:
            condition: 规则条件
            action: 规则动作
            confidence: 初始置信度
            source: 规则来源
        
        Returns:
            规则ID
        """
        db = DatabaseManager.get(self.db_path)
        cursor = db.execute('''
            INSERT INTO learning_rules
            (condition, action, confidence, status, source, priority, 
             trial_count, trial_success, created_at)
            VALUES (?, ?, ?, 'trial', ?, 5, 0, 0, ?)
        ''', (condition, action, confidence, source, datetime.now().isoformat()), commit=True)
        
        rule_id = cursor.lastrowid
        
        logger.info(f"创建试用期规则 #{rule_id}: {condition[:50]} → {action}")
        
        return rule_id
    
    def record_trial_result(self, rule_id: int, success: bool):
        """记录试用期结果
        
        Args:
            rule_id: 规则ID
            success: 是否成功
        """
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE learning_rules
            SET trial_count = trial_count + 1,
                trial_success = trial_success + ?
            WHERE id = ?
        ''', (1 if success else 0, rule_id), commit=True)
        
        row = db.query_one('''
            SELECT trial_count, trial_success, condition, action
            FROM learning_rules
            WHERE id = ?
        ''', (rule_id,))
        
        if not row:
            return
        
        trial_count, trial_success, condition, action = row
        
        if trial_count >= self.trial_threshold:
            success_ratio = trial_success / trial_count
            
            if success_ratio >= self.success_ratio:
                db.execute('''
                    UPDATE learning_rules
                    SET status = 'active'
                    WHERE id = ?
                ''', (rule_id,), commit=True)
                
                logger.info(f"✅ 试用期规则 #{rule_id} 激活 (成功率: {success_ratio:.1%})")
            else:
                db.execute('''
                    UPDATE learning_rules
                    SET status = 'expired'
                    WHERE id = ?
                ''', (rule_id,), commit=True)
                
                logger.warning(f"❌ 试用期规则 #{rule_id} 失败 (成功率: {success_ratio:.1%})")
    
    def get_trial_rules(self) -> List[Dict]:
        """获取所有试用期规则"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT id, condition, action, confidence, trial_count, trial_success
            FROM learning_rules
            WHERE status = 'trial'
        ''')
        
        rules = []
        for row in rows:
            rules.append({
                "id": row[0],
                "condition": row[1],
                "action": row[2],
                "confidence": row[3],
                "trial_count": row[4],
                "trial_success": row[5]
            })
        
        return rules
    
    def get_trial_stats(self) -> Dict:
        """获取试用期统计"""
        db = DatabaseManager.get(self.db_path)
        trial_count = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='trial'")[0]
        
        activated_count = db.query_one('''
            SELECT COUNT(*) FROM learning_rules 
            WHERE status='active' AND trial_count > 0
        ''')[0]
        
        expired_count = db.query_one('''
            SELECT COUNT(*) FROM learning_rules 
            WHERE status='expired' AND trial_count > 0
        ''')[0]
        
        return {
            "trial_count": trial_count,
            "activated_count": activated_count,
            "expired_count": expired_count,
            "total_evaluated": activated_count + expired_count
        }


rule_trial_manager = RuleTrialManager()
