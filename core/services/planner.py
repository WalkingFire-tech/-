"""
数据驱动的规划器 - 完全由统计库决定路由
配置文件仅提供用户偏好和降级后备
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
from collections import deque
from typing import Optional, Dict, List

try:
    from meta.bayesian_optimizer import bayesian_optimizer
    BAYESIAN_AVAILABLE = True
except Exception as e:
    BAYESIAN_AVAILABLE = False
    logger.warning(f"贝叶斯优化器加载失败: {e}")

try:
    from infrastructure.vector_retriever import vector_retriever
    VECTOR_AVAILABLE = True
except Exception as e:
    VECTOR_AVAILABLE = False
    logger.debug(f"向量检索器加载失败: {e}")

try:
    from meta.induction import induction_scheduler
    from meta.conflict_detector import conflict_detector
    INDUCTION_AVAILABLE = True
except Exception as e:
    INDUCTION_AVAILABLE = False
    logger.warning(f"归纳总结器加载失败: {e}")

try:
    from tools.generator import ToolGenerator
    TOOL_GENERATOR_AVAILABLE = True
except Exception as e:
    TOOL_GENERATOR_AVAILABLE = False
    logger.warning(f"工具生成器加载失败: {e}")


class DataDrivenPlanner:
    """完全数据驱动的规划器"""
    
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
        self.context_buffer = deque(maxlen=100)
        self.last_call_id: Optional[int] = None
        
        self.failure_history: Dict[str, List[int]] = {}
        self.decomposer = None
        self.tool_generator = None
        self.optimization_enabled = config.get("optimization.enabled", True)
        self.induction_interval = config.get("optimization.induction_interval_hours", 24)
        self.last_induction_time = 0
        
        try:
            from core.services.problem_decomposer import problem_decomposer
            self.decomposer = problem_decomposer
        except Exception as e:
            logger.warning(f"问题拆解器加载失败: {e}")
        
        if BAYESIAN_AVAILABLE and self.optimization_enabled:
            self._setup_bayesian_optimization()
        
        if TOOL_GENERATOR_AVAILABLE:
            primary_model = next(iter(self.adapters.values())) if self.adapters else None
            self.tool_generator = ToolGenerator(llm_adapter=primary_model)
            logger.info("工具生成器已激活")
        
        if INDUCTION_AVAILABLE:
            logger.info("归纳总结器已就绪")
    
    def get_last_call_info(self):
        return self.last_call_info
    
    def _setup_bayesian_optimization(self):
        """设置贝叶斯优化目标函数"""
        def evaluate_params(params: Dict) -> float:
            quality_weight = params.get("quality_weight", 0.5)
            speed_weight = params.get("speed_weight", 0.3)
            cost_weight = params.get("cost_weight", 0.2)
            
            total_score = 0.0
            sample_size = 0
            
            for intent_type in ["code", "question", "document", "chat"]:
                weights = {
                    "quality": quality_weight,
                    "speed": speed_weight,
                    "cost": cost_weight,
                    "success": 0.1
                }
                
                best_model = self.stats.get_best_model_for_task(intent_type, weights)
                
                if best_model:
                    model_stats = self.stats.get_model_stats(best_model)
                    if model_stats:
                        avg_quality = model_stats.get("avg_quality", 50)
                        success_rate = model_stats.get("success_rate", 0.5)
                        score = avg_quality * 0.6 + success_rate * 100 * 0.4
                        total_score += score
                        sample_size += 1
            
            return total_score / max(sample_size, 1)
        
        bayesian_optimizer.define_objective_function(evaluate_params)
        logger.info("贝叶斯优化目标函数已设置")
    
    def run_optimization(self, n_iterations: int = 20, method: str = "bayesian") -> Dict:
        """运行参数优化"""
        if not BAYESIAN_AVAILABLE:
            return {"success": False, "message": "贝叶斯优化器未加载"}
        
        try:
            result = bayesian_optimizer.optimize(
                params_to_optimize=["quality_weight", "speed_weight", "cost_weight"],
                n_iterations=n_iterations,
                method=method
            )
            
            bayesian_optimizer.apply_best_params(result.best_params)
            bayesian_optimizer.save_optimization_result(result)
            
            return {
                "success": True,
                "best_params": result.best_params,
                "best_score": result.best_score,
                "iterations": result.iterations
            }
        
        except Exception as e:
            logger.error(f"优化失败: {e}")
            return {"success": False, "message": str(e)}
    
    def run_induction(self, days: int = 7) -> Dict:
        """运行归纳总结"""
        if not INDUCTION_AVAILABLE:
            return {"success": False, "message": "归纳总结器未加载"}
        
        try:
            result = induction_scheduler.run_induction(days)
            
            if result.get("success") and result.get("rules", 0) > 0:
                conflict_report = conflict_detector.get_conflict_report()
                result["conflicts"] = conflict_report["total_conflicts"]
                
                if conflict_report["total_conflicts"] > 0:
                    for conflict in conflict_report["conflicts"][:3]:
                        conflict_detector.resolve_conflict(conflict, resolution="auto")
                    logger.info(f"自动解决{min(3, conflict_report['total_conflicts'])}个冲突")
            
            self.last_induction_time = time.time()
            return result
        
        except Exception as e:
            logger.error(f"归纳失败: {e}")
            return {"success": False, "message": str(e)}
    
    def _check_periodic_induction(self):
        """检查是否需要定期归纳"""
        if not INDUCTION_AVAILABLE:
            return
        
        hours_since_last = (time.time() - self.last_induction_time) / 3600
        
        if hours_since_last >= self.induction_interval:
            logger.info("触发定期归纳任务")
            self.run_induction(days=7)
    
    def _get_user_preference_weights(self) -> tuple:
        """获取用户偏好权重"""
        prefs = config.get("user_preferences", {})
        mode = prefs.get("mode", "balanced")
        
        if mode == "quality":
            return (1.0, 0.0, 0.0)  # quality, speed, cost
        elif mode == "speed":
            return (0.0, 1.0, 0.0)
        elif mode == "cost":
            return (0.0, 0.0, 1.0)
        else:  # balanced
            weights = prefs.get("weights", {})
            w_quality = weights.get("quality", 0.5)
            w_speed = weights.get("speed", 0.3)
            w_cost = weights.get("cost", 0.2)
            return (w_quality, w_speed, w_cost)
    
    def _select_model(self, intent: Intent):
        """完全数据驱动的模型选择"""
        intent_type = intent.type
        
        # 0. 检查学习规则设置的临时优先模型
        if hasattr(self, '_temp_preferred_model') and self._temp_preferred_model:
            preferred = self._temp_preferred_model
            if preferred in self.adapters:
                logger.info(f"✓ 学习规则优先模型: {preferred}")
                self._temp_preferred_model = None  # 清除临时标记
                return self.adapters[preferred]
        
        # 1. 从统计库获取最佳模型(核心决策)
        w_quality, w_speed, w_cost = self._get_user_preference_weights()
        
        weights = {
            "quality": w_quality,
            "speed": w_speed,
            "cost": w_cost,
            "success": 0.1  # 成功率基础权重
        }
        
        best_model_name = self.stats.get_best_model_for_task(
            task_type=intent_type,
            weights=weights
        )
        
        if best_model_name and best_model_name in self.adapters:
            logger.info(f"✓ 统计库推荐模型: {best_model_name} for {intent_type}")
            return self.adapters[best_model_name]
        
        # 2. 降级:使用配置文件中的fallback顺序
        fallback_order = config.get(
            f"fallback.task_model_order.{intent_type}",
            []
        )
        
        # 如果没有特定意图的fallback,使用全局默认
        if not fallback_order:
            fallback_order = config.get("fallback.default_order", [])
        
        for model_name in fallback_order:
            if model_name in self.adapters:
                logger.warning(f"⚠ 统计库无记录,使用fallback: {model_name}")
                return self.adapters[model_name]
        
        # 3. 最终降级:使用第一个可用模型
        if self.adapters:
            fallback = next(iter(self.adapters.values()))
            logger.warning(f"⚠ 无匹配模型,使用默认: {fallback.model_name}")
            return fallback
        
        raise RuntimeError("No model available")
    
    def _get_recent_context(self, rounds: int = None) -> str:
        """获取最近对话上下文(内存缓存优化)"""
        if rounds is None:
            rounds = config.get("memory.short_term.max_rounds", 3)
        
        if len(self.context_buffer) == 0:
            self._load_context_from_file()
        
        context_list = list(self.context_buffer)
        recent = context_list[-rounds*2:] if len(context_list) >= rounds*2 else context_list
        
        if not recent:
            return ""
        
        context = "Recent conversation history:\n"
        for entry in recent:
            context += entry + "\n"
        context += "\nCurrent question: "
        return context
    
    def _load_context_from_file(self):
        """从文件加载上下文到内存缓冲区"""
        file_path = config.get("memory.short_term.file_path", "campfire_log.txt")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line.startswith("[") and ("user:" in line.lower() or "拓荒者:" in line):
                    content = line.split("] ", 1)[-1]
                    self.context_buffer.append(content)
        
        except FileNotFoundError:
            pass
    
    def _build_prompt(self, intent: Intent) -> str:
        """构建提示词"""
        if intent.type == "code":
            return f"Output code only, no extra explanation. User request: {intent.raw_text}"
        elif intent.type == "question":
            return f"Answer the following question in detail: {intent.raw_text}"
        elif intent.type == "memory":
            return f"Based on the conversation history, answer the user's question. If history does not contain info, say you don't know. Question: {intent.raw_text}"
        elif intent.type == "document":
            return f"Analyze and summarize the following document:\n\n{intent.raw_text}"
        else:
            return intent.raw_text
    
    def plan(self, intent: Intent):
        """执行任务规划"""
        self._check_periodic_induction()
        
        # 优先检查向量检索是否有相似成功案例
        if VECTOR_AVAILABLE:
            try:
                similar = vector_retriever.find_similar_plan(intent.raw_text, intent.type, top_k=1)
                if similar and similar[0].get('quality_score', 0) >= 70:
                    logger.info(f"✓ 复用相似成功案例(相似度:{similar[0].get('similarity', 0):.2f})")
                    response = similar[0].get('plan', {}).get('response', '')
                    if response:
                        bus.publish("plan_executed", response)
                        return
            except Exception as e:
                logger.debug(f"向量检索失败: {e}")
        
        rule = self._match_learning_rule(intent)
        if rule:
            logger.info(f"命中学习规则: {rule['id']} -> {rule['action']}")
            
            action = rule["action"]
            action_parsed = self._parse_action(action)
            
            if action_parsed["type"] == "reroute":
                target_model = action_parsed["target"]
                if target_model in self.adapters:
                    model = self.adapters[target_model]
                    base_prompt = self._build_prompt(intent)
                    context = self._get_recent_context()
                    full_prompt = f"{context}\n{base_prompt}" if context else base_prompt
                    
                    response = model.generate(full_prompt, task_type=intent.type)
                    
                    if isinstance(response, tuple):
                        response, _ = response
                    
                    self._update_rule_stats(rule["id"], success=True)
                    bus.publish("plan_executed", response)
                    return
            
            elif action_parsed["type"] == "merge":
                for sub_action in action_parsed["actions"]:
                    if sub_action["type"] == "reroute":
                        target_model = sub_action["target"]
                        if target_model in self.adapters:
                            try:
                                model = self.adapters[target_model]
                                base_prompt = self._build_prompt(intent)
                                context = self._get_recent_context()
                                full_prompt = f"{context}\n{base_prompt}" if context else base_prompt
                                
                                response = model.generate(full_prompt, task_type=intent.type)
                                
                                if isinstance(response, tuple):
                                    response, _ = response
                                
                                self._update_rule_stats(rule["id"], success=True)
                                bus.publish("plan_executed", response)
                                return
                            except Exception as e:
                                logger.warning(f"合并动作{sub_action}失败: {e}")
                                continue
            
            elif action_parsed["type"] == "prefer":
                target_model = action_parsed["target"]
                if target_model in self.adapters:
                    self._temp_preferred_model = target_model
                    logger.info(f"临时优先模型: {target_model}")
            
            elif action_parsed["type"] == "ask_user":
                msg = action_parsed["message"]
                bus.publish("clarification_needed", {
                    "question_id": f"rule_{rule['id']}",
                    "message": msg,
                    "options": ["确认", "取消"]
                })
                return
            
            elif action_parsed["type"] == "avoid":
                avoid = action_parsed["target"]
                if not hasattr(self, '_temp_avoid_models'):
                    self._temp_avoid_models = []
                self._temp_avoid_models.append(avoid)
                logger.info(f"临时避免模型: {avoid}")
        
        context = self._get_recent_context()
        base_prompt = self._build_prompt(intent)
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
            result = model.generate(full_prompt, task_type=intent.type)
            
            if isinstance(result, tuple):
                response, quality = result
            else:
                response = result
                quality = self._evaluate_quality(response, intent.type)
            
            duration = time.time() - start
            self.last_call_info["duration"] = duration
            self.last_call_info["quality"] = quality
            
            audit = SelfAudit.audit(response, intent.type)
            if audit["blocked"]:
                logger.warning(f"Audit blocked: {audit['reason']}")
                response = f"⚠️ 系统检测到危险操作,已拦截。原因: {audit['reason']}"
            
            self.experience_pool.add_experience(
                intent_type=intent.type,
                raw_input=intent.raw_text,
                plan=base_prompt,
                model_name=model.model_name,
                quality_score=quality,
                user_feedback=0,
                success=quality >= 50,
                duration=duration,
                response=response
            )
            
            self.context_buffer.append(f"用户: {intent.raw_text}")
            self.context_buffer.append(f"拓荒者: {response[:200]}")
            
            intent_key = f"{intent.type}_{model.model_name}"
            if intent_key in self.failure_history:
                recent_failures = [
                    t for t in self.failure_history[intent_key]
                    if time.time() - t < 300
                ]
                self.failure_history[intent_key] = recent_failures
            
            bus.publish("plan_executed", response)
            
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            
            intent_key = f"{intent.type}_{model.model_name}"
            if intent_key not in self.failure_history:
                self.failure_history[intent_key] = []
            self.failure_history[intent_key].append(int(time.time()))
            
            if self.tool_generator:
                failure_context = {
                    "task_type": intent.type,
                    "user_input": intent.raw_text,
                    "failure_reason": str(e),
                    "model": model.model_name
                }
                try:
                    new_tool = self.tool_generator.generate_and_register_tool(
                        failure_context, auto_register=False
                    )
                    if new_tool:
                        logger.info(f"生成新工具: {new_tool.name}")
                except Exception as te:
                    logger.warning(f"工具生成失败: {te}")
            
            fallback_response = self._try_fallback_models(intent, full_prompt)
            
            if fallback_response:
                bus.publish("plan_executed", fallback_response)
            else:
                if self.decomposer:
                    error_count = len(self.failure_history.get(intent_key, []))
                    
                    if self.decomposer.should_decompose(intent.type, 0, error_count):
                        decompose_msg = self.decomposer.generate_fallback_message(
                            intent.type,
                            list(self.adapters.keys())
                        )
                        bus.publish("plan_executed", decompose_msg)
                        return
                
                error_msg = self._format_error(e)
                bus.publish("plan_executed", error_msg)
    
    def _evaluate_quality(self, response: str, task_type: str) -> int:
        """评估响应质量"""
        if not response or len(response) < 10:
            return 20
        
        score = 50
        
        if task_type == "code":
            if "def " in response or "class " in response:
                score += 15
            if "```" in response:
                score += 10
            if len(response) > 100:
                score += 10
        
        elif task_type == "question":
            if len(response) > 50:
                score += 10
            if "。" in response or "." in response:
                score += 5
            if any(word in response for word in ["因为", "所以", "因此", "由于"]):
                score += 10
        
        elif task_type == "document":
            if len(response) > 100:
                score += 15
            if "总结" in response or "摘要" in response:
                score += 10
        
        return min(score, 100)
    
    def _try_fallback_models(self, intent: Intent, full_prompt: str) -> Optional[str]:
        """尝试fallback模型"""
        intent_type = intent.type
        
        fallback_order = config.get(f"fallback.task_model_order.{intent_type}", [])
        if not fallback_order:
            fallback_order = config.get("fallback.default_order", [])
        
        current_model = self.last_call_info.get("model")
        if current_model in fallback_order:
            fallback_order = [m for m in fallback_order if m != current_model]
        
        for model_name in fallback_order:
            if model_name not in self.adapters:
                continue
            
            try:
                logger.info(f"尝试fallback模型: {model_name}")
                model = self.adapters[model_name]
                response = model.generate(full_prompt, task_type=intent_type)
                
                if isinstance(response, tuple):
                    response, _ = response
                
                logger.info(f"Fallback成功: {model_name}")
                return response
            
            except Exception as e:
                logger.warning(f"Fallback失败 {model_name}: {e}")
                continue
        
        return None
    
    def _format_error(self, error: Exception) -> str:
        """格式化友好的错误消息"""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return "抱歉,处理超时。建议:\n1. 简化问题\n2. 稍后重试"
        elif "connection" in error_str or "connect" in error_str:
            return "抱歉,服务连接失败。请检查:\n1. 网络连接\n2. 服务状态"
        elif "rate limit" in error_str or "429" in error_str:
            return "抱歉,API调用频率超限。建议:\n1. 稍后重试\n2. 降低调用频率"
        elif "unauthorized" in error_str or "401" in error_str:
            return "抱歉,API认证失败。请检查:\n1. API密钥是否正确\n2. 账号是否有效"
        elif "model" in error_str and ("not found" in error_str or "unavailable" in error_str):
            return "抱歉,模型不可用。请检查:\n1. 模型名称是否正确\n2. 服务是否支持该模型"
        else:
            logger.error(f"未分类错误: {error}", exc_info=True)
            return "抱歉,处理时出错。请稍后重试或联系管理员。"
    
    def _match_learning_rule(self, intent: Intent) -> Optional[Dict]:
        """匹配学习规则库中的活跃规则"""
        try:
            import sqlite3
            from infrastructure.rule_matcher import RuleMatcher
            
            conn = sqlite3.connect("learning_rules.db")
            conn.row_factory = sqlite3.Row
            cur = conn.execute('''
                SELECT id, condition, action, priority, confidence
                FROM learning_rules
                WHERE status = 'active'
                ORDER BY priority ASC, confidence DESC
            ''')
            rules = [dict(row) for row in cur.fetchall()]
            conn.close()
            
            matcher = RuleMatcher()
            context = {
                "intent_type": intent.type,
                "quality": self.last_call_info.get("quality", 100),
                "model": self.last_call_info.get("model", ""),
                "duration": self.last_call_info.get("duration", 0),
            }
            
            for rule in rules:
                cond = rule["condition"]
                if matcher.evaluate_condition(cond, context):
                    logger.debug(f"规则匹配成功: {cond}")
                    return rule
            
            return None
        
        except Exception as e:
            logger.debug(f"规则匹配失败: {e}")
            return None
    
    def _update_rule_stats(self, rule_id: int, success: bool = True):
        """更新规则应用统计"""
        try:
            import sqlite3
            with sqlite3.connect("learning_rules.db") as conn:
                conn.execute('''
                    UPDATE learning_rules
                    SET apply_count = apply_count + 1,
                        success_count = success_count + ?,
                        last_applied = ?
                    WHERE id = ?
                ''', (1 if success else 0, time.time(), rule_id))
        
        except Exception as e:
            logger.debug(f"更新规则统计失败: {e}")
    
    def _parse_action(self, action: str) -> Dict:
        """解析动作字符串"""
        if action.startswith("merge:"):
            sub_actions = action.split(":", 1)[1].split("|")
            return {
                "type": "merge",
                "actions": [self._parse_action(a) for a in sub_actions]
            }
        elif action.startswith("reroute:"):
            return {"type": "reroute", "target": action.split(":")[1]}
        elif action.startswith("prefer_model:"):
            return {"type": "prefer", "target": action.split(":")[1]}
        elif action.startswith("avoid_model:"):
            return {"type": "avoid", "target": action.split(":")[1]}
        elif action.startswith("ask_user:"):
            return {"type": "ask_user", "message": action.split(":", 1)[1]}
        else:
            return {"type": "other", "raw": action}


# 向后兼容
Planner = DataDrivenPlanner
