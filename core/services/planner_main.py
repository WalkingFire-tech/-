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
from core.ports.adapters import get_storage_port
from loguru import logger
import time
from datetime import datetime
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
    logger.error(f"向量检索器加载失败: {e}")

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

try:
    from infrastructure.recurrent_reasoner import recurrent_reasoner
    RECURRENT_AVAILABLE = True
except Exception as e:
    RECURRENT_AVAILABLE = False
    logger.warning(f"循环推理器加载失败: {e}")

try:
    from infrastructure.cognitive_layer import cognitive_layer
    COGNITIVE_AVAILABLE = True
except Exception as e:
    COGNITIVE_AVAILABLE = False
    logger.warning(f"认知层加载失败: {e}")

try:
    from infrastructure.cognitive_evolution_adapter import cognitive_evolution_adapter
    EVOLUTION_AVAILABLE = True
except Exception as e:
    EVOLUTION_AVAILABLE = False
    logger.warning(f"v2.0认知进化架构加载失败: {e}")


class DataDrivenPlanner:
    """完全数据驱动的规划器"""
    
    def __init__(self, adapters: dict, adapters_lock=None):
        self.adapters = adapters
        self.adapters_lock = adapters_lock
        self.logger = CampfireLogger()
        self.stats = ModelStats()
        self.experience_pool = ExperiencePool()
        self.db_path = "data/experience_pool.db"
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
        
        # 缓存常用配置（减少I/O）
        self.optimization_enabled = config.get("optimization.enabled", True)
        self.induction_interval = config.get("optimization.induction_interval_hours", 24)
        self.parallel_enabled = config.get("parallel_scheduling.enabled", True)
        self.parallel_top_k = config.get("parallel_scheduling.top_k", 2)
        self.parallel_max_concurrent = config.get("parallel_scheduling.max_concurrent", 3)
        self.parallel_timeout = config.get("parallel_scheduling.timeout_seconds", 20)
        
        self.last_induction_time = 0
        self.last_optimization_score = None
        
        # 决策日志器
        try:
            from infrastructure.decision_logger import decision_logger
            self.decision_logger = decision_logger
        except Exception:
            self.decision_logger = None
        
        # 模型健康检查器
        try:
            from infrastructure.model_health_checker import model_health_checker
            self.health_checker = model_health_checker
        except Exception:
            self.health_checker = None
        
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
        
        try:
            from infrastructure.dialogue_stream_learner import dialogue_learner
            bus.subscribe("learning_opportunity", self._on_learning_opportunity)
            logger.info("对话流学习器已激活")
        except Exception as e:
            logger.warning(f"对话流学习器加载失败: {e}")
        
        try:
            from meta.meta_induction import meta_inductor
            logger.info("元归纳器已就绪")
        except Exception as e:
            logger.warning(f"元归纳器加载失败: {e}")
        
        try:
            from infrastructure.model_capability import model_capability
            from infrastructure.parallel_scheduler import parallel_scheduler
            from infrastructure.model_discovery import model_discovery
            from infrastructure.task_decomposer import task_decomposer
            from infrastructure.result_fusion import result_fusion
            
            self.capability = model_capability
            self.parallel_scheduler = parallel_scheduler
            self.model_discovery = model_discovery
            self.task_decomposer = task_decomposer
            self.result_fusion = result_fusion
            
            for name in self.adapters:
                self.capability.ensure_model_registered(name)
            
            logger.info("联邦调度模块已激活（含任务分解与结果融合）")
            
            import threading
            threading.Thread(target=self._auto_load_models, daemon=True).start()
            
        except Exception as e:
            logger.warning(f"联邦调度模块加载失败: {e}")
            self.parallel_scheduler = None
            self.capability = None
        
        # 第二阶段组件：深化感知与记忆
        try:
            from core.layers.l1_perception_enhanced import get_emotion_detector
            from core.memory.stereo_memory import get_stereo_memory
            from core.relationship.model import get_relationship_model
            from core.presence.self_review import get_self_review_engine
            from core.presence.active_perception import get_active_perception_engine
            
            self.emotion_detector = get_emotion_detector()
            self.stereo_memory = get_stereo_memory()
            self.relationship_model = get_relationship_model()
            self.self_review_engine = get_self_review_engine()
            self.active_perception = get_active_perception_engine()
            
            logger.info("第二阶段组件已激活：情绪感知、立体记忆、关系模型、自我评估、主动感知")
        except Exception as e:
            logger.warning(f"第二阶段组件加载失败: {e}")
            self.emotion_detector = None
            self.stereo_memory = None
            self.relationship_model = None
            self.self_review_engine = None
            self.active_perception = None
    
    def get_last_call_info(self):
        return self.last_call_info
    
    
    def _is_complex_task(self, intent: Intent) -> bool:
        """判断是否为复杂任务（需要联邦调度）
        
        复杂度判定标准：
        1. 文本长度 > 200字符
        2. 包含复杂关键词（并且、同时、比较、分析等）
        3. 特定意图类型（analysis、comparison、document）
        """
        if len(intent.raw_text) > 200:
            return True
        
        complex_keywords = [
            "并且", "同时", "先", "再", "比较", "分析", 
            "对比", "分别", "既要", "又要", "详细", "全面"
        ]
        if any(kw in intent.raw_text for kw in complex_keywords):
            return True
        
        if intent.type in ["analysis", "comparison", "document"]:
            return True
        
        if intent.type == "calculation":
            if any(op in intent.raw_text for op in ["+", "-", "*", "/", "(", ")"]):
                if len(intent.raw_text) > 50:
                    return True
        
        return False
    
    
    
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
            
            self.last_optimization_score = result.best_score
            
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
    
    
    def _get_user_preference_weights(self, urgency: str = 'normal') -> tuple:
        """获取用户偏好权重（增强版：情绪感知）"""
        prefs = config.get("user_preferences", {})
        mode = prefs.get("mode", "balanced")
        
        # 情绪影响权重调整
        if urgency == 'urgent':
            # 紧急情况：优先速度
            return (0.2, 0.7, 0.1)  # quality, speed, cost
        elif urgency == 'relaxed':
            # 放松情况：优先质量
            return (0.7, 0.2, 0.1)
        
        # 正常情况：使用用户配置
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
    
    
    
    def _data_driven_select(self, intent: Intent):
        """数据驱动的模型选择（降级方案）"""
        intent_type = intent.type
        
        # 0. 检查学习规则设置的临时优先模型
        if hasattr(self, '_temp_preferred_model') and self._temp_preferred_model:
            preferred = self._temp_preferred_model
            if preferred in self.adapters:
                logger.info(f"✓ 学习规则优先模型: {preferred}")
                self._temp_preferred_model = None
                return self.adapters[preferred]
        
        # 0.5. 情绪感知权重调整
        emotion_info = self._infer_emotion(intent)
        urgency = emotion_info.get('urgency', 'normal')
        
        # 1. 从统计库获取最佳模型
        w_quality, w_speed, w_cost = self._get_user_preference_weights(urgency)
        
        weights = {
            "quality": w_quality,
            "speed": w_speed,
            "cost": w_cost,
            "success": 0.1
        }
        
        # 记录情绪影响
        if urgency == 'urgent':
            logger.info(f"⚡ 检测到紧急情绪，优先选择快速模型")
        
        best_model_name = self.stats.get_best_model_for_task(
            task_type=intent_type,
            weights=weights
        )
        
        # 健康检查
        if best_model_name and best_model_name in self.adapters:
            if self.health_checker and not self.health_checker.is_available(best_model_name):
                logger.warning(f"模型 {best_model_name} 不可用，选择备选")
                best_model_name = None
        
        if best_model_name and best_model_name in self.adapters:
            logger.info(f"✓ 数据驱动选择: {best_model_name} for {intent_type}")
            return self.adapters[best_model_name]
        
        # 2. 降级:使用配置fallback
        fallback_order = config.get(
            f"fallback.task_model_order.{intent_type}",
            []
        )
        
        if not fallback_order:
            fallback_order = config.get("fallback.default_order", [])
        
        # 过滤不可用模型
        if self.health_checker:
            fallback_order = [
                m for m in fallback_order 
                if self.health_checker.is_available(m)
            ]
        
        for model_name in fallback_order:
            if model_name in self.adapters:
                logger.warning(f"⚠ 使用fallback: {model_name}")
                return self.adapters[model_name]
        
        # 3. 最终降级:第一个可用模型
        if self.adapters:
            available_models = list(self.adapters.keys())
            if self.health_checker:
                available_models = [
                    m for m in available_models
                    if self.health_checker.is_available(m)
                ]
            
            if available_models:
                fallback_model = available_models[0]
                fallback = self.adapters[fallback_model]
                logger.warning(f"⚠ 无匹配模型,使用默认: {fallback.model_name}")
                return fallback
        
        raise RuntimeError("No model available")
        """完全数据驱动的模型选择（增强版：情绪感知）"""
        intent_type = intent.type
        
        # 0. 检查学习规则设置的临时优先模型
        if hasattr(self, '_temp_preferred_model') and self._temp_preferred_model:
            preferred = self._temp_preferred_model
            if preferred in self.adapters:
                logger.info(f"✓ 学习规则优先模型: {preferred}")
                self._temp_preferred_model = None
                return self.adapters[preferred]
        
        # 0.5. 情绪感知权重调整（新增）
        emotion_info = self._infer_emotion(intent)
        urgency = emotion_info.get('urgency', 'normal')
        
        # 1. 从统计库获取最佳模型(核心决策)
        w_quality, w_speed, w_cost = self._get_user_preference_weights(urgency)
        
        weights = {
            "quality": w_quality,
            "speed": w_speed,
            "cost": w_cost,
            "success": 0.1
        }
        
        # 记录情绪影响
        if urgency == 'urgent':
            logger.info(f"⚡ 检测到紧急情绪，优先选择快速模型")
        
        best_model_name = self.stats.get_best_model_for_task(
            task_type=intent_type,
            weights=weights
        )
        
        # 健康检查：确保模型可用
        if best_model_name and best_model_name in self.adapters:
            if self.health_checker and not self.health_checker.is_available(best_model_name):
                logger.warning(f"模型 {best_model_name} 不可用，选择备选")
                best_model_name = None
        
        if best_model_name and best_model_name in self.adapters:
            logger.info(f"✓ 统计库推荐模型: {best_model_name} for {intent_type}")
            
            # 记录决策
            if self.decision_logger:
                self.decision_logger.log_decision(
                    decision_type="model_selection",
                    choice=best_model_name,
                    reason=f"统计库推荐，任务类型: {intent_type}",
                    alternatives=list(self.adapters.keys())[:3],
                    score=0.8
                )
            
            return self.adapters[best_model_name]
        
        # 2. 降级:使用配置文件中的fallback顺序
        fallback_order = config.get(
            f"fallback.task_model_order.{intent_type}",
            []
        )
        
        if not fallback_order:
            fallback_order = config.get("fallback.default_order", [])
        
        # 过滤不可用模型
        if self.health_checker:
            fallback_order = [
                m for m in fallback_order 
                if self.health_checker.is_available(m)
            ]
        
        for model_name in fallback_order:
            if model_name in self.adapters:
                logger.warning(f"⚠ 统计库无记录,使用fallback: {model_name}")
                
                # 记录决策
                if self.decision_logger:
                    self.decision_logger.log_decision(
                        decision_type="model_selection",
                        choice=model_name,
                        reason="统计库无记录，使用fallback",
                        alternatives=fallback_order
                    )
                
                return self.adapters[model_name]
        
        # 3. 最终降级:使用第一个可用模型
        if self.adapters:
            available_models = list(self.adapters.keys())
            if self.health_checker:
                available_models = [
                    m for m in available_models
                    if self.health_checker.is_available(m)
                ]
            
            if available_models:
                fallback_model = available_models[0]
                fallback = self.adapters[fallback_model]
                logger.warning(f"⚠ 无匹配模型,使用默认: {fallback.model_name}")
                return fallback
        
        raise RuntimeError("No model available")
    
    def _get_recent_context(self, rounds: int = None) -> str:
        """获取最近对话上下文(内存缓存优化 + 会话压缩)"""
        if rounds is None:
            rounds = config.get("memory.short_term.max_rounds", 3)
        
        if len(self.context_buffer) == 0:
            self._load_context_from_file()
        
        # 会话压缩（新增）
        context_list = list(self.context_buffer)
        if len(context_list) > 20:  # 超过20轮触发压缩
            try:
                from infrastructure.session_compressor import SessionCompressor
                compressor = SessionCompressor()
                
                # 转换为字典格式（压缩器期望的格式）
                messages = []
                for i, entry in enumerate(context_list[:-8]):
                    role = "user" if i % 2 == 0 else "assistant"
                    messages.append({"role": role, "content": entry})
                
                # 压缩
                result = compressor.compress(messages)
                
                if result.get("compressed"):
                    # 提取压缩后的摘要
                    summary = result.get("summary", "")
                    context_list = [f"[历史摘要] {summary[:200]}"] + context_list[-8:]
                    logger.info(f"会话压缩: {result.get('original_length')} → {len(context_list)}")
            except Exception as e:
                logger.error(f"会话压缩失败: {e}")
        
        recent = context_list[-rounds*2:] if len(context_list) >= rounds*2 else context_list
        
        if not recent:
            return ""
        
        # 改进：更清晰的上下文格式
        context = "=== 对话历史 ===\n"
        for entry in recent:
            context += entry + "\n"
        context += "=== 当前问题 ===\n"
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
        has_context = len(self.context_buffer) > 0
        
        if intent.type == "code":
            return f"Output code only, no extra explanation. User request: {intent.raw_text}"
        elif intent.type == "question":
            if has_context:
                return f"[上下文对话] 根据之前的对话历史，回答用户的问题。如果用户在追问或要求补充，请继续之前的话题。\n\n问题: {intent.raw_text}"
            return f"Answer the following question in detail: {intent.raw_text}"
        elif intent.type == "memory":
            return f"Based on the conversation history, answer the user's question. If history does not contain info, say you don't know. Question: {intent.raw_text}"
        elif intent.type == "document":
            return f"Analyze and summarize the following document:\n\n{intent.raw_text}"
        elif intent.type == "verification":
            # challenge场景：验证上一回答的正确性
            if has_context:
                recent = list(self.context_buffer)[-2:]  # 获取最近的问答
                last_response = ""
                for entry in recent:
                    if entry.startswith("拓荒者:"):
                        last_response = entry.replace("拓荒者:", "").strip()
                        break
                
                if last_response:
                    return f"[质疑验证] 用户在质疑上一条回答的正确性。\n\n上一条回答: {last_response}\n\n用户质疑: {intent.raw_text}\n\n请检查上一条回答是否正确，如果有错误请指出并纠正，如果正确请解释原因。"
                else:
                    return f"[质疑验证] 用户在质疑，但没有找到上一条回答。请回应用户的质疑: {intent.raw_text}"
            return f"用户在质疑或验证。请认真回应: {intent.raw_text}"
        else:
            if has_context:
                return f"[上下文对话] {intent.raw_text}"
            return intent.raw_text
    
    def _on_learning_opportunity(self, opportunity: Dict):
        """处理学习机会事件"""
        opp_type = opportunity.get('type')
        action = opportunity.get('action')
        
        logger.info(f"捕获学习机会: {opp_type} → {action}")
        
        if action == 'trigger_induction' or action == 'force_induction':
            if INDUCTION_AVAILABLE:
                logger.info("从学习机会触发归纳")
                self.run_induction(days=1)
        
        elif action == 'consider_clarification':
            logger.debug("语义漂移已记录，等待后续处理")
    
    
    
    def _handle_memory_query(self, intent: Intent) -> str:
        """处理记忆查询意图 - 真正的反思，不是形式主义
        
        Args:
            intent: 记忆意图
        
        Returns:
            历史对话内容（带深度反思）
        """
        user_question = intent.raw_text.lower()
        
        # 检查是否是回顾历史对话
        if any(kw in user_question for kw in ["回顾历史", "历史对话", "历史问题", "回顾对话", "之前的对话"]):
            try:
                # 获取历史对话
                if hasattr(self, 'campfire') and self.campfire:
                    context = self.campfire.get_recent_context(rounds=10)
                else:
                    from infrastructure.logger import CampfireLogger
                    temp_logger = CampfireLogger()
                    context = temp_logger.get_recent_context(rounds=10)
                
                if not context:
                    return "暂无历史对话记录。"
                
                # 真正的深度反思
                try:
                    from core.honest_learning_system import honest_system
                    
                    # 解析历史对话
                    history = self._parse_history(context)
                    
                    # 深度反思（不是简单罗列）
                    reflection = honest_system.deep_reflection(user_question, history)
                    
                    return reflection
                    
                except Exception as e:
                    logger.warning(f"深度反思失败: {e}")
                    # 降级：返回历史 + 承认反思不足
                    return f"""以下是最近的对话历史：

{context}

---

**反思声明**

我必须承认：我目前只是罗列了历史，没有进行真正的反思。

这是我的不足，我会改进。

---
_共显示最近10轮对话_"""
                
            except Exception as e:
                logger.error(f"读取历史对话失败: {e}")
                return "抱歉，无法读取历史对话记录。"
        
        # 检查是否是质疑之前回答
        if any(kw in user_question for kw in ["之前", "刚才", "刚才你", "你刚才", "不对", "错误"]):
            try:
                from core.honest_learning_system import honest_system
                from core.requirement_validator import requirement_validator
                
                # 获取最近的对话
                if hasattr(self, 'campfire') and self.campfire:
                    context = self.campfire.get_recent_context(rounds=2)
                else:
                    from infrastructure.logger import CampfireLogger
                    temp_logger = CampfireLogger()
                    context = temp_logger.get_recent_context(rounds=2)
                
                if not context:
                    return "让我回顾一下刚才的对话..."
                
                # 解析并验证
                history = self._parse_history(context)
                
                if history:
                    last = history[-1]
                    user_msg = last.get('user', '')
                    assistant_msg = last.get('assistant', '')
                    
                    # 验证之前的回答
                    req = requirement_validator.extract_core_requirement(user_msg)
                    is_valid, issues = requirement_validator.validate_response_against_requirement(
                        req, assistant_msg
                    )
                    
                    if not is_valid:
                        # 承认错误
                        return f"""
【承认错误】

您说得对，我刚才的回答有问题。

**用户需求**: {user_msg[:100]}
**我的回答**: {assistant_msg[:100]}

**问题所在**:
{chr(10).join(f'- {issue}' for issue in issues)}

**自我批评**:
我没有仔细验证就给出了答案，这是不负责任的表现。

**纠正**:
让我重新认真回答您的问题...

---

_感谢您的质疑，这帮助我发现了错误。_
"""
                
                return "让我认真反思刚才的回答..."
                
            except Exception as e:
                logger.warning(f"历史纠正失败: {e}")
                return "我正在反思刚才的回答..."
        
        # 其他记忆查询
        return "我目前只能记住当前对话中的内容。如果需要回顾历史对话，请说'回顾历史对话'。"
    
    def _parse_history(self, context: str) -> list:
        """解析历史对话文本"""
        
        history = []
        lines = context.split('\n')
        
        current_user = ""
        current_assistant = ""
        
        for line in lines:
            if line.startswith('用户:') or line.startswith('User:'):
                if current_user and current_assistant:
                    history.append({
                        'user': current_user,
                        'assistant': current_assistant
                    })
                current_user = line.split(':', 1)[1].strip()
                current_assistant = ""
            elif line.startswith('拓荒者:') or line.startswith('Assistant:'):
                current_assistant = line.split(':', 1)[1].strip()
        
        if current_user and current_assistant:
            history.append({
                'user': current_user,
                'assistant': current_assistant
            })
        
        return history
    
    
    
    
    
    
    
    
    
    def _normal_generate(self, intent: Intent) -> str:
        """降级到普通生成"""
        model = self._select_model(intent)
        response = model.generate(intent.raw_text, task_type=intent.type)
        if isinstance(response, tuple):
            response, _ = response
        return response
    
    def _parallel_schedule(self, intent: Intent) -> Optional[str]:
        """并行调度多模型
        
        Args:
            intent: 用户意图
        
        Returns:
            最佳响应，None表示降级到单模型
        """
        try:
            from infrastructure.parallel_scheduler import parallel_scheduler
            from infrastructure.model_capability import model_capability
            
            context = self._get_recent_context()
            base_prompt = self._build_prompt(intent)
            full_prompt = f"{context}\n{base_prompt}" if context else base_prompt
            
            top_k = config.get("parallel_scheduling.top_k", 2)
            
            import asyncio
            
            async def _run_federated_call():
                return await parallel_scheduler.federated_call(
                    prompt=full_prompt,
                    task_type=intent.type,
                    adapters=self.adapters,
                    top_k=top_k
                )
            
            try:
                loop = asyncio.get_running_loop()
                result = asyncio.run_coroutine_threadsafe(
                    _run_federated_call(),
                    loop
                ).result(timeout=60)
            except RuntimeError:
                result = asyncio.run(_run_federated_call())
            
            if result.get('error'):
                logger.warning(f"联邦调度错误: {result['error']}")
                return None
            
            best = result.get('best')
            if best and best.get('success'):
                response = best.get('response')
                model_name = best.get('model_name')
                quality_score = best.get('final_score', 0.5) * 100
                duration = best.get('duration', 0)
                
                # 应用循环推理（深度思考）
                if RECURRENT_AVAILABLE and quality_score < 85:
                    logger.info(f"质量不足({quality_score:.0f})，启用循环推理增强")
                    try:
                        model = self.adapters.get(model_name)
                        if model:
                            enhanced_response, trajectory = recurrent_reasoner.reason_with_loops(
                                model=model,
                                prompt=intent.raw_text,
                                intent_type=intent.type,
                                context=context,
                                max_iterations=3
                            )
                            if enhanced_response:
                                response = enhanced_response
                                logger.info(f"循环推理增强完成: {len(trajectory)}轮迭代")
                    except Exception as e:
                        logger.warning(f"循环推理失败: {e}")
                
                self.experience_pool.add_experience(
                    intent_type=intent.type,
                    raw_input=intent.raw_text,
                    plan=base_prompt,
                    model_name=model_name,
                    quality_score=int(quality_score),
                    user_feedback=0,
                    success=quality_score >= 50,
                    duration=duration,
                    response=response
                )
                
                try:
                    model_capability.update_from_feedback(
                        model_name=model_name,
                        task_type=intent.type,
                        success=quality_score >= 50,
                        quality_score=quality_score / 100.0
                    )
                except Exception as cap_error:
                    logger.warning(f"能力矩阵更新失败: {cap_error}")
                
                stats = result.get('stats', {})
                logger.info(
                    f"并行调度完成: {stats.get('successful')}/{stats.get('total_models')}个模型成功, "
                    f"最佳={model_name}, 耗时={stats.get('duration', 0):.2f}s"
                )
                
                return response
            
            return None
            
        except Exception as e:
            logger.error(f"并行调度异常: {e}")
            return None
    
    
    
    
    
    def plan(self, intent: Intent):
        """主规划方法 - 清晰的流程编排
        
        流程:
        1. 反射级检查（最高优先级）
        2. 情绪推断（理解用户）
        3. 系统状态检查（自我感知）
        4. 意图路由（特殊意图处理）
        5. 五层防御（智能应对）
        6. 正常流程（常规处理）
        """
        # 1. 反射级检查
        if result := self._check_reflex_level(intent):
            bus.publish("plan_executed", result)
            return
        
        # 2. 情绪推断
        emotion = self._infer_emotion(intent)
        
        # 3. 系统状态检查
        if result := self._check_system_state():
            bus.publish("plan_executed", result)
            return
        
        # 4. 定期归纳检查
        self._check_periodic_induction()
        
        # 5. 意图路由
        if intent.type in ["meta_value", "meta_mechanism", "meta_capability", "meta"]:
            logger.info(f"处理元认知问题: {intent.type}")
            response = self._handle_meta_question(intent.raw_text, meta_type=intent.type)
            bus.publish("plan_executed", response)
            return
        
        # 5.5. 记忆意图处理
        if intent.type == "memory":
            logger.info("处理记忆查询")
            response = self._handle_memory_query(intent)
            bus.publish("plan_executed", response)
            return
        
        # 5.6. 认知模式检查（逻辑导向）
        if self._should_use_cognitive_mode(intent):
            logger.info("启用认知模式 - 逻辑导向")
            response = self._cognitive_mode(intent)
            bus.publish("plan_executed", response)
            return
        
        # 6. 五层防御
        if result := self._apply_five_layer_defense(intent):
            bus.publish("plan_executed", result)
            return
        
        # 7. 正常流程
        self._handle_normal_flow(intent, emotion)
        
    def _handle_normal_flow(self, intent: Intent, emotion: Dict):
        """【正常流程】常规处理逻辑 - 已拆分为子流程"""
        
        # 0. 学习规则影子匹配（记录统计，不干扰主流程）
        matched_rule = self._match_learning_rule(intent)
        if matched_rule:
            self._update_rule_stats(matched_rule["id"], success=True)
        
        # 0.5 所有问题类型都尝试搜索增强（扩展）
        if intent.type in ["question", "verification", "chat"]:
            logger.info(f"🔍 尝试搜索增强: intent.type={intent.type}, query={intent.raw_text[:50]}")
            if response := self._try_search_enhanced_answer(intent):
                self._update_phase2_components(intent, emotion, response)
                return
            else:
                logger.warning("⚠️ 搜索增强返回None，继续常规流程")
        
        # 1. 置信度评估与外脑协作
        if response := self._try_expert_collaboration(intent):
            self._update_phase2_components(intent, emotion, response)
            return
        
        # 2. 联邦调度流程
        if response := self._try_federation_flow(intent):
            self._update_phase2_components(intent, emotion, response)
            return
        
        # 3. 向量检索复用
        if response := self._try_vector_reuse(intent):
            self._update_phase2_components(intent, emotion, response)
            return
        
        # 4. 学习规则路由
        if response := self._try_rule_based_routing(intent):
            self._update_phase2_components(intent, emotion, response)
            return
        
        # 5. 单模型降级
        response = self._single_model_fallback(intent)
        self._update_phase2_components(intent, emotion, response)
    
        """更新第二阶段组件：关系模型、立体记忆、自我评估"""
        if not response:
            return
        
        # 1. 更新关系模型
        if hasattr(self, 'relationship_model') and self.relationship_model:
            try:
                self.relationship_model.update_from_conversation({
                    "user_satisfaction": 0.7,
                    "emotional_intensity": emotion.get("intensity", 0.5),
                    "duration_minutes": 2,
                    "system_helpfulness": 0.8,
                    "user_input": intent.raw_text,
                    "system_response": response
                })
            except Exception as e:
                logger.error(f"关系模型更新失败: {e}")
        
        # 2. 存储到立体记忆
        if hasattr(self, 'stereo_memory') and self.stereo_memory:
            try:
                from core.memory.stereo_memory import MemoryType
                self.stereo_memory.save({
                    "user_content": intent.raw_text,
                    "memory_type": MemoryType.CONVERSATION,
                    "context": {"emotion": emotion.get("emotion", "neutral")},
                    "metadata": {"response": response[:200]}
                })
            except Exception as e:
                logger.error(f"立体记忆存储失败: {e}")
        
        # 3. 自我评估
        if hasattr(self, 'self_review_engine') and self.self_review_engine:
            try:
                self.self_review_engine.review({
                    "conversation_id": str(id(intent)),
                    "user_input": intent.raw_text,
                    "system_response": response,
                    "perception_result": emotion,
                    "validation_result": {"status": "pass"}
                })
            except Exception as e:
                logger.error(f"自我评估失败: {e}")
    
    
    def _try_federation_flow(self, intent: Intent) -> Optional[str]:
        """尝试联邦调度流程"""
        if not (hasattr(self, 'parallel_scheduler') and self.parallel_scheduler):
            return None
        
        # 复杂任务检测
        if self._is_complex_task(intent):
            logger.info(f"检测到复杂任务，启用智能分解与联邦调度 (意图: {intent.type})")
            
            # 尝试任务分解
            if hasattr(self, 'task_decomposer') and hasattr(self, 'result_fusion'):
                response = self._decompose_and_execute(intent)
                if response:
                    bus.publish("plan_executed", response)
                    return response
                else:
                    logger.warning("任务分解失败，降级到联邦调度")
            
            # 联邦调度
            response = self._parallel_schedule(intent)
            if response:
                bus.publish("plan_executed", response)
                return response
            else:
                logger.warning("联邦调度失败，降级到普通路由")
        
        # 常规并行调度
        if self.parallel_enabled and len(self.adapters) >= 2:
            try:
                response = self._parallel_schedule(intent)
                if response:
                    bus.publish("plan_executed", response)
                    return response
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning(f"并行调度网络错误，降级到单模型: {e}")
            except Exception as e:
                logger.error(f"并行调度未知错误: {type(e).__name__}: {e}")
        
        return None
    
    
    def _try_rule_based_routing(self, intent: Intent) -> Optional[str]:
        """尝试学习规则路由"""
        rule = self._match_learning_rule(intent)
        if not rule:
            return None
        
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
                return response
        
        return None
    
    
    
    
    def _request_user_help(self, intent: Intent, error: str) -> Optional[str]:
        """【第4层防御】主动向用户求助
        
        当系统确定自己无法解决时，坦诚告知用户并提供帮助途径。
        这不仅是诚实，也是邀请用户参与完善的过程。
        
        Returns:
            求助消息，失败返回None
        """
        try:
            # 检查失败次数
            intent_key = f"{intent.type}"
            failures = self.failure_history.get(intent_key, [])
            recent_failures = [t for t in failures if time.time() - t < 300]
            
            # 只有连续失败才求助
            if len(recent_failures) < 2:
                return None
            
            logger.info(f"【第4层防御】主动求助 (失败{len(recent_failures)}次)")
            
            help_msg = f"""
抱歉，我在处理这个问题时遇到了困难。

**问题**: {intent.raw_text[:100]}...
**错误**: {error[:100]}

**您可以通过以下方式帮助我**：

1. 📝 **提供答案** - 如果您知道正确答案，请告诉我，我会记住它
   ```
   :teach <答案>
   ```

2. 🔍 **授权搜索** - 允许我调用外部工具
   ```
   :enable web_search
   ```

3. 🔄 **换种问法** - 尝试用不同的方式提问

4. 📊 **查看我的能力边界**
   ```
   你的能力边界在哪里？
   ```

我会从这次失败中学习，下次遇到类似问题时做得更好。
"""
            return help_msg
            
        except Exception as e:
            logger.error(f"求助消息生成失败: {e}")
            return None
    
    def _trigger_failure_learning(self, intent: Intent, error: str):
        """【第5层防御】失败学习机制
        记录失败案例，触发归纳总结，生成学习规则。
        
        这才是真正的学习：
        1. 检测到失败 -> 搜索学习
        2. 分析对比搜索结果
        3. 存储高质量知识
        4. 生成学习规则
        5. 下次遇到类似问题就能回答了
        """
        try:
            # 1. 记录失败（质量分为0）
            conn = get_storage_port()._get_conn(self.db_path)
            conn.execute('''
                INSERT INTO experiences 
                (intent_type, model_used, success, quality_score, response, context)
                VALUES (?, ?, 0, 0, ?, ?)
            ''', (
                intent.intent_type if intent else 'unknown',
                'none',
                f"[失败] {error}",
                json.dumps({'question': intent.raw_text if intent else ''}, ensure_ascii=False)
            ))
            conn.commit()
            
            logger.info(f"【第5层防御】失败已记录")
            
            # 2. 触发学习闭环 - 这才是关键！
            try:
                from core.learning_loop import check_and_learn
                
                question = intent.raw_text if intent else "未知问题"
                
                learning_result = check_and_learn(
                    question=question,
                    answer=None,
                    confidence=0.0,
                    quality_score=0.0,
                    error=str(error)
                )
                
                if learning_result.get("success"):
                    logger.info(f"✅ 学习闭环完成: 获得{learning_result['knowledge_gained']}条知识")
                    
                    # 如果学习成功，尝试用新知识回答
                    if learning_result['knowledge_gained'] > 0:
                        # 重新检索知识库
                        knowledge_result = self._try_knowledge_retrieval(intent)
                        if knowledge_result and knowledge_result.get('confidence', 0) > 0.5:
                            logger.info("🎯 用刚学到的知识回答问题！")
                            return knowledge_result['answer']
                
            except Exception as learn_error:
                logger.warning(f"学习闭环触发失败: {learn_error}")
            
            # 3. 触发归纳总结
            try:
                if INDUCTION_AVAILABLE:
                    from meta.induction import induction_scheduler
                    induction_scheduler.run_induction()
                    logger.info("失败后触发归纳总结")
            except Exception as induction_error:
                logger.error(f"归纳总结触发失败: {induction_error}")
            
            # 4. 触发主动学习器
            try:
                from core.active_scheduler import active_scheduler
                active_scheduler._run_optimization_tasks()
            except Exception as al_error:
                logger.error(f"主动学习器触发失败: {al_error}")
            
            # 5. 自动工具生成
            try:
                if self.tool_generator:
                    self.tool_generator.auto_generate_tools()
            except Exception as tool_error:
                logger.error(f"自动工具生成失败: {tool_error}")
            
            logger.info(f"【第5层防御】学习机制已触发")
            
        except Exception as e:
            logger.error(f"失败学习触发失败: {e}")
    
    
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
        """匹配学习规则库中的活跃规则，同时为trial规则记录影子匹配"""
        try:
            from infrastructure.rule_matcher import RuleMatcher
            
            conn = get_storage_port()._get_conn("data/learning_rules.db")
            cur = conn.execute('''
                SELECT id, condition, action, priority, confidence, status
                FROM learning_rules
                WHERE status IN ('active', 'trial')
                ORDER BY priority ASC, confidence DESC
            ''')
            rules = [dict(row) for row in cur.fetchall()]
            
            matcher = RuleMatcher()
            
            intent_type_mapped = intent.type
            INTENT_TYPE_MAP = {
                "greeting": "chat",
                "confirmation": "chat",
                "simple_query": "question",
                "complex_query": "code",
                "learning_trigger": "question",
                "challenge": "verification",
                "history_query": "memory",
            }
            mapped_type = INTENT_TYPE_MAP.get(intent.type, intent.type)
            
            context = {
                "intent_type": intent.type,
                "intent_type_legacy": mapped_type,
                "raw_input": intent.raw_text,
                "quality": self.last_call_info.get("quality", 100),
                "model": self.last_call_info.get("model", ""),
                "duration": self.last_call_info.get("duration", 0),
            }
            
            matched_active = None
            for rule in rules:
                cond = rule["condition"]
                if matcher.evaluate_condition(cond, context):
                    if rule.get("status") == "active":
                        logger.warning(f"规则匹配成功: {cond}")
                        matched_active = rule
                    elif rule.get("status") == "trial":
                        self._record_trial_match(rule["id"])
            
            return matched_active
        
        except Exception as e:
            logger.error(f"规则匹配失败: {e}")
            return None
    
    def _record_trial_match(self, rule_id: int):
        """记录trial规则的影子匹配，增加apply_count用于后续评估"""
        try:
            conn = get_storage_port()._get_conn("data/learning_rules.db")
            conn.execute('''
                UPDATE learning_rules
                SET apply_count = apply_count + 1,
                    last_applied = ?
                WHERE id = ? AND status = 'trial'
            ''', (time.time(), rule_id))
            from infrastructure.rule_trial_manager import rule_trial_manager
            rule_trial_manager.record_trial_result(rule_id, success=True)
        except Exception as e:
            logger.error(f"记录trial匹配失败: {e}")
    
    def _update_rule_stats(self, rule_id: int, success: bool = True):
        """更新规则应用统计"""
        try:
            conn = get_storage_port()._get_conn("data/learning_rules.db")
            conn.execute('''
                UPDATE learning_rules
                SET apply_count = apply_count + 1,
                    success_count = success_count + ?,
                    last_applied = ?
                WHERE id = ?
            ''', (1 if success else 0, time.time(), rule_id))
        
        except Exception as e:
            logger.error(f"更新规则统计失败: {e}")
    
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
    
    def _should_use_cognitive_mode(self, intent: Intent) -> bool:
        """
        判断是否应该使用认知模式
        
        条件：
        1. 用户明确请求（:plan命令）
        2. 资源不足（无可用模型）
        3. 任务复杂度高且信息缺口多
        """
        # 检查用户是否请求逻辑模式
        if hasattr(intent, 'entities') and intent.entities:
            if intent.entities.get("logic_only"):
                return True
        
        # 检查资源可用性
        if not self.adapters or len(self.adapters) == 0:
            logger.info("无可用模型，切换到认知模式")
            return True
        
        # 检查模型健康度
        if self.health_checker:
            healthy_models = [
                name for name in self.adapters.keys()
                if not self.health_checker.is_blacklisted(name)
            ]
            if not healthy_models:
                logger.info("所有模型不可用，切换到认知模式")
                return True
        
        # 检查任务复杂度
        if len(intent.raw_text) > 200:
            # 复杂任务，考虑使用认知模式辅助
            # 但不强制，只是增强
            pass
        
        return False
    
    def _cognitive_mode(self, intent: Intent) -> str:
        """
        认知模式 - 仅输出逻辑分析，不执行模型
        
        核心价值：
        - 即使没有模型，也能提供有价值的分析框架
        - 输出问题分解、因果链、执行计划
        - v2.0增强：六层认知进化架构
        """
        logger.info("进入认知模式")
        
        # 尝试使用v2.0进化架构
        if EVOLUTION_AVAILABLE and cognitive_evolution_adapter.should_use_evolution(intent.raw_text):
            logger.info("使用v2.0认知进化架构")
            
            try:
                result = cognitive_evolution_adapter.process_standalone(intent.raw_text)
                
                if result.get('is_valid'):
                    # v2.0处理成功
                    output = result.get('user_friendly_output', '')
                    
                    # 添加思考链摘要
                    thinking_chain = result.get('thinking_chain', [])
                    if thinking_chain:
                        output += "\n\n**思考过程**:"
                        for layer in thinking_chain[:3]:  # 只显示前3层
                            layer_name = layer.get('layer', '')
                            declaration = layer.get('declaration', '')
                            if declaration:
                                output += f"\n- [{layer_name}] {declaration[:80]}"
                    
                    return output
                else:
                    # v2.0检测到问题
                    output = result.get('user_friendly_output', '')
                    output += "\n\n⚠️ 系统检测到潜在问题，建议人工确认或提供更多信息。"
                    return output
                    
            except Exception as e:
                logger.error(f"v2.0认知进化架构失败: {e}")
                # 降级到现有认知层
        
        # 使用现有认知层
        if not COGNITIVE_AVAILABLE:
            return "认知层不可用，无法提供逻辑分析。"
        
        try:
            # 调用认知层
            result = cognitive_layer.analyze(
                text=intent.raw_text,
                intent_type=intent.type,
                context=self._get_recent_context()
            )
            
            # 生成报告
            report = cognitive_layer.generate_report(result)
            
            # 添加说明
            report += "\n\n---\n"
            report += "**说明**：以上为系统的逻辑分析结果。"
            report += "如需执行具体子任务，请确保模型可用或提供更多信息。"
            
            logger.info(f"认知模式完成: {len(result['subtasks'])}个子任务")
            
            return report
            
        except Exception as e:
            logger.error(f"认知模式失败: {e}")
            return f"逻辑分析失败：{str(e)}\n\n请尝试提供更明确的问题描述。"


# 向后兼容
Planner = DataDrivenPlanner
