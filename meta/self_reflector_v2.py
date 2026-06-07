"""
自我反思器 - 分析失败案例,生成改进规则
实现失败模式识别、规则生成、生命周期管理
"""
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config


@dataclass
class LearningRule:
    """学习规则"""
    rule_id: int
    condition: str
    action: str
    priority: int
    created_at: str
    status: str  # active, expired, conflicted, pending
    last_applied: Optional[str]
    apply_count: int
    success_count: int
    confidence: float


class SelfReflector:
    """自我反思器"""
    
    def __init__(self, adapters: dict):
        self.adapters = adapters
        self.db_path = config.get("learning_rules.db_path", "learning_rules.db")
        self._init_db()
        
        logger.info("自我反思器初始化完成")
    
    def _init_db(self):
        """初始化规则数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    condition TEXT NOT NULL,
                    action TEXT NOT NULL,
                    priority INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    last_applied TEXT,
                    apply_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.5,
                    source TEXT DEFAULT 'reflection',
                    metadata TEXT
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON learning_rules(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_priority ON learning_rules(priority)')
    
    def reflect_on_failures(self, limit: int = 20) -> List[Dict]:
        """分析最近的失败案例,生成改进规则"""
        
        failures = self._get_recent_failures(limit)
        
        if not failures:
            logger.info("无失败案例,跳过反思")
            return []
        
        logger.info(f"分析{len(failures)}个失败案例")
        
        light_llm = self._get_light_llm()
        if not light_llm:
            logger.warning("无轻量LLM,使用规则引擎")
            return self._rule_based_reflection(failures)
        
        try:
            rules = self._llm_based_reflection(failures, light_llm)
            
            if rules:
                self._save_rules(rules)
                
                bus.publish("reflection_completed", {
                    "failure_count": len(failures),
                    "rules_generated": len(rules),
                    "timestamp": datetime.now().isoformat()
                })
            
            return rules
        
        except Exception as e:
            logger.error(f"LLM反思失败: {e},使用规则引擎")
            return self._rule_based_reflection(failures)
    
    def _get_recent_failures(self, limit: int) -> List[Dict]:
        """获取最近的失败案例"""
        exp_db = config.get("stats.db_path", "experience_pool.db")
        
        try:
            with sqlite3.connect(exp_db) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute('''
                    SELECT intent_type, raw_input, model_name, quality_score, 
                           user_feedback, duration, timestamp
                    FROM experiences
                    WHERE quality_score < 30 OR success = 0
                    ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cur.fetchall()]
        
        except Exception as e:
            logger.error(f"获取失败案例失败: {e}")
            return []
    
    def _get_light_llm(self):
        """获取轻量LLM"""
        for model_name in ["qwen2.5-coder:1.5b", "mindchat", "deepseek-chat"]:
            if model_name in self.adapters:
                return self.adapters[model_name]
        return None
    
    def _llm_based_reflection(self, failures: List[Dict], llm) -> List[Dict]:
        """基于LLM的反思"""
        failure_summary = [
            {
                "intent": f["intent_type"],
                "input": f["raw_input"][:100],
                "model": f["model_name"],
                "quality": f["quality_score"]
            }
            for f in failures[:10]
        ]
        
        prompt = f"""分析以下失败案例,总结模式并提出改进规则。

失败案例:
{json.dumps(failure_summary, indent=2, ensure_ascii=False)}

请输出JSON数组,每个元素包含:
- condition: 触发条件(如 "intent_type == 'code' and quality < 30")
- action: 建议动作(如 "reroute:qwen2.5-coder:1.5b" 或 "ask_user:请安装代码模型")
- priority: 优先级(1-5)

只输出JSON,不要解释。"""

        response = llm.generate(prompt, task_type="reflection")
        
        if isinstance(response, tuple):
            response = response[0]
        
        json_str = self._extract_json(response)
        
        if json_str:
            return json.loads(json_str)
        
        return []
    
    def _rule_based_reflection(self, failures: List[Dict]) -> List[Dict]:
        """基于规则的反思(兜底)"""
        rules = []
        
        failure_patterns = {}
        for f in failures:
            key = f"{f['intent_type']}_{f['model_name']}"
            if key not in failure_patterns:
                failure_patterns[key] = []
            failure_patterns[key].append(f)
        
        for pattern_key, pattern_failures in failure_patterns.items():
            if len(pattern_failures) >= 2:
                intent_type, model_name = pattern_key.rsplit('_', 1)
                
                if intent_type == "code":
                    rules.append({
                        "condition": f"intent_type == 'code' and model == '{model_name}'",
                        "action": "reroute:qwen2.5-coder:1.5b",
                        "priority": 4
                    })
                
                else:
                    rules.append({
                        "condition": f"intent_type == '{intent_type}' and quality < 30",
                        "action": f"avoid_model:{model_name}",
                        "priority": 3
                    })
        
        logger.info(f"规则引擎生成{len(rules)}条规则")
        return rules
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON"""
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                return json_str.strip()
            
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0]
                return json_str.strip()
            
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                return json_match.group(0)
            
            return None
        
        except Exception as e:
            logger.error(f"JSON提取失败: {e}")
            return None
    
    def _save_rules(self, rules: List[Dict]):
        """保存规则到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            for rule in rules:
                conn.execute('''
                    INSERT INTO learning_rules 
                    (condition, action, priority, created_at, status, confidence)
                    VALUES (?, ?, ?, ?, 'pending', 0.5)
                ''', (
                    rule.get("condition"),
                    rule.get("action"),
                    rule.get("priority", 3),
                    datetime.now().isoformat()
                ))
        
        logger.info(f"保存{len(rules)}条反思规则")
    
    def get_active_rules(self) -> List[LearningRule]:
        """获取活跃规则"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute('''
                SELECT * FROM learning_rules
                WHERE status = 'active'
                ORDER BY priority DESC, confidence DESC
            ''')
            
            return [LearningRule(**dict(row)) for row in cur.fetchall()]
    
    def apply_rule(self, rule_id: int, success: bool):
        """应用规则后更新统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE learning_rules
                SET apply_count = apply_count + 1,
                    success_count = success_count + ?,
                    last_applied = ?,
                    confidence = CAST(success_count + ? AS REAL) / (apply_count + 1)
                WHERE id = ?
            ''', (1 if success else 0, datetime.now().isoformat(), 1 if success else 0, rule_id))
    
    def cleanup_rules(self, days: int = 30, min_confidence: float = 0.3):
        """清理过期规则"""
        threshold = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE learning_rules
                SET status = 'expired'
                WHERE last_applied < ? AND confidence < ?
            ''', (threshold.isoformat(), min_confidence))
            
            conn.execute('''
                DELETE FROM learning_rules
                WHERE status = 'expired' AND apply_count = 0
            ''')
        
        logger.info(f"清理过期规则(>{days}天,置信度<{min_confidence})")
    
    def activate_pending_rules(self, min_observations: int = 3):
        """激活观察期规则"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE learning_rules
                SET status = 'active'
                WHERE status = 'pending' AND apply_count >= ?
            ''', (min_observations,))
        
        logger.info(f"激活观察期规则(>={min_observations}次观察)")
    
    def get_rules_summary(self) -> Dict:
        """获取规则统计摘要"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('SELECT COUNT(*) FROM learning_rules')
            total = cur.fetchone()[0]
            
            cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status = 'active'")
            active = cur.fetchone()[0]
            
            cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status = 'pending'")
            pending = cur.fetchone()[0]
            
            cur = conn.execute("SELECT AVG(confidence) FROM learning_rules WHERE status = 'active'")
            avg_conf = cur.fetchone()[0] or 0
        
        return {
            "total_rules": total,
            "active_rules": active,
            "pending_rules": pending,
            "avg_confidence": avg_conf
        }


self_reflector = SelfReflector({})