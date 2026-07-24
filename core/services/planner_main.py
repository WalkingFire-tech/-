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
from core.services.planner.search_engine import SearchEngineMixin
from core.services.planner.knowledge_retriever import KnowledgeRetrieverMixin
from core.services.planner.self_evaluator import SelfEvaluatorMixin
from core.services.planner.meta_problem_solver import MetaProblemSolverMixin
from core.services.planner.model_selector import ModelSelectorMixin
from core.services.planner.tool_executor import ToolExecutorMixin
from core.services.planner.optimizer import OptimizerMixin
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


class DataDrivenPlanner(
    SearchEngineMixin,
    KnowledgeRetrieverMixin,
    SelfEvaluatorMixin,
    MetaProblemSolverMixin,
    ModelSelectorMixin,
    ToolExecutorMixin,
    OptimizerMixin,
):
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
        
        self._init_search()
        self._init_knowledge()
        self._init_evaluator()
        self._init_meta_solver()
        self._init_model_selector()
        self._init_tool_executor()
        self._init_optimizer()
    
    def get_last_call_info(self):
        return self.last_call_info
    
    
    
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
    
    
    
    
    
    
    
    
    
    
    
    
    
    def _normal_generate(self, intent: Intent) -> str:
        """降级到普通生成"""
        model = self._select_model(intent)
        response = model.generate(intent.raw_text, task_type=intent.type)
        if isinstance(response, tuple):
            response, _ = response
        return response
    
    
    
    
    
    
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
    
    
