"""
梦境整合模块 (Dream Integration)
参考Claude 5的梦境整合机制，空闲时整理记忆
"""
import sqlite3
import threading
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

ALLOWED_INTENT_TYPES = {
    'code', 'question', 'chat', 'memory', 'calculation',
    'feedback', 'meta', 'document', 'analysis', 'comparison'
}
MAX_EXPERIENCES = 10000


class DreamIntegrator:
    """梦境整合器 - 空闲时整理记忆，生成跨任务关联规则"""
    
    def __init__(self, db_path: str = "data/experience_pool.db"):
        self.db_path = db_path
        self.rules_db_path = "data/learning_rules.db"
        self._lock = threading.Lock()
        
        Path("data").mkdir(exist_ok=True)
        
    def integrate(self, days: int = 7) -> Dict[str, Any]:
        """
        执行梦境整合
        
        Args:
            days: 扫描最近几天的经验
        
        Returns:
            整合结果统计
        """
        with self._lock:
            logger.info(f"开始梦境整合，扫描最近{days}天的经验...")
            
            isolated_experiences = self._find_isolated_experiences(days)
            logger.info(f"发现{len(isolated_experiences)}条孤立成功经验")
            
            cross_task_patterns = self._discover_cross_task_patterns(isolated_experiences)
            logger.info(f"发现{len(cross_task_patterns)}个跨任务模式")
            
            new_rules = self._generate_integration_rules(cross_task_patterns)
            logger.info(f"生成{len(new_rules)}条整合规则")
            
            cleaned = self._cleanup_redundant_memories()
            
            result = {
                "isolated_experiences": len(isolated_experiences),
                "cross_task_patterns": len(cross_task_patterns),
                "new_rules": len(new_rules),
                "cleaned_memories": cleaned,
                "integrated_at": datetime.now().isoformat()
            }
            
            logger.info(f"梦境整合完成: {result}")
            return result
    
    def _find_isolated_experiences(self, days: int) -> List[Dict]:
        """
        查找孤立的成功经验
        孤立定义：未被任何规则引用的成功经验
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_input, intent_type, model_name, response, quality_score
                FROM experiences
                WHERE timestamp >= ?
                AND quality_score >= 0.7
                ORDER BY timestamp DESC
                LIMIT ?
            """, (cutoff_date, MAX_EXPERIENCES))
            
            experiences = []
            for row in cursor.fetchall():
                experiences.append({
                    "id": row[0],
                    "user_input": row[1],
                    "intent_type": row[2],
                    "model_name": row[3],
                    "response": row[4],
                    "quality_score": row[5]
                })
        
        isolated = []
        with sqlite3.connect(self.rules_db_path) as conn_rules:
            cursor_rules = conn_rules.cursor()
            
            for exp in experiences:
                cursor_rules.execute("""
                    SELECT COUNT(*) FROM learning_rules
                    WHERE condition LIKE ?
                """, (f"%{exp['id']}%",))
                
                count = cursor_rules.fetchone()[0]
                if count == 0:
                isolated.append(exp)
        
        conn.close()
        conn_rules.close()
        
        return isolated
    
    def _discover_cross_task_patterns(self, experiences: List[Dict]) -> List[Dict]:
        """
        发现跨任务关联模式
        例如：用户常在代码问题后问数学计算
        """
        patterns = []
        
        # 按意图类型分组
        intent_groups = {}
        for exp in experiences:
            intent = exp["intent_type"]
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append(exp)
        
        # 分析意图转换模式
        if len(experiences) >= 10:
            # 统计意图转换频率
            transitions = {}
            for i in range(len(experiences) - 1):
                current_intent = experiences[i]["intent_type"]
                next_intent = experiences[i + 1]["intent_type"]
                
                key = f"{current_intent}→{next_intent}"
                transitions[key] = transitions.get(key, 0) + 1
            
            # 找出高频转换（超过3次）
            for transition, count in transitions.items():
                if count >= 3:
                    patterns.append({
                        "type": "intent_transition",
                        "pattern": transition,
                        "frequency": count,
                        "confidence": min(count / len(experiences), 1.0)
                    })
        
        # 分析模型使用模式
        model_usage = {}
        for exp in experiences:
            intent = exp["intent_type"]
            model = exp["model_name"]
            key = f"{intent}→{model}"
            model_usage[key] = model_usage.get(key, 0) + 1
        
        for usage, count in model_usage.items():
            if count >= 5:
                patterns.append({
                    "type": "model_preference",
                    "pattern": usage,
                    "frequency": count,
                    "confidence": min(count / len(experiences), 1.0)
                })
        
        return patterns
    
    def _generate_integration_rules(self, patterns: List[Dict]) -> List[Dict]:
        """
        根据跨任务模式生成整合规则
        """
        new_rules = []
        
        with sqlite3.connect(self.rules_db_path) as conn:
            cursor = conn.cursor()
            
            for pattern in patterns:
                if pattern["type"] == "intent_transition":
                    parts = pattern["pattern"].split("→")
                    if len(parts) == 2:
                        intent_type = parts[0].strip()
                        next_intent = parts[1].strip()
                        
                        if intent_type not in ALLOWED_INTENT_TYPES:
                            logger.warning(f"跳过非法意图类型: {intent_type}")
                            continue
                        
                        if next_intent not in ALLOWED_INTENT_TYPES:
                            logger.warning(f"跳过非法目标意图: {next_intent}")
                            continue
                        
                        condition_data = json.dumps({
                            "type": "intent_equals",
                            "intent_type": intent_type
                        }, ensure_ascii=False)
                        
                        action_data = json.dumps({
                            "type": "prepare_for",
                            "target_intent": next_intent
                        }, ensure_ascii=False)
                        
                        cursor.execute("""
                            INSERT INTO learning_rules
                            (condition, action, confidence, source, description, status, created_at)
                            VALUES (?, ?, ?, ?, ?, 'pending', ?)
                        """, (
                            condition_data,
                            action_data,
                            pattern["confidence"],
                            "dream_integration",
                            f"用户在{intent_type}后常问{next_intent}",
                            datetime.now().isoformat()
                        ))
                        
                        new_rules.append({
                            "condition": condition_data,
                            "action": action_data,
                            "confidence": pattern["confidence"]
                        })
                
                elif pattern["type"] == "model_preference":
                    parts = pattern["pattern"].split("→")
                    if len(parts) == 2:
                        intent_type = parts[0].strip()
                        model_name = parts[1].strip()
                        
                        if intent_type not in ALLOWED_INTENT_TYPES:
                            logger.warning(f"跳过非法意图类型: {intent_type}")
                            continue
                        
                        condition_data = json.dumps({
                            "type": "intent_equals",
                            "intent_type": intent_type
                        }, ensure_ascii=False)
                        
                        action_data = json.dumps({
                            "type": "use_model",
                            "model": model_name
                        }, ensure_ascii=False)
                        
                        cursor.execute("""
                            INSERT INTO learning_rules
                            (condition, action, confidence, source, description, status, created_at)
                            VALUES (?, ?, ?, ?, ?, 'pending', ?)
                        """, (
                            condition_data,
                            action_data,
                            pattern["confidence"],
                            "dream_integration",
                            f"{intent_type}意图偏好使用{model_name}",
                            datetime.now().isoformat()
                        ))
                        
                        new_rules.append({
                            "condition": condition_data,
                            "action": action_data,
                            "confidence": pattern["confidence"]
                        })
            
            conn.commit()
        
        return new_rules
    
    def _cleanup_redundant_memories(self) -> int:
        """
        清理冗余记忆
        - 删除质量分过低的经验（< 0.3）
        - 删除重复的失败案例
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM experiences
                WHERE quality_score < 0.3
                AND timestamp < date('now', '-30 days')
            """)
            deleted_low_quality = cursor.rowcount
            
            cursor.execute("""
                DELETE FROM experiences
                WHERE rowid NOT IN (
                    SELECT MAX(rowid)
                    FROM experiences
                    WHERE quality_score < 0.5
                    GROUP BY user_input
                )
                AND quality_score < 0.5
            """)
            deleted_duplicates = cursor.rowcount
            
            conn.commit()
        
        total_cleaned = deleted_low_quality + deleted_duplicates
        if total_cleaned > 0:
            logger.info(f"清理冗余记忆: {total_cleaned}条")
        
        return total_cleaned


# 集成到InductionScheduler
def integrate_with_scheduler():
    """
    在meta/induction.py的InductionScheduler中集成梦境整合
    """
    code = """
from infrastructure.dream_integrator import DreamIntegrator

class InductionScheduler:
    def __init__(self):
        # ... 现有初始化 ...
        
        # 添加梦境整合器
        self.dream_integrator = DreamIntegrator()
    
    def run_dream_integration(self, days: int = 7):
        '''运行梦境整合（建议每周一次）'''
        logger.info("开始梦境整合...")
        
        try:
            result = self.dream_integrator.integrate(days)
            
            logger.info(
                f"梦境整合完成: "
                f"孤立经验{result['isolated_experiences']}条, "
                f"跨任务模式{result['cross_task_patterns']}个, "
                f"新规则{result['new_rules']}条, "
                f"清理{result['cleaned_memories']}条"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"梦境整合失败: {e}")
            return {"error": str(e)}
"""
    return code


if __name__ == "__main__":
    # 测试梦境整合
    print("=" * 60)
    print("梦境整合模块测试")
    print("=" * 60)
    
    integrator = DreamIntegrator()
    
    print("\n执行梦境整合...")
    result = integrator.integrate(days=7)
    
    print("\n整合结果:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)