"""
在线反思器 - 实时分析失败并生成规则
不等待离线归纳，立即响应低质量结果
"""
import time
import threading
import json
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class OnlineReflector:
    """在线反思器"""
    
    ALLOWED_INTENTS = {
        'code', 'question', 'chat', 'memory', 
        'calculation', 'feedback', 'meta', 'document',
        'translation', 'analysis', 'creative', 'planning'
    }
    
    def __init__(self):
        self.quality_threshold = 40
        self.cooldown_seconds = 600
        self.last_reflection_time = 0
        self.reflection_count = 0
        self._lock = threading.Lock()
        
        logger.info("在线反思器已初始化")
    
    def should_reflect(self, quality_score: float) -> bool:
        """判断是否需要反思"""
        # 质量分低于阈值
        if quality_score >= self.quality_threshold:
            return False
        
        # 冷却时间检查
        elapsed = time.time() - self.last_reflection_time
        if elapsed < self.cooldown_seconds:
            logger.warning(f"反思冷却中，还需等待 {self.cooldown_seconds - elapsed:.0f}秒")
            return False
        
        return True
    
    def reflect(self, 
                intent_type: str,
                raw_input: str,
                model_name: str,
                quality_score: float,
                response: str,
                error: Optional[str] = None) -> Optional[Dict]:
        """
        在线反思并生成规则
        
        Args:
            intent_type: 意图类型
            raw_input: 原始输入
            model_name: 使用的模型
            quality_score: 质量分
            response: 响应内容
            error: 错误信息
        
        Returns:
            生成的规则（如果有）
        """
        if intent_type not in self.ALLOWED_INTENTS:
            logger.warning(f"无效的intent_type: {intent_type}")
            return None
        
        if not self.should_reflect(quality_score):
            return None
        
        try:
            logger.info(f"触发在线反思: {intent_type}, 质量={quality_score}, 模型={model_name}")
            
            failure_analysis = self._analyze_failure(
                intent_type, raw_input, model_name, quality_score, response, error
            )
            
            rule = self._generate_rule_from_analysis(failure_analysis)
            
            if rule:
                self._save_rule(rule)
                
                with self._lock:
                    self.last_reflection_time = time.time()
                    self.reflection_count += 1
                
                logger.info(f"在线反思完成，生成规则: {rule['condition'][:50]}...")
                
                return rule
            
            return None
            
        except Exception as e:
            logger.warning(f"在线反思失败: {e}")
            return None
    
    def _analyze_failure(self, 
                        intent_type: str,
                        raw_input: str,
                        model_name: str,
                        quality_score: float,
                        response: str,
                        error: Optional[str]) -> Dict:
        """分析失败原因"""
        analysis = {
            "intent_type": intent_type,
            "model_name": model_name,
            "quality_score": quality_score,
            "timestamp": datetime.now().isoformat(),
            "failure_type": None,
            "suggested_action": None,
            "reason": None
        }
        
        # 判断失败类型
        if error:
            if "timeout" in error.lower():
                analysis["failure_type"] = "timeout"
                analysis["reason"] = "模型响应超时"
                analysis["suggested_action"] = "avoid_model"
            elif "connection" in error.lower():
                analysis["failure_type"] = "connection_error"
                analysis["reason"] = "连接失败"
                analysis["suggested_action"] = "avoid_model"
            else:
                analysis["failure_type"] = "execution_error"
                analysis["reason"] = f"执行错误: {error[:50]}"
                analysis["suggested_action"] = "reroute"
        else:
            # 基于响应质量分析
            if not response or len(response) < 10:
                analysis["failure_type"] = "empty_response"
                analysis["reason"] = "响应为空或过短"
                analysis["suggested_action"] = "avoid_model"
            elif "错误" in response or "error" in response.lower():
                analysis["failure_type"] = "error_in_response"
                analysis["reason"] = "响应包含错误信息"
                analysis["suggested_action"] = "reroute"
            else:
                analysis["failure_type"] = "low_quality"
                analysis["reason"] = f"质量分过低: {quality_score}"
                analysis["suggested_action"] = "prefer_other_model"
        
        return analysis
    
    def _generate_rule_from_analysis(self, analysis: Dict) -> Optional[Dict]:
        """从分析结果生成规则"""
        intent_type = analysis["intent_type"]
        model_name = analysis["model_name"]
        action_type = analysis["suggested_action"]
        
        if not action_type:
            return None
        
        condition_data = json.dumps({
            "type": "intent_equals",
            "intent_type": intent_type
        }, ensure_ascii=False)
        
        if action_type == "avoid_model":
            action = f"avoid_model:{model_name}"
            confidence = 0.7
        elif action_type == "prefer_other_model":
            better_model = self._find_better_model(intent_type, model_name)
            if better_model:
                action = f"prefer_model:{better_model}"
                confidence = 0.6
            else:
                action = f"avoid_model:{model_name}"
                confidence = 0.5
        elif action_type == "reroute":
            action = f"avoid_model:{model_name}"
            confidence = 0.65
        else:
            return None
        
        rule = {
            "condition": condition_data,
            "action": action,
            "confidence": confidence,
            "source": "online_reflection",
            "priority": 7,
            "reason": analysis["reason"],
            "created_at": analysis["timestamp"]
        }
        
        return rule
    
    def _find_better_model(self, intent_type: str, current_model: str) -> Optional[str]:
        """查找更好的模型"""
        try:
            db = DatabaseManager.get("data/model_stats.db")
            rows = db.query('''
                SELECT model_name, AVG(quality)
                FROM model_calls
                WHERE intent_type = ?
                GROUP BY model_name
                ORDER BY AVG(quality) DESC
                LIMIT 3
            ''', (intent_type,))
            
            for row in rows:
                if row[0] != current_model:
                    return row[0]
            
            return None
            
        except Exception as e:
            logger.error(f"查找更好模型失败: {e}")
            return None
    
    def _save_rule(self, rule: Dict):
        """保存规则到数据库"""
        db = DatabaseManager.get("data/learning_rules.db")
        db.execute('''
            INSERT INTO learning_rules
            (condition, action, confidence, status, source, priority, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?)
        ''', (
            rule["condition"],
            rule["action"],
            rule["confidence"],
            rule["source"],
            rule["priority"],
            rule["created_at"]
        ), commit=True)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            last_time = self.last_reflection_time
            count = self.reflection_count
        
        return {
            "reflection_count": count,
            "last_reflection": datetime.fromtimestamp(last_time).isoformat() if last_time > 0 else None,
            "cooldown_remaining": max(0, self.cooldown_seconds - (time.time() - last_time))
        }


online_reflector = OnlineReflector()
