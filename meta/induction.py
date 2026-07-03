"""
离线归纳总结器 - 从经验池挖掘通用模式
定期分析经验数据,生成新的学习规则

改进：
- 时间衰减权重：最近经验权重更高
- 增量归纳：支持增量更新
- 模式验证：验证生成模式的有效性
"""
import json
import sqlite3
import math
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
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
                           success, duration, user_feedback, timestamp
                    FROM {table_name}
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (threshold.isoformat(),))

                experiences = [dict(row) for row in cur.fetchall()]
                
                # 添加时间衰减权重
                now = datetime.now()
                for exp in experiences:
                    if 'timestamp' in exp and exp['timestamp']:
                        try:
                            exp_time = datetime.fromisoformat(exp['timestamp'])
                            age_days = (now - exp_time).days
                            # 指数衰减：最近的经验权重更高
                            exp['weight'] = math.exp(-age_days / (days / 2))
                        except:
                            exp['weight'] = 0.5  # 默认权重
                    else:
                        exp['weight'] = 0.5
                
                return experiences
        except Exception as e:
            logger.error(f"加载经验失败: {e}")
            return []
    
    def _mine_intent_patterns(self, experiences: List[Dict]) -> List[Dict]:
        """挖掘意图模式（带时间衰减权重）"""
        patterns = []
        
        intent_success = Counter()
        intent_failure = Counter()
        intent_weight = Counter()  # 加权计数
        
        for exp in experiences:
            intent_type = exp["intent_type"]
            weight = exp.get("weight", 1.0)
            
            if exp["success"]:
                intent_success[intent_type] += weight
            else:
                intent_failure[intent_type] += weight
            intent_weight[intent_type] += weight
        
        for intent_type, success_count in intent_success.items():
            failure_count = intent_failure.get(intent_type, 0)
            total_weight = intent_weight.get(intent_type, 0)
            
            if total_weight >= self.min_support:
                success_rate = success_count / total_weight if total_weight > 0 else 0
                
                if success_rate < 0.5:
                    patterns.append({
                        "type": "intent_failure",
                        "condition": f"intent_type == '{intent_type}'",
                        "insight": f"意图{intent_type}成功率仅{success_rate:.1%}",
                        "support": total_weight,
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
        
        if pattern["support"] < 3.0:
            return None
        
        if pattern["confidence"] < 0.5:
            return None
        
        rule = {
            "condition": pattern["condition"],
            "action": self._determine_action(pattern),
            "priority": self._calculate_priority(pattern),
            "confidence": pattern["confidence"],
            "source": "induction",
            "metadata": {
                "pattern_type": pattern["type"],
                "insight": pattern["insight"],
                "support": pattern["support"],
                "confidence": pattern["confidence"]
            },
            "created_at": datetime.now().isoformat(),
            "status": "canary"
        }
        
        return rule
    
    def _determine_action(self, pattern: Dict) -> str:
        """确定规则动作"""
        import re
        
        if pattern["type"] == "intent_failure":
            return "trigger_reflection"
        
        elif pattern["type"] == "model_mismatch":
            return "reroute:best_alternative"
        
        elif pattern["type"] == "model_excellent":
            match = re.search(r"model == '([\w\-\.]+)'", pattern.get('condition', ''))
            if match:
                return f"prefer_model:{match.group(1)}"
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
                   db_path: str = "data/learning_rules.db") -> None:
        """保存生成的规则"""
        
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS learning_rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        condition TEXT,
                        action TEXT,
                        priority INTEGER,
                        confidence REAL,
                        created_at TEXT,
                        updated_at TEXT,
                        status TEXT,
                        source TEXT,
                        metadata TEXT
                    )
                ''')
                
                for rule in rules:
                    conn.execute('''
                        INSERT INTO learning_rules
                        (condition, action, priority, created_at, status, source, metadata, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rule["condition"],
                        rule["action"],
                        rule["priority"],
                        rule["created_at"],
                        rule["status"],
                        rule["source"],
                        json.dumps(rule["metadata"], ensure_ascii=False),
                        rule.get("confidence", 0.5)
                    ))
            
            logger.info(f"保存{len(rules)}条归纳规则")
        
        except Exception as e:
            logger.error(f"保存规则失败: {e}")


class InductionScheduler:
    """归纳调度器"""
    
    def __init__(self):
        self.miner = PatternMiner()
        self.generator = RuleGenerator()
        
        self._trial_manager = None
        try:
            from infrastructure.rule_trial_manager import rule_trial_manager
            self._trial_manager = rule_trial_manager
            logger.info("试用期管理器已加载")
        except ImportError:
            logger.warning("rule_trial_manager不可用，规则将直接保存")
        
        logger.info("归纳调度器初始化完成")
    
    def _calculate_rule_confidence(self, rule: Dict, pattern_data: List[Dict]) -> float:
        """
        基于真实数据的规则置信度计算（第三刀）
        
        使用贝叶斯平滑处理小样本问题
        """
        # 查找匹配该规则的样本
        matches = []
        for data in pattern_data:
            if self._rule_matches(data, rule):
                matches.append(data)
        
        if not matches:
            return 0.5  # 无数据，中性
        
        # 计算成功率
        success_count = sum(1 for m in matches if m.get("success", False))
        raw_success_rate = success_count / len(matches)
        
        # 贝叶斯平滑（小样本量时拉向0.5）
        alpha = 2  # 先验强度
        smoothed = (success_count + alpha * 0.5) / (len(matches) + alpha)
        
        # 加上复杂度和工具调用的修正
        complexity_boost = 0.05 if rule.get("complexity") == "complex" else 0
        tool_boost = 0.05 if rule.get("uses_tools") else 0
        
        return min(0.95, smoothed + complexity_boost + tool_boost)
    
    def _rule_matches(self, data: Dict, rule: Dict) -> bool:
        """检查数据是否匹配规则条件"""
        condition = rule.get("condition", "")
        
        # 简单的条件匹配逻辑
        if "intent_type ==" in condition:
            import re
            match = re.search(r"intent_type == '(\w+)'", condition)
            if match:
                intent = match.group(1)
                return data.get("intent_type") == intent
        
        if "model ==" in condition:
            import re
            match = re.search(r"model == '([\w\-\.]+)'", condition)
            if match:
                model = match.group(1)
                return data.get("model_name") == model
        
        return False
    
    def run_induction(self, days: int = 7) -> Dict:
        """执行归纳任务"""
        
        logger.info(f"开始归纳任务(最近{days}天)")
        
        patterns = self.miner.mine_patterns(days)
        
        if not patterns:
            return {
                "success": False,
                "error": "未发现显著模式",
                "message": "未发现显著模式",
                "patterns": 0,
                "rules": 0
            }
        
        rules = self.generator.generate_rules(patterns)
        
        # ========== 第三刀：基于真实成功率计算置信度 ==========
        # 获取经验数据用于置信度计算
        experiences = self.miner._load_recent_experiences(days)
        
        for rule in rules:
            # 使用新方法计算置信度
            rule["confidence"] = self._calculate_rule_confidence(rule, experiences)
            rule["updated_at"] = datetime.now().isoformat()
            logger.debug(f"规则置信度: {rule.get('condition', '')[:30]} -> {rule['confidence']:.3f}")
        
        if rules:
            if self._trial_manager:
                try:
                    for rule in rules:
                        self._trial_manager.create_trial_rule(
                            condition=rule["condition"],
                            action=rule["action"],
                            confidence=rule["confidence"],
                            source=rule.get("source", "induction")
                        )
                    
                    logger.info(f"已创建 {len(rules)} 条试用期规则")
                except Exception as e:
                    logger.warning(f"试用期创建失败，使用常规保存: {e}")
                    self.generator.save_rules(rules)
            else:
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
    
    def activate_pending_rules(self, min_confidence: float = 0.4) -> int:
        """激活待定规则：置信度达标的直接激活，低于阈值的晋升到trial"""
        try:
            import sqlite3
            with sqlite3.connect("data/learning_rules.db") as conn:
                cur = conn.execute('''
                    UPDATE learning_rules
                    SET status = 'active'
                    WHERE status = 'pending' AND confidence >= ?
                ''', (min_confidence,))
                
                activated = cur.rowcount
                
                cur2 = conn.execute('''
                    UPDATE learning_rules
                    SET status = 'trial', promoted_at = ?,
                        promotion_reason = '归纳调度晋升试用：置信度不足但值得验证'
                    WHERE status = 'pending' AND confidence >= 0.3
                ''', (datetime.now().isoformat(),))
                
                promoted = cur2.rowcount
                conn.commit()
                
                logger.info(f"激活{activated}条规则，晋升{promoted}条到试用期")
                return activated + promoted
        
        except Exception as e:
            logger.error(f"激活规则失败: {e}")
            return 0


induction_scheduler = InductionScheduler()