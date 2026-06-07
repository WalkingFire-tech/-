"""
自我修正规划器 - 失败时主动学习
实现真正的自我完善能力
"""
from core.ports.llm_port import LLMPort
from core.services.intent_parser import Intent
from infrastructure.event_bus import bus
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from infrastructure.experience_pool import ExperiencePool
from infrastructure.self_audit import SelfAudit
from infrastructure.config_manager import config
from loguru import logger
import sqlite3
import time
import json
from pathlib import Path
from typing import Dict, Optional, List


class PlanCorrection:
    """计划修正记录"""
    def __init__(self, intent_type: str, failed_plan: str, correct_approach: str, context: str):
        self.intent_type = intent_type
        self.failed_plan = failed_plan
        self.correct_approach = correct_approach
        self.context = context


class SelfCorrectingPlanner:
    """自我修正的规划器"""
    
    def __init__(self, adapters: dict):
        self.adapters = adapters
        self.logger = CampfireLogger()
        self.stats = ModelStats()
        self.experience_pool = ExperiencePool()
        self.last_call_info = {
            "model": None,
            "task_type": None,
            "plan": None,
            "duration": 0.0,
            "quality": 0
        }
        
        # 自我修正相关
        self.correction_db_path = Path("plan_corrections.db")
        self._init_correction_db()
        self.quality_threshold = config.get("planner.quality_threshold", 50)
        self.auto_learn_enabled = config.get("planner.auto_learn", True)
        self.correction_count = 0
    
    def _init_correction_db(self):
        """初始化修正数据库"""
        with sqlite3.connect(self.correction_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plan_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_type TEXT,
                    failed_plan TEXT,
                    failed_model TEXT,
                    correct_approach TEXT,
                    context TEXT,
                    timestamp TEXT,
                    applied_count INTEGER DEFAULT 0
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_intent ON plan_corrections(intent_type)')
    
    def get_last_call_info(self):
        return self.last_call_info
    
    def _get_recent_context(self, rounds: int = None) -> str:
        """获取最近对话上下文"""
        if rounds is None:
            rounds = config.get("memory.short_term.max_rounds", 3)
        
        file_path = config.get("memory.short_term.file_path", "campfire_log.txt")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return ""
        
        history = []
        for line in lines:
            line = line.strip()
            if line.startswith("[") and ("user:" in line.lower() or "拓荒者:" in line):
                content = line.split("] ", 1)[-1]
                history.append(content)
        
        recent = history[-rounds*2:] if len(history) >= rounds*2 else history
        if not recent:
            return ""
        
        context = "Recent conversation history:\n"
        for entry in recent:
            context += entry + "\n"
        context += "\nCurrent question: "
        return context
    
    def _has_failed_before(self, intent: Intent) -> bool:
        """检查是否有历史失败记录"""
        with sqlite3.connect(self.correction_db_path) as conn:
            cur = conn.execute(
                'SELECT COUNT(*) FROM plan_corrections WHERE intent_type = ?',
                (intent.type,)
            )
            count = cur.fetchone()[0]
            return count > 0
    
    def _get_corrected_plan(self, intent: Intent) -> Optional[Dict]:
        """获取修正后的计划"""
        with sqlite3.connect(self.correction_db_path) as conn:
            cur = conn.execute(
                '''SELECT correct_approach, context FROM plan_corrections 
                   WHERE intent_type = ? 
                   ORDER BY timestamp DESC LIMIT 1''',
                (intent.type,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "approach": row[0],
                    "context": row[1]
                }
        return None
    
    def _select_model(self, intent: Intent):
        """选择模型(数据驱动)"""
        # 优先从统计库获取最佳模型
        best_model_name = self.stats.get_best_model_for_task(intent.type)
        
        if best_model_name and best_model_name in self.adapters:
            logger.info(f"统计库推荐模型: {best_model_name}")
            return self.adapters[best_model_name]
        
        # 降级:使用配置的路由策略
        routing_config = config.get_routing_config(intent.type)
        for model_key in routing_config.preferred:
            if model_key in self.adapters:
                return self.adapters[model_key]
        
        # 最终降级
        if self.adapters:
            return next(iter(self.adapters.values()))
        
        raise RuntimeError("No model available")
    
    def _build_prompt(self, intent: Intent, correction: Optional[Dict] = None) -> str:
        """构建提示词"""
        if correction:
            # 使用修正后的方法
            return f"{correction['context']}\n用户请求: {intent.raw_text}\n建议方法: {correction['approach']}"
        
        if intent.type == "code":
            return f"Output code only, no extra explanation. User request: {intent.raw_text}"
        elif intent.type == "question":
            return f"Answer the following question in detail: {intent.raw_text}"
        elif intent.type == "memory":
            return f"Based on the conversation history, answer the user's question. If history does not contain info, say you don't know. Question: {intent.raw_text}"
        else:
            return intent.raw_text
    
    def plan(self, intent: Intent):
        """执行任务规划(带自我修正)"""
        context = self._get_recent_context()
        
        # 检查是否有历史修正
        correction = None
        if self._has_failed_before(intent):
            correction = self._get_corrected_plan(intent)
            if correction:
                logger.info(f"使用修正后的策略处理: {intent.type}")
        
        base_prompt = self._build_prompt(intent, correction)
        full_prompt = f"{context}\n{base_prompt}" if context else base_prompt
        
        model = self._select_model(intent)
        self.last_call_info = {
            "model": model.model_name,
            "task_type": intent.type,
            "plan": base_prompt,
            "duration": 0,
            "quality": 0
        }
        
        logger.info(f"Planner using model: {model.model_name} for intent: {intent.type}")
        
        try:
            start = time.time()
            response = model.generate(full_prompt, task_type=intent.type)
            duration = time.time() - start
            self.last_call_info["duration"] = duration
            
            # 安全审核
            audit = SelfAudit.audit(response, intent.type)
            if audit["blocked"]:
                logger.warning(f"Audit blocked: {audit['reason']}")
                response = f"⚠️ 系统检测到危险操作,已拦截。原因: {audit['reason']}"
            
            # 获取质量分
            conn = sqlite3.connect(config.get("stats.db_path", "model_stats.db"))
            cur = conn.execute("SELECT quality_score FROM model_performance ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            quality = row[0] if row else 0
            conn.close()
            self.last_call_info["quality"] = quality
            
            # 记录经验
            self.experience_pool.add_experience(
                intent_type=intent.type,
                raw_input=intent.raw_text,
                plan=base_prompt,
                model_name=model.model_name,
                quality_score=quality,
                user_feedback=0,
                success=quality >= self.quality_threshold,
                duration=duration
            )
            
            # 自我修正检查
            if quality < self.quality_threshold and self.auto_learn_enabled:
                self._handle_low_quality(intent, response, quality, model.model_name)
            
            bus.publish("plan_executed", response)
            
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            
            # 记录失败
            self._record_failure(intent, str(e), model.model_name)
            
            # 尝试降级处理
            fallback_response = self._try_fallback(intent, e)
            bus.publish("plan_executed", fallback_response)
    
    def _handle_low_quality(self, intent: Intent, response: str, quality: int, model_name: str):
        """处理低质量结果"""
        logger.warning(f"低质量结果: {quality} < {self.quality_threshold}")
        
        # 记录潜在问题
        self._record_potential_issue(intent, response, quality, model_name)
        
        # 如果质量极低,主动询问用户
        if quality < 30:
            self._ask_user_for_correction(intent, response)
    
    def _record_potential_issue(self, intent: Intent, response: str, quality: int, model_name: str):
        """记录潜在问题"""
        issue_record = {
            "intent_type": intent.type,
            "raw_text": intent.raw_text[:100],
            "response": response[:200],
            "quality": quality,
            "model": model_name,
            "timestamp": time.time()
        }
        
        # 可以存储到文件或数据库
        issue_file = Path("plan_issues.json")
        issues = []
        if issue_file.exists():
            try:
                with open(issue_file, 'r', encoding='utf-8') as f:
                    issues = json.load(f)
            except:
                pass
        
        issues.append(issue_record)
        
        # 只保留最近100个问题
        issues = issues[-100:]
        
        with open(issue_file, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)
    
    def _ask_user_for_correction(self, intent: Intent, failed_response: str):
        """询问用户正确做法(异步,不阻塞)"""
        # 这里只是记录,实际询问在UI层实现
        correction_request = {
            "type": "correction_request",
            "intent": intent.type,
            "question": intent.raw_text,
            "failed_response": failed_response[:200],
            "message": f"上次的回答质量不够好。您希望如何处理这类'{intent.type}'任务?"
        }
        
        # 发布事件,由UI层处理
        bus.publish("correction_needed", correction_request)
        
        logger.info(f"已发起修正请求: {intent.type}")
    
    def learn_from_user_correction(self, intent: Intent, correct_approach: str, failed_plan: str = None):
        """从用户修正中学习"""
        logger.info(f"学习用户修正: {intent.type} -> {correct_approach}")
        
        # 保存修正
        with sqlite3.connect(self.correction_db_path) as conn:
            conn.execute('''
                INSERT INTO plan_corrections 
                (intent_type, failed_plan, failed_model, correct_approach, context, timestamp)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (
                intent.type,
                failed_plan or self.last_call_info.get("plan", ""),
                self.last_call_info.get("model", ""),
                correct_approach,
                intent.raw_text
            ))
        
        self.correction_count += 1
        logger.info(f"已记录修正,总修正次数: {self.correction_count}")
        
        # 更新统计
        self._update_correction_stats(intent.type)
    
    def _record_failure(self, intent: Intent, error: str, model_name: str):
        """记录失败"""
        self.experience_pool.add_experience(
            intent_type=intent.type,
            raw_input=intent.raw_text,
            plan=self.last_call_info.get("plan", ""),
            model_name=model_name,
            quality_score=0,
            user_feedback=-1,  # 标记为失败
            success=False,
            duration=self.last_call_info.get("duration", 0)
        )
    
    def _try_fallback(self, intent: Intent, original_error: Exception) -> str:
        """尝试降级处理"""
        # 1. 尝试其他模型
        tried_models = [self.last_call_info.get("model")]
        
        for model_key, adapter in self.adapters.items():
            if adapter.model_name not in tried_models:
                try:
                    logger.info(f"尝试降级模型: {adapter.model_name}")
                    response = adapter.generate(intent.raw_text, task_type=intent.type)
                    return f"[降级处理] {response}"
                except Exception as e:
                    logger.warning(f"降级模型也失败: {e}")
                    tried_models.append(adapter.model_name)
        
        # 2. 返回友好错误
        return self._format_friendly_error(original_error)
    
    def _format_friendly_error(self, error: Exception) -> str:
        """格式化友好的错误消息"""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return "抱歉,处理超时。建议:\n1. 简化问题\n2. 稍后重试"
        elif "connection" in error_str:
            return "抱歉,服务连接失败。请检查:\n1. 网络连接\n2. 服务状态"
        elif "not found" in error_str:
            return "抱歉,找不到所需资源。请检查配置。"
        else:
            return f"抱歉,处理时遇到问题: {str(error)}"
    
    def _update_correction_stats(self, intent_type: str):
        """更新修正统计"""
        # 更新应用次数
        with sqlite3.connect(self.correction_db_path) as conn:
            conn.execute('''
                UPDATE plan_corrections 
                SET applied_count = applied_count + 1
                WHERE intent_type = ?
            ''', (intent_type,))
    
    def get_correction_statistics(self) -> Dict:
        """获取修正统计"""
        with sqlite3.connect(self.correction_db_path) as conn:
            cur = conn.execute('SELECT COUNT(*) FROM plan_corrections')
            total = cur.fetchone()[0]
            
            cur = conn.execute('''
                SELECT intent_type, COUNT(*) as count
                FROM plan_corrections
                GROUP BY intent_type
            ''')
            by_type = {row[0]: row[1] for row in cur.fetchall()}
            
            cur = conn.execute('SELECT SUM(applied_count) FROM plan_corrections')
            applied = cur.fetchone()[0] or 0
        
        return {
            "total_corrections": total,
            "by_intent_type": by_type,
            "total_applied": applied
        }