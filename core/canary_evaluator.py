"""
金丝雀规则验证器 (Canary Evaluator) - 进化安全网
新规则小范围A/B测试，自动验证效果

跨学科理论依据：
- 医学循证实践（EBP）：随机对照试验（RCT）
- 软件工程：金丝雀发布（Canary Deployment）
- 博弈论：多臂老虎机（MAB）验证

设计原则：
1. 新规则默认进入金丝雀模式
2. 5%流量验证效果
3. 自动晋升或拒绝
4. 记录失败原因作为负反馈
"""
import logging
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class CanaryEvaluator:
    """
    金丝雀规则验证器 - 自动验证新规则效果
    
    工作流程：
    1. 新规则标记为canary状态
    2. 5%流量使用该规则
    3. 对比金丝雀组vs对照组
    4. 效果好→晋升为active
    5. 效果差→标记为rejected
    """
    
    def __init__(
        self,
        rules_db: str = "data/learning_rules.db",
        reflection_db: str = "logs/campfire_log.db"
    ):
        self.rules_db = rules_db
        self.reflection_db = reflection_db
        
        # 配置
        self.canary_ratio = 0.05  # 5% 金丝雀流量
        self.min_samples = 20      # 最少验证样本数
        self.promotion_threshold = 0.05  # 置信度提升阈值
        self.rejection_threshold = -0.02  # 置信度下降阈值
        self.observation_days = 3  # 观察期
        
        logger.info("🦜 金丝雀验证器已初始化")
    
    def is_canary(self, rule_id: int) -> bool:
        """判断某个规则是否处于金丝雀模式"""
        conn = sqlite3.connect(self.rules_db)
        
        try:
            cursor = conn.execute(
                'SELECT status FROM learning_rules WHERE id = ?',
                (rule_id,)
            )
            row = cursor.fetchone()
            return row and row[0] == "canary"
        finally:
            conn.close()
    
    def should_apply_rule(self, rule_id: int) -> bool:
        """
        决定是否应用该规则
        
        - 非金丝雀规则：正常应用
        - 金丝雀规则：5%概率应用
        """
        if not self.is_canary(rule_id):
            return True
        
        return random.random() < self.canary_ratio
    
    async def evaluate_rule(self, rule_id: int) -> Dict[str, str]:
        """
        评估金丝雀规则的效果
        
        Returns:
            {
                "status": "active" | "rejected" | "canary" | "pending",
                "reason": str,
                "delta": float
            }
        """
        try:
            conn = sqlite3.connect(self.rules_db)
            conn.row_factory = sqlite3.Row
            
            # 0. 检查观察期
            cursor = conn.execute(
                'SELECT created_at FROM learning_rules WHERE id = ?',
                (rule_id,)
            )
            rule_row = cursor.fetchone()
            
            if rule_row and rule_row["created_at"]:
                created_at = datetime.fromisoformat(rule_row["created_at"])
                age_days = (datetime.utcnow() - created_at).days
                
                if age_days < self.observation_days:
                    conn.close()
                    return {
                        "status": "canary",
                        "reason": f"观察期未满 ({age_days}/{self.observation_days}天)",
                        "delta": 0.0
                    }
            
            conn.close()
            
            # 1. 获取使用该规则的金丝雀样本
            conn = sqlite3.connect(self.reflection_db)
            conn.row_factory = sqlite3.Row
            
            # 使用时间窗口限制（最近observation_days天）
            time_threshold = (datetime.utcnow() - timedelta(days=self.observation_days)).isoformat()
            
            cursor = conn.execute('''
                SELECT confidence, query, final_answer, timestamp
                FROM reflection_log
                WHERE rule_used = ? AND is_canary_sample = 1
                  AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (rule_id, time_threshold, self.min_samples * 2))
            canary_samples = [dict(row) for row in cursor.fetchall()]
            
            # 2. 获取对照组（同期未使用该规则的样本）
            cursor = conn.execute('''
                SELECT confidence, query, final_answer, timestamp
                FROM reflection_log
                WHERE (rule_used IS NULL OR rule_used != ?)
                  AND is_canary_sample = 0
                  AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (rule_id, time_threshold, self.min_samples * 2))
            control_samples = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            # 3. 计算平均置信度
            if not canary_samples:
                return {
                    "status": "pending",
                    "reason": "无金丝雀样本",
                    "delta": 0.0
                }
            
            canary_conf = sum(s["confidence"] for s in canary_samples) / len(canary_samples)
            control_conf = sum(s["confidence"] for s in control_samples) / len(control_samples) if control_samples else 0.5
            
            delta = canary_conf - control_conf
            
            # 4. 做出决策
            if len(canary_samples) < self.min_samples:
                return {
                    "status": "canary",
                    "reason": f"样本不足 ({len(canary_samples)}/{self.min_samples})",
                    "delta": delta
                }
            
            if delta > self.promotion_threshold:
                self._promote_rule(rule_id)
                return {
                    "status": "active",
                    "reason": f"置信度提升 {delta:.2%}",
                    "delta": delta
                }
            
            elif delta < self.rejection_threshold:
                self._reject_rule(rule_id, delta)
                return {
                    "status": "rejected",
                    "reason": f"置信度下降 {abs(delta):.2%}",
                    "delta": delta
                }
            
            else:
                # 效果持平，继续观察
                return {
                    "status": "canary",
                    "reason": f"效果持平 ({delta:.2%})，继续观察",
                    "delta": delta
                }
                
        finally:
            conn.close()
    
    def _promote_rule(self, rule_id: int):
        """将规则晋升为全量"""
        conn = sqlite3.connect(self.rules_db)
        
        try:
            conn.execute('''
                UPDATE learning_rules
                SET status = 'active', promoted_at = ?, promotion_reason = 'canary_success'
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), rule_id))
            
            conn.commit()
            logger.info(f"✅ 规则 {rule_id} 晋升为全量")
            
        finally:
            conn.close()
    
    def _reject_rule(self, rule_id: int, delta: float):
        """拒绝规则"""
        conn = sqlite3.connect(self.rules_db)
        
        try:
            conn.execute('''
                UPDATE learning_rules
                SET status = 'rejected', rejected_at = ?, rejection_reason = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), f"置信度下降 {delta:.2%}", rule_id))
            
            conn.commit()
            logger.info(f"❌ 规则 {rule_id} 被拒绝")
            
        finally:
            conn.close()
    
    async def evaluate_all_canary_rules(self) -> Dict[str, Any]:
        """
        评估所有金丝雀规则
        
        Returns:
            {
                "evaluated": int,
                "promoted": int,
                "rejected": int,
                "pending": int,
                "details": list
            }
        """
        result = {
            "evaluated": 0,
            "promoted": 0,
            "rejected": 0,
            "pending": 0,
            "details": []
        }
        
        conn = sqlite3.connect(self.rules_db)
        
        try:
            # 获取所有金丝雀规则
            cursor = conn.execute('''
                SELECT id, condition, action, confidence, created_at
                FROM learning_rules
                WHERE status = 'canary'
            ''')
            
            canary_rules = cursor.fetchall()
            
            for rule in canary_rules:
                rule_id = rule[0]
                evaluation = await self.evaluate_rule(rule_id)
                
                result["evaluated"] += 1
                result["details"].append({
                    "rule_id": rule_id,
                    "condition": rule[1][:50],
                    **evaluation
                })
                
                if evaluation["status"] == "active":
                    result["promoted"] += 1
                elif evaluation["status"] == "rejected":
                    result["rejected"] += 1
                else:
                    result["pending"] += 1
            
            logger.info(
                f"🦜 金丝雀评估完成: "
                f"评估{result['evaluated']}条, "
                f"晋升{result['promoted']}条, "
                f"拒绝{result['rejected']}条"
            )
            
            return result
            
        finally:
            conn.close()
    
    def create_canary_rule(
        self,
        condition: str,
        action: str,
        confidence: float = 0.5,
        source: str = "induction"
    ) -> int:
        """
        创建新的金丝雀规则
        
        新规则默认进入canary状态，等待验证
        """
        conn = sqlite3.connect(self.rules_db)
        
        try:
            cursor = conn.execute('''
                INSERT INTO learning_rules
                (condition, action, confidence, source, status, created_at)
                VALUES (?, ?, ?, ?, 'canary', ?)
            ''', (condition, action, confidence, source, datetime.utcnow().isoformat()))
            
            rule_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"🦜 新规则 {rule_id} 进入金丝雀模式")
            return rule_id
            
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.rules_db)
        
        try:
            total = conn.execute('SELECT COUNT(*) FROM learning_rules').fetchone()[0]
            canary = conn.execute(
                "SELECT COUNT(*) FROM learning_rules WHERE status='canary'"
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM learning_rules WHERE status='active'"
            ).fetchone()[0]
            rejected = conn.execute(
                "SELECT COUNT(*) FROM learning_rules WHERE status='rejected'"
            ).fetchone()[0]
            
            return {
                "total_rules": total,
                "canary_rules": canary,
                "active_rules": active,
                "rejected_rules": rejected,
                "canary_ratio": canary / total if total > 0 else 0
            }
            
        finally:
            conn.close()


# 全局实例
_evaluator = None

def get_canary_evaluator(**kwargs) -> CanaryEvaluator:
    """获取金丝雀验证器实例（单例）"""
    global _evaluator
    if _evaluator is None:
        _evaluator = CanaryEvaluator(**kwargs)
    return _evaluator