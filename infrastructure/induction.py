"""
离线归纳总结器 - 从经验池挖掘通用规则
支持LLM归纳和规则引擎降级
"""
import json
import sqlite3
import re
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from infrastructure.experience_pool import ExperiencePool


class InductionEngine:
    """离线归纳总结器"""
    
    def __init__(self, pool: ExperiencePool, llm_adapter=None):
        self.pool = pool
        self.llm = llm_adapter
        self.db_path = "learning_rules.db"
        
        logger.info("归纳总结器初始化完成")
    
    def induce_rules(self, intent_type: str = None, 
                    min_quality: int = 70, 
                    limit: int = 50) -> List[Dict]:
        """从高质量经验中归纳规则"""
        
        good_exps = self._get_high_quality_experiences(
            intent_type=intent_type,
            min_quality=min_quality,
            limit=limit
        )
        
        if not good_exps:
            logger.info("没有足够的高质量经验,跳过归纳")
            return []
        
        bad_exps = self._get_failed_experiences(
            intent_type=intent_type,
            limit=limit // 2
        )
        
        logger.info(f"归纳分析: 成功{len(good_exps)}条, 失败{len(bad_exps)}条")
        
        if self.llm:
            rules = self._llm_induction(good_exps, bad_exps)
        else:
            rules = self._rule_based_induction(good_exps, bad_exps)
        
        saved = []
        for rule in rules:
            rule_id = self._save_rule(rule)
            if rule_id:
                saved.append({**rule, "id": rule_id})
        
        logger.info(f"归纳生成 {len(saved)} 条规则")
        return saved
    
    def _get_high_quality_experiences(self, intent_type: str = None,
                                      min_quality: int = 70,
                                      limit: int = 50) -> List[Dict]:
        """获取高质量成功经验"""
        try:
            db_path = "experience_pool.db"
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if intent_type:
                    cur = conn.execute('''
                        SELECT intent_type, raw_input, plan, model_name, 
                               quality_score, success, user_feedback
                        FROM experiences
                        WHERE quality_score >= ? AND intent_type = ? AND success = 1
                        ORDER BY quality_score DESC
                        LIMIT ?
                    ''', (min_quality, intent_type, limit))
                else:
                    cur = conn.execute('''
                        SELECT intent_type, raw_input, plan, model_name,
                               quality_score, success, user_feedback
                        FROM experiences
                        WHERE quality_score >= ? AND success = 1
                        ORDER BY quality_score DESC
                        LIMIT ?
                    ''', (min_quality, limit))
                
                return [dict(row) for row in cur.fetchall()]
        
        except Exception as e:
            logger.error(f"获取高质量经验失败: {e}")
            return []
    
    def _get_failed_experiences(self, intent_type: str = None,
                               limit: int = 25) -> List[Dict]:
        """获取失败经验"""
        try:
            db_path = "experience_pool.db"
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if intent_type:
                    cur = conn.execute('''
                        SELECT intent_type, raw_input, plan, model_name,
                               quality_score, success, user_feedback
                        FROM experiences
                        WHERE quality_score < 50 AND intent_type = ? AND success = 0
                        ORDER BY quality_score ASC
                        LIMIT ?
                    ''', (intent_type, limit))
                else:
                    cur = conn.execute('''
                        SELECT intent_type, raw_input, plan, model_name,
                               quality_score, success, user_feedback
                        FROM experiences
                        WHERE quality_score < 50 AND success = 0
                        ORDER BY quality_score ASC
                        LIMIT ?
                    ''', (limit,))
                
                return [dict(row) for row in cur.fetchall()]
        
        except Exception as e:
            logger.error(f"获取失败经验失败: {e}")
            return []
    
    def _llm_induction(self, good_exps: List[Dict], bad_exps: List[Dict]) -> List[Dict]:
        """使用LLM分析并生成规则"""
        prompt = self._build_induction_prompt(good_exps, bad_exps)
        
        try:
            response = self.llm.generate(prompt, task_type="induction")
            
            json_match = re.search(r'\[[\s\S]*\]', response)
            
            if json_match:
                rules = json.loads(json_match.group())
                
                validated = []
                for r in rules:
                    if "condition" in r and "action" in r:
                        validated.append({
                            "condition": r["condition"],
                            "action": r["action"],
                            "priority": r.get("priority", 3),
                            "confidence": r.get("confidence", 0.6),
                            "source": "induction",
                            "metadata": json.dumps({"generated_by": "llm"})
                        })
                
                return validated
            else:
                logger.warning("LLM返回未包含JSON,使用规则引擎降级")
                return self._rule_based_induction(good_exps, bad_exps)
        
        except Exception as e:
            logger.error(f"LLM归纳失败: {e},降级到规则引擎")
            return self._rule_based_induction(good_exps, bad_exps)
    
    def _build_induction_prompt(self, good_exps: List[Dict], bad_exps: List[Dict]) -> str:
        """构建归纳提示词"""
        good_summary = "\n".join([
            f"- 输入: {e['raw_input'][:100]}, 模型: {e['model_name']}, 质量: {e['quality_score']}"
            for e in good_exps[:10]
        ])
        
        bad_summary = "\n".join([
            f"- 输入: {e['raw_input'][:100]}, 模型: {e['model_name']}, 质量: {e['quality_score']}"
            for e in bad_exps[:5]
        ])
        
        prompt = f"""你是一个智能系统的规则归纳器。请分析以下成功和失败案例,生成通用的if-then规则。

成功案例(质量≥70):
{good_summary}

失败案例(质量<50且无正面反馈):
{bad_summary}

请输出JSON数组,每个元素包含:
- condition: 触发条件(自然语言,例如 "intent_type == 'code' and quality < 30")
- action: 建议动作(例如 "reroute:qwen2.5-coder:1.5b" 或 "ask_user:请提供代码模型")
- priority: 优先级(1-5,1最高)
- confidence: 置信度(0-1)

只输出JSON,不要其他解释。"""
        
        return prompt
    
    def _rule_based_induction(self, good_exps: List[Dict], bad_exps: List[Dict]) -> List[Dict]:
        """基于规则的简单归纳(备用)"""
        rules = []
        
        for exp in bad_exps:
            if "code" in exp.get("intent_type", "") and "mindchat" in exp.get("model_name", ""):
                rules.append({
                    "condition": "intent_type == 'code' and model_name == 'mindchat'",
                    "action": "reroute:qwen2.5-coder:1.5b",
                    "priority": 1,
                    "confidence": 0.7,
                    "source": "induction_rule",
                    "metadata": "{}"
                })
                break
        
        for exp in good_exps:
            if "calculation" in exp.get("intent_type", "") and "remote_gpt4" in exp.get("model_name", ""):
                rules.append({
                    "condition": "intent_type == 'calculation'",
                    "action": "prefer_model:remote_gpt4",
                    "priority": 2,
                    "confidence": 0.8,
                    "source": "induction_rule",
                    "metadata": "{}"
                })
                break
        
        return rules
    
    def _save_rule(self, rule: Dict) -> Optional[int]:
        """保存规则到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute('''
                    INSERT INTO learning_rules
                    (condition, action, priority, confidence, status, source, created_at, metadata)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
                ''', (
                    rule["condition"],
                    rule["action"],
                    rule.get("priority", 3),
                    rule.get("confidence", 0.5),
                    rule.get("source", "induction"),
                    datetime.now().isoformat(),
                    rule.get("metadata", "{}")
                ))
                
                rule_id = cur.lastrowid
                conn.commit()
                
                logger.debug(f"规则已保存, ID: {rule_id}, 条件: {rule['condition'][:50]}")
                return rule_id
        
        except Exception as e:
            logger.error(f"保存规则失败: {e}")
            return None
