"""
自我反思器 - 分析失败案例,生成改进规则
实现失败模式识别、规则生成、生命周期管理
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


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
        self.db_path = config.get("learning_rules.db_path", "data/learning_rules.db")
        self._init_db()
        
        logger.info("自我反思器初始化完成")
    
    def _init_db(self):
        """初始化规则数据库"""
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
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
            );
            CREATE INDEX IF NOT EXISTS idx_status ON learning_rules(status);
            CREATE INDEX IF NOT EXISTS idx_priority ON learning_rules(priority);
        ''')
    
    PERSPECTIVES = [
        {"name": "failure_analyst", "focus": "根因分析：为什么失败？模式是什么？"},
        {"name": "devils_advocate", "focus": "反向审视：失败是否可能是正确选择但时机不对？是否有被忽略的成功信号？"},
        {"name": "alternative_path", "focus": "替代路径：如果当时选择不同模型/路由，结果会怎样？"},
        {"name": "system_health", "focus": "系统健康：失败是否反映了更深层问题（资源不足/模型退化/配置过时）？"},
    ]

    def reflect_on_failures(self, limit: int = 20) -> List[Dict]:
        """分析最近的失败案例,生成改进规则 — 通过治理器频率控制"""
        
        try:
            from meta.governor import meta_governor
            approval = meta_governor.approve_adjustment(
                "self_reflector", {"reflect": 1.0}
            )
            if not approval["approved"]:
                logger.debug(f"反思被治理器节流: {approval['reason']}")
                return []
        except Exception:
            pass
        
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
            counterfactuals = self._counterfactual_reflection(failures, light_llm)
            rules.extend(counterfactuals)
            
            if rules:
                self._save_rules(rules)
                
                bus.publish("reflection_completed", {
                    "failure_count": len(failures),
                    "rules_generated": len(rules),
                    "perspectives_used": [p["name"] for p in self.PERSPECTIVES],
                    "timestamp": datetime.now().isoformat()
                })
            
            return rules
        
        except Exception as e:
            logger.error(f"LLM反思失败: {e},使用规则引擎")
            return self._rule_based_reflection(failures)
    
    def _get_recent_failures(self, limit: int) -> List[Dict]:
        """获取最近的失败案例"""
        exp_db = config.get("stats.db_path", "data/experience_pool.db")
        
        try:
            db = DatabaseManager.get(exp_db)
            rows = db.query('''
                SELECT intent_type, raw_input, model_name, quality_score, 
                       user_feedback, duration, timestamp
                FROM experiences
                WHERE quality_score < 30 OR success = 0
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in rows]
        
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
        """基于LLM的多视角反思"""
        failure_summary = [
            {
                "intent": f["intent_type"],
                "input": f["raw_input"][:100],
                "model": f["model_name"],
                "quality": f["quality_score"]
            }
            for f in failures[:10]
        ]
        
        perspective_prompts = []
        for p in self.PERSPECTIVES:
            perspective_prompts.append(f"视角【{p['name']}】: {p['focus']}")
        perspectives_text = "\n".join(perspective_prompts)

        prompt = f"""从多个视角分析以下失败案例,每个视角独立提出改进规则。

失败案例:
{json.dumps(failure_summary, indent=2, ensure_ascii=False)}

分析视角:
{perspectives_text}

请输出JSON数组,每个元素包含:
- condition: 触发条件(如 "intent_type == 'code' and quality < 30")
- action: 建议动作(如 "reroute:qwen2.5-coder:1.5b" 或 "ask_user:请安装代码模型")
- priority: 优先级(1-5)
- perspective: 来源视角名称
- confidence: 置信度(0.0-1.0)

只输出JSON,不要解释。"""

        response = llm.generate(prompt, task_type="reflection")
        
        if isinstance(response, tuple):
            response = response[0]
        
        json_str = self._extract_json(response)
        
        if json_str:
            return json.loads(json_str)
        
        return []
    
    def _rule_based_reflection(self, failures: List[Dict]) -> List[Dict]:
        """基于规则的反思(兜底) — 含多视角"""
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
                        "priority": 4,
                        "perspective": "failure_analyst",
                        "confidence": 0.7,
                    })
                
                else:
                    rules.append({
                        "condition": f"intent_type == '{intent_type}' and quality < 30",
                        "action": f"avoid_model:{model_name}",
                        "priority": 3,
                        "perspective": "failure_analyst",
                        "confidence": 0.6,
                    })

        for pattern_key, pattern_failures in failure_patterns.items():
            if len(pattern_failures) >= 1:
                intent_type, model_name = pattern_key.rsplit('_', 1)
                avg_quality = sum(f.get("quality_score", 0) for f in pattern_failures) / len(pattern_failures)
                if 20 < avg_quality < 40:
                    rules.append({
                        "condition": f"intent_type == '{intent_type}' and model == '{model_name}' and 20 < quality < 40",
                        "action": f"retry_with_context:{intent_type}",
                        "priority": 2,
                        "perspective": "devils_advocate",
                        "confidence": 0.4,
                    })

        for pattern_key, pattern_failures in failure_patterns.items():
            if len(pattern_failures) >= 1:
                intent_type, model_name = pattern_key.rsplit('_', 1)
                rules.append({
                    "condition": f"intent_type == '{intent_type}' and model == '{model_name}'",
                    "action": f"try_alternative_model:{intent_type}",
                    "priority": 2,
                    "perspective": "alternative_path",
                    "confidence": 0.5,
                })

        durations = [f.get("duration", 0) for f in failures if f.get("duration")]
        if durations and sum(durations) / len(durations) > 15:
            rules.append({
                "condition": "duration > 15",
                "action": "check_system_resources",
                "priority": 3,
                "perspective": "system_health",
                "confidence": 0.5,
            })
        
        logger.info(f"规则引擎生成{len(rules)}条规则(含多视角)")
        return rules
    
    def _counterfactual_reflection(self, failures: List[Dict], llm) -> List[Dict]:
        """反事实推理：如果当时做了不同选择会怎样？"""
        if not failures:
            return []
        
        sample = failures[:5]
        scenarios = []
        for f in sample:
            scenarios.append({
                "actual": f"意图={f['intent_type']}, 模型={f['model_name']}, 质量={f['quality_score']}",
                "counterfactual_1": f"如果使用不同模型会怎样？",
                "counterfactual_2": f"如果用户提供更多上下文会怎样？",
                "counterfactual_3": f"如果系统处于不同状态（低负载/高负载）会怎样？",
            })
        
        prompt = f"""对以下失败案例进行反事实推理：如果当时做了不同选择，结果会如何变化？

案例:
{json.dumps(scenarios, indent=2, ensure_ascii=False)}

请输出JSON数组,每个元素包含:
- condition: 触发条件(基于反事实假设)
- action: 预防性动作(避免类似失败)
- priority: 优先级(1-5)
- perspective: "counterfactual"
- confidence: 置信度(0.0-1.0,反事实推理通常较低)

只输出JSON,不要解释。"""

        try:
            response = llm.generate(prompt, task_type="reflection")
            if isinstance(response, tuple):
                response = response[0]
            json_str = self._extract_json(response)
            if json_str:
                rules = json.loads(json_str)
                for r in rules:
                    r.setdefault("perspective", "counterfactual")
                    r.setdefault("confidence", 0.3)
                return rules
        except Exception as e:
            logger.warning(f"反事实推理失败: {e}")
        
        return []
    
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
        db = DatabaseManager.get(self.db_path)
        db.executemany('''
            INSERT INTO learning_rules 
            (condition, action, priority, created_at, status, confidence, source, metadata)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
        ''', [(
            rule.get("condition"),
            rule.get("action"),
            rule.get("priority", 3),
            datetime.now().isoformat(),
            rule.get("confidence", 0.5),
            rule.get("perspective", "reflection"),
            json.dumps({"perspective": rule.get("perspective", "unknown")}, ensure_ascii=False),
        ) for rule in rules], commit=True)
        
        logger.info(f"保存{len(rules)}条反思规则(含视角标记)")
    
    def get_active_rules(self) -> List[LearningRule]:
        """获取活跃规则"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT id as rule_id, condition, action, priority, created_at, status,
                   last_applied, apply_count, success_count, confidence
            FROM learning_rules
            WHERE status = 'active'
            ORDER BY priority DESC, confidence DESC
        ''')
        
        return [LearningRule(**dict(row)) for row in rows]
    
    def apply_rule(self, rule_id: int, success: bool):
        """应用规则后更新统计"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE learning_rules
            SET apply_count = apply_count + 1,
                success_count = success_count + ?,
                last_applied = ?,
                confidence = CAST(success_count + ? AS REAL) / (apply_count + 1)
            WHERE id = ?
        ''', (1 if success else 0, datetime.now().isoformat(), 1 if success else 0, rule_id), commit=True)
    
    def cleanup_rules(self, days: int = 30, min_confidence: float = 0.3):
        """清理过期规则"""
        threshold = datetime.now() - timedelta(days=days)
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE learning_rules
            SET status = 'expired'
            WHERE last_applied < ? AND confidence < ?
        ''', (threshold.isoformat(), min_confidence))
        
        db.execute('''
            DELETE FROM learning_rules
            WHERE status = 'expired' AND apply_count = 0
        ''', commit=True)
        
        logger.info(f"清理过期规则(>{days}天,置信度<{min_confidence})")
    
    def activate_pending_rules(self, min_observations: int = 3):
        """激活观察期规则"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE learning_rules
            SET status = 'active'
            WHERE status = 'pending' AND apply_count >= ?
        ''', (min_observations,), commit=True)
        
        logger.info(f"激活观察期规则(>={min_observations}次观察)")
    
    def get_rules_summary(self) -> Dict:
        """获取规则统计摘要"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('SELECT COUNT(*) FROM learning_rules')
        total = row[0]
        
        row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status = 'active'")
        active = row[0]
        
        row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status = 'pending'")
        pending = row[0]
        
        row = db.query_one("SELECT AVG(confidence) FROM learning_rules WHERE status = 'active'")
        avg_conf = row[0] or 0
        
        return {
            "total_rules": total,
            "active_rules": active,
            "pending_rules": pending,
            "avg_confidence": avg_conf
        }


self_reflector = SelfReflector({})
