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
    
    def process_timeout_trials(self, timeout_days: int = 30) -> Dict:
        """处理超时trial规则：根据置信度和匹配记录决定激活或过期

        逻辑：
        - 超时且trial_count>=5且成功率>=60%: 激活
        - 超时且trial_count>=5但成功率<60%: 过期
        - 超时且trial_count>0但<5: 给一次机会，提升置信度0.1
        - 超时且trial_count==0且置信度>=0.5: 激活（高置信度但从未匹配到，可能是条件格式问题）
        - 超时且trial_count==0且置信度<0.3: 过期（低质量规则）
        - 超时且trial_count==0且0.3<=置信度<0.5: 尝试桥接条件格式后保留

        Args:
            timeout_days: 超时天数阈值

        Returns:
            处理统计
        """
        db = DatabaseManager.get(self.db_path)
        cutoff = datetime.now().timestamp() - timeout_days * 86400

        rows = db.query('''
            SELECT id, condition, action, confidence, trial_count, trial_success, created_at
            FROM learning_rules
            WHERE status = 'trial'
        ''')

        activated = 0
        expired = 0
        bridged = 0
        promoted = 0

        for row in rows:
            rule_id, condition, action, confidence, trial_count, trial_success, created_at = row

            if not created_at:
                continue

            try:
                created_ts = datetime.fromisoformat(created_at).timestamp()
            except (ValueError, TypeError):
                continue

            if created_ts > cutoff:
                continue

            if trial_count >= self.trial_threshold:
                success_ratio = trial_success / trial_count if trial_count > 0 else 0
                if success_ratio >= self.success_ratio:
                    db.execute("UPDATE learning_rules SET status='active' WHERE id=?", (rule_id,), commit=True)
                    activated += 1
                else:
                    db.execute("UPDATE learning_rules SET status='expired' WHERE id=?", (rule_id,), commit=True)
                    expired += 1
            elif trial_count > 0:
                new_conf = min(confidence + 0.1, 1.0)
                db.execute("UPDATE learning_rules SET confidence=? WHERE id=?", (new_conf, rule_id), commit=True)
                promoted += 1
            elif confidence >= 0.5:
                db.execute("UPDATE learning_rules SET status='active' WHERE id=?", (rule_id,), commit=True)
                activated += 1
            elif confidence < 0.3:
                db.execute("UPDATE learning_rules SET status='expired' WHERE id=?", (rule_id,), commit=True)
                expired += 1
            else:
                bridged_condition = self._bridge_condition_format(condition)
                if bridged_condition != condition:
                    db.execute("UPDATE learning_rules SET condition=? WHERE id=?", (bridged_condition, rule_id), commit=True)
                    bridged += 1
                else:
                    db.execute("UPDATE learning_rules SET status='expired' WHERE id=?", (rule_id,), commit=True)
                    expired += 1

        result = {"activated": activated, "expired": expired, "promoted": promoted, "bridged": bridged}
        if any(v > 0 for v in result.values()):
            logger.info(f"⏰ 超时trial处理: 激活={activated}, 过期={expired}, 提升置信={promoted}, 条件桥接={bridged}")

        return result

    def _bridge_condition_format(self, condition: str) -> str:
        """桥接归纳引擎的条件格式到RuleMatcher可匹配的格式

        归纳引擎产出格式:
        - "[模式]intent_type:query text" → "intent_type == 'intent_type'"
        - "模式 keyword1 keyword2 ..." → 无法桥接，保持原样
        - 纯自然语言问句 → 无法桥接，保持原样
        """
        if condition.startswith("[模式]"):
            rest = condition[len("[模式]"):]
            if ":" in rest:
                intent_type = rest.split(":", 1)[0].strip()
                if intent_type and not any(c in intent_type for c in " \t\n"):
                    return f"intent_type == '{intent_type}'"
        return condition

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
