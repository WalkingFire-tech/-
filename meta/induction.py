"""
离线归纳总结器 - 从经验池挖掘通用模式
定期分析经验数据,生成新的学习规则
"""
import json
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
from loguru import logger
from infrastructure.config_manager import config


class PatternMiner:
    """经验模式挖掘器"""
    
    def __init__(self):
        self.min_support = 3  # 最小支持度
        self.patterns: List[Dict] = []
        
        logger.info("模式挖掘器初始化完成")
    
    def mine_patterns(self, days: int = 7) -> List[Dict]:
        """挖掘最近N天的经验模式"""
        
        experiences = self._load_recent_experiences(days)
        
        if not experiences:
            logger.warning("无足够经验数据")
            return []
        
        logger.info(f"加载{len(experiences)}条经验,开始挖掘模式")
        
        patterns = []
        
        intent_patterns = self._mine_intent_patterns(experiences)
        patterns.extend(intent_patterns)
        
        model_patterns = self._mine_model_patterns(experiences)
        patterns.extend(model_patterns)
        
        quality_patterns = self._mine_quality_patterns(experiences)
        patterns.extend(quality_patterns)
        
        self.patterns = patterns
        
        logger.info(f"挖掘出{len(patterns)}个模式")
        
        return patterns
    
    def _load_recent_experiences(self, days: int) -> List[Dict]:
        """加载最近的经验（使用 ExperiencePool 类）"""
        from infrastructure.experience_pool import ExperiencePool
        
        pool = ExperiencePool()
        db_path = pool.db_path
        threshold = datetime.now() - timedelta(days=days)

        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                # 查询表名（动态获取，兼容复数或单数）
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='experiences' OR name='experience')")
                table_row = cur.fetchone()
                if not table_row:
                    logger.error("经验池表不存在，请检查数据库初始化")
                    return []
                table_name = table_row[0]

                cur = conn.execute(f'''
                    SELECT intent_type, raw_input, model_name, quality_score,
                           success, duration, user_feedback
                    FROM {table_name}
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (threshold.isoformat(),))

                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"加载经验失败: {e}")
            return []
    
    def _mine_intent_patterns(self, experiences: List[Dict]) -> List[Dict]:
        """挖掘意图模式"""
        patterns = []
        
        intent_success = Counter()
        intent_failure = Counter()
        
        for exp in experiences:
            intent_type = exp["intent_type"]
            if exp["success"]:
                intent_success[intent_type] += 1
            else:
                intent_failure[intent_type] += 1
        
        for intent_type, success_count in intent_success.items():
            failure_count = intent_failure.get(intent_type, 0)
            total = success_count + failure_count
            
            if total >= self.min_support:
                success_rate = success_count / total
                
                if success_rate < 0.5:
                    patterns.append({
                        "type": "intent_failure",
                        "condition": f"intent_type == '{intent_type}'",
                        "insight": f"意图{intent_type}成功率仅{success_rate:.1%}",
                        "support": total,
                        "confidence": 1 - success_rate,
                        "suggestion": "需要改进该意图的处理策略"
                    })
        
        return patterns
    
    def _mine_model_patterns(self, experiences: List[Dict]) -> List[Dict]:
        """挖掘模型使用模式"""
        patterns = []
        
        model_intent_quality = {}
        
        for exp in experiences:
            key = (exp["model_name"], exp["intent_type"])
            if key not in model_intent_quality:
                model_intent_quality[key] = []
            model_intent_quality[key].append(exp["quality_score"])
        
        for (model, intent), qualities in model_intent_quality.items():
            if len(qualities) >= self.min_support:
                avg_quality = sum(qualities) / len(qualities)
                
                if avg_quality < 50:
                    patterns.append({
                        "type": "model_mismatch",
                        "condition": f"model == '{model}' and intent_type == '{intent}'",
                        "insight": f"模型{model}处理{intent}平均质量{avg_quality:.1f}",
                        "support": len(qualities),
                        "confidence": (100 - avg_quality) / 100,
                        "suggestion": f"建议为{intent}任务更换模型"
                    })
                
                elif avg_quality > 80:
                    patterns.append({
                        "type": "model_excellent",
                        "condition": f"model == '{model}' and intent_type == '{intent}'",
                        "insight": f"模型{model}处理{intent}表现优秀({avg_quality:.1f})",
                        "support": len(qualities),
                        "confidence": avg_quality / 100,
                        "suggestion": f"推荐{model}作为{intent}的首选模型"
                    })
        
        return patterns
    
    def _mine_quality_patterns(self, experiences: List[Dict]) -> List[Dict]:
        """挖掘质量模式"""
        patterns = []
        
        low_quality_count = sum(1 for exp in experiences if exp["quality_score"] < 30)
        total_count = len(experiences)
        
        if total_count >= self.min_support:
            low_quality_rate = low_quality_count / total_count
            
            if low_quality_rate > 0.3:
                patterns.append({
                    "type": "quality_issue",
                    "condition": "quality_score < 30",
                    "insight": f"{low_quality_rate:.1%}的任务质量低于30分",
                    "support": low_quality_count,
                    "confidence": low_quality_rate,
                    "suggestion": "需要改进任务处理流程或模型选择"
                })
        
        return patterns


class RuleGenerator:
    """规则生成器"""
    
    def __init__(self):
        self.generated_rules: List[Dict] = []
        
        logger.info("规则生成器初始化完成")
    
    def generate_rules(self, patterns: List[Dict]) -> List[Dict]:
        """从模式生成规则"""
        
        rules = []
        
        for pattern in patterns:
            rule = self._pattern_to_rule(pattern)
            if rule:
                rules.append(rule)
        
        self.generated_rules = rules
        
        logger.info(f"生成{len(rules)}条规则")
        
        return rules
    
    def _pattern_to_rule(self, pattern: Dict) -> Optional[Dict]:
        """将模式转换为规则"""
        
        if pattern["support"] < 3:
            return None
        
        if pattern["confidence"] < 0.5:
            return None
        
        rule = {
            "condition": pattern["condition"],
            "action": self._determine_action(pattern),
            "priority": self._calculate_priority(pattern),
            "source": "induction",
            "metadata": {
                "pattern_type": pattern["type"],
                "insight": pattern["insight"],
                "support": pattern["support"],
                "confidence": pattern["confidence"]
            },
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        return rule
    
    def _determine_action(self, pattern: Dict) -> str:
        """确定规则动作"""
        
        if pattern["type"] == "intent_failure":
            return "trigger_reflection"
        
        elif pattern["type"] == "model_mismatch":
            return "reroute:best_alternative"
        
        elif pattern["type"] == "model_excellent":
            condition_parts = pattern['condition'].split('==')
            if len(condition_parts) > 1:
                model_name = condition_parts[1].strip().strip("'")
                return f"prefer_model:{model_name}"
            return "prefer_model:unknown"
        
        elif pattern["type"] == "quality_issue":
            return "enable_strict_quality_check"
        
        else:
            return "log_warning"
    
    def _calculate_priority(self, pattern: Dict) -> int:
        """计算规则优先级"""
        
        base_priority = 3
        
        if pattern["confidence"] > 0.8:
            base_priority += 2
        elif pattern["confidence"] > 0.6:
            base_priority += 1
        
        if pattern["support"] > 10:
            base_priority += 1
        
        return min(base_priority, 5)
    
    def save_rules(self, rules: List[Dict], 
                   db_path: str = "learning_rules.db") -> None:
        """保存生成的规则"""
        
        try:
            with sqlite3.connect(db_path) as conn:
                for rule in rules:
                    conn.execute('''
                        INSERT INTO learning_rules
                        (condition, action, priority, created_at, status, source, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rule["condition"],
                        rule["action"],
                        rule["priority"],
                        rule["created_at"],
                        rule["status"],
                        rule["source"],
                        json.dumps(rule["metadata"], ensure_ascii=False)
                    ))
            
            logger.info(f"保存{len(rules)}条归纳规则")
        
        except Exception as e:
            logger.error(f"保存规则失败: {e}")


class InductionScheduler:
    """归纳调度器"""
    
    def __init__(self):
        self.miner = PatternMiner()
        self.generator = RuleGenerator()
        
        logger.info("归纳调度器初始化完成")
    
    def run_induction(self, days: int = 7) -> Dict:
        """执行归纳任务"""
        
        logger.info(f"开始归纳任务(最近{days}天)")
        
        patterns = self.miner.mine_patterns(days)
        
        if not patterns:
            return {
                "success": False,
                "message": "未发现显著模式",
                "patterns": 0,
                "rules": 0
            }
        
        rules = self.generator.generate_rules(patterns)
        
        if rules:
            # 使用试用期机制保存规则
            try:
                from infrastructure.rule_trial_manager import rule_trial_manager
                
                for rule in rules:
                    rule_trial_manager.create_trial_rule(
                        condition=rule["condition"],
                        action=rule["action"],
                        confidence=rule["confidence"],
                        source=rule.get("source", "induction")
                    )
                
                logger.info(f"已创建 {len(rules)} 条试用期规则")
            except Exception as e:
                logger.warning(f"试用期创建失败，使用常规保存: {e}")
                self.generator.save_rules(rules)
        
        result = {
            "success": True,
            "message": f"发现{len(patterns)}个模式,生成{len(rules)}条规则",
            "patterns": len(patterns),
            "rules": len(rules),
            "pattern_details": patterns[:5],
            "rule_details": rules[:5],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"归纳完成: {result['message']}")
        
        self.activate_pending_rules()
        
        return result
    
    def activate_pending_rules(self, min_confidence: float = 0.6) -> int:
        """激活待定规则"""
        try:
            import sqlite3
            with sqlite3.connect("learning_rules.db") as conn:
                cur = conn.execute('''
                    UPDATE learning_rules
                    SET status = 'active'
                    WHERE status = 'pending' AND confidence >= ?
                ''', (min_confidence,))
                
                activated = cur.rowcount
                conn.commit()
                
                logger.info(f"激活{activated}条待定规则")
                return activated
        
        except Exception as e:
            logger.error(f"激活规则失败: {e}")
            return 0


induction_scheduler = InductionScheduler()