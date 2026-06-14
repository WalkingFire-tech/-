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
        except:
            self.decision_logger = None
        
        # 模型健康检查器
        try:
            from infrastructure.model_health_checker import model_health_checker
            self.health_checker = model_health_checker
        except:
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
    
    def get_last_call_info(self):
        return self.last_call_info
    
    def _auto_load_models(self):
        """后台线程：自动发现并加载新模型"""
        if not hasattr(self, 'model_discovery'):
            return
        try:
            discovered = self.model_discovery.discover_all_models_sync()
            
            for info in discovered:
                name = info['name']
                if name not in self.adapters:
                    try:
                        from adapters.llm.ollama_adapter import OllamaAdapter
                        self.adapters[name] = OllamaAdapter(model_name=name)
                        
                        capabilities = info.get('capabilities', {})
                        self.capability.ensure_model_registered(name, capabilities)
                        
                        logger.info(f"自动发现并加载新模型: {name}")
                    except Exception as e:
                        logger.warning(f"无法加载模型 {name}: {e}")
        except Exception as e:
            logger.error(f"自动发现模型失败: {e}")
    
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
    
    def _update_capability_from_result(self, model_name: str, task_type: str,
                                       quality: float, success: bool):
        """根据调用结果更新能力矩阵"""
        try:
            self.capability.update_from_feedback(
                model_name=model_name,
                task_type=task_type,
                success=success,
                quality_score=quality
            )
        except Exception as e:
            logger.warning(f"能力矩阵更新失败: {e}")
    
    def _decompose_and_execute(self, intent: Intent) -> Optional[str]:
        """分解复杂任务并执行
        
        Args:
            intent: 用户意图
        
        Returns:
            融合后的结果
        """
        try:
            # 1. 分解任务
            llm_adapter = self.adapters.get('code_light') or next(iter(self.adapters.values()))
            subtasks = self.task_decomposer.decompose_with_llm(
                intent.raw_text, 
                llm_adapter=llm_adapter
            )
            
            if len(subtasks) <= 1:
                logger.info("任务无法分解，使用联邦调度")
                return self._parallel_schedule(intent)
            
            logger.info(f"任务已分解为 {len(subtasks)} 个子任务")
            
            # 2. 执行子任务
            results = []
            for subtask in subtasks:
                sub_intent = Intent(
                    type=subtask['type'],
                    raw_text=subtask['description'],
                    confidence=0.8,
                    entities=[]
                )
                
                # 使用联邦调度执行子任务
                result = self._parallel_schedule(sub_intent)
                if result:
                    results.append(result)
                else:
                    # 降级到单模型
                    model = self._select_model(sub_intent)
                    result = model.generate(subtask['description'], task_type=subtask['type'])
                    if isinstance(result, tuple):
                        result = result[0]
                    results.append(result if result else "")
            
            # 3. 融合结果
            summary_model = self.adapters.get('remote_gpt4') or self.adapters.get('mindchat')
            fused_result = self.result_fusion.fuse(
                subtasks=subtasks,
                results=results,
                original_intent=intent.raw_text,
                strategy='auto',
                summary_model=summary_model
            )
            
            # 4. 保存分解记录
            self.task_decomposer.save_decomposition(
                original_task=intent.raw_text,
                subtasks=subtasks,
                strategy='llm' if llm_adapter else 'rule',
                success=True,
                quality_score=self._evaluate_quality(fused_result, intent.type) / 100.0
            )
            
            logger.info(f"任务分解执行完成，融合结果长度: {len(fused_result)}")
            return fused_result
            
        except Exception as e:
            logger.error(f"任务分解执行失败: {e}")
            return None
    
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
    
    def _check_periodic_induction(self):
        """检查是否需要定期归纳"""
        if not INDUCTION_AVAILABLE:
            return
        
        hours_since_last = (time.time() - self.last_induction_time) / 3600
        
        if hours_since_last >= self.induction_interval:
            logger.info("触发定期归纳任务")
            self.run_induction(days=7)
            
            try:
                from meta.meta_induction import meta_inductor
                if meta_inductor.should_trigger_optimization():
                    logger.info("触发元归纳优化")
                    meta_result = meta_inductor.optimize_parameters()
                    if meta_result.get('success'):
                        logger.info(f"元归纳完成: {len(meta_result.get('adjustments', []))}项调整")
            except Exception as e:
                logger.warning(f"元归纳优化失败: {e}")
    
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
    
    def _select_model(self, intent: Intent):
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
                logger.debug(f"会话压缩失败: {e}")
        
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
    
    def _handle_meta_question(self, user_question: str) -> str:
        """
        处理元认知问题（关于系统自身的问题）
        
        Args:
            user_question: 用户关于系统的问题
        
        Returns:
            系统的自我反思回答
        """
        import sqlite3
        
        # 特殊处理：学习能力相关问题（直接回答，不反问）
        q_lower = user_question.lower()
        if any(kw in q_lower for kw in ["学习能力", "学习的能力", "学习能力"]):
            return """提升学习能力的核心方法：

**1. 主动回想（Active Recall）**
- 读完内容后合上书，用自己的话复述
- 不要重复阅读，而是主动提取记忆

**2. 间隔重复（Spaced Repetition）**
- 今天学、明天复习、一周后再看、一个月后再巩固
- 利用睡眠巩固记忆，分散学习比集中学习更有效
- 工具推荐：Anki（间隔重复闪卡）

**3. 费曼技巧（Feynman Technique）**
- 假装教给一个8岁孩子
- 卡住的地方就是你的知识盲区
- 用简单语言解释复杂概念

**4. 最小可行习惯**
- 每天5分钟，先建立习惯再延长
- 不要一开始就要求学1小时
- 习惯 > 强度

**5. 多模态编码**
- 同时使用：视觉（图表）、听觉（讲解）、动觉（动手写）
- 多通道输入强化神经连接

**6. 错误驱动学习**
- 错误不是失败，是定位盲区的信号
- 对每个错误做"错误分析"：为什么错？正确思路是什么？

**7. 元认知监控**
- 学习前：我要学什么？为什么学？
- 学习中：我理解了吗？哪里卡住了？
- 学习后：我学到了哪三个关键点？

如果需要针对特定领域（编程、语言、考试）的详细方案，请直接告诉我。"""
        
        if any(kw in q_lower for kw in ["培养学习", "自主学习", "学习习惯"]):
            return """培养自主学习习惯的实用方法：

**第一阶段：建立习惯（1-2周）**
- 固定时间：每天同一时间学习（如早上8点）
- 固定地点：创造专属学习空间
- 最小行动：从"打开书"开始，不要求学多久
- 触发机制：将学习绑定到已有习惯后（如"喝完咖啡后学习"）

**第二阶段：形成节奏（3-4周）**
- 番茄工作法：25分钟专注 + 5分钟休息
- 每日清单：列出3个最重要的事，完成打勾
- 周回顾：每周日回顾本周学习，规划下周

**第三阶段：深化习惯（2-3月）**
- 输出倒逼输入：学完就教别人或写笔记
- 项目驱动：用真实项目练习
- 社群支持：找到学习伙伴或社区

**关键原则**：
1. 环境 > 意志力（改变环境比靠意志力更有效）
2. 身份认同（"我是学习者"而非"我要学习"）
3. 允许失败（断档后立刻恢复，不要自责）

**工具推荐**：
- Forest：专注时种树，可视化学习时间
- Notion：构建个人知识库
- Obsidian：双向链接笔记"""

        # 特殊处理：能力边界查询
        if any(kw in user_question for kw in ["能力边界", "边界", "能力在哪", "你的能力"]):
            return self._report_capability_boundary()
        
        # 特殊处理：自我评估体系查询
        if any(kw in user_question for kw in ["自我评估", "评估体系", "如何决策", "如何认识"]):
            return self._report_self_assessment()
        
        # 特殊处理：对话评价
        if any(kw in user_question for kw in ["回顾对话", "评价", "给出评价"]):
            return self._evaluate_recent_dialogs()
        
        # 通用元认知问题处理
        try:
            conn_exp = sqlite3.connect('data/experience_pool.db')
            cur = conn_exp.execute("SELECT COUNT(*), AVG(quality_score) FROM experiences")
            exp_count, exp_quality = cur.fetchone()
            conn_exp.close()
            
            conn_rules = sqlite3.connect('data/learning_rules.db')
            cur = conn_rules.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = cur.fetchone()[0]
            conn_rules.close()
            
            best_score = getattr(self, 'last_optimization_score', 0.0)
            
        except Exception as e:
            logger.error(f"收集系统状态失败: {e}")
            exp_count, exp_quality, active_rules, best_score = 0, 0.0, 0, 0.0
        
        exp_quality = exp_quality if exp_quality is not None else 0.0
        best_score = best_score if best_score is not None else 0.0
        
        meta_prompt = f"""用户问我关于自身能力的问题：" {user_question} "

作为联盟拓荒者智能体，我需要反思自己的能力。以下是我的当前状态：

【系统状态】
- 经验池: {exp_count}条经验
- 平均响应质量: {exp_quality:.2f}分
- 活跃学习规则: {active_rules}条
- 最近优化得分: {best_score:.2f}

【我的理解能力】
我通过以下方式理解用户需求：
1. 意图识别：使用规则匹配识别任务类型（code/question/meta等）
2. 模型路由：根据统计库选择最适合的模型
3. 经验复用：通过向量检索重用历史成功案例
4. 规则学习：从失败中归纳新规则

【改进方向】
为了更好地理解需求，我可以：
1. 积累更多对话经验，学习用户的表达习惯
2. 主动提出澄清问题，减少误解
3. 从用户反馈中学习，调整路由策略
4. 优化意图识别规则，覆盖更多表达方式

请以第一人称"我"的语气回答用户，提供真诚的反思和具体的改进建议。
回答要简洁、具体、有温度。"""

        model = self.adapters.get("code_light") or self.adapters.get("remote_gpt4")
        
        if model:
            try:
                response = model.generate(meta_prompt, task_type="meta")
                if isinstance(response, tuple):
                    response, _ = response
                return response
            except Exception as e:
                logger.error(f"元认知回答生成失败: {e}")
        
        return f"""作为联盟拓荒者，我目前通过意图识别和模型路由来理解你的需求。

当前状态：
- 已积累 {exp_count} 条经验
- 平均响应质量 {exp_quality:.1f} 分
- 活跃学习规则 {active_rules} 条

为了更好地理解你的需求，我需要：
1. 从你的反馈中学习更多表达方式
2. 积累更多对话经验
3. 主动提出澄清问题

你觉得我在哪方面最需要改进？"""
    
    def _handle_memory_query(self, intent: Intent) -> str:
        """处理记忆查询意图
        
        Args:
            intent: 记忆意图
        
        Returns:
            历史对话内容
        """
        user_question = intent.raw_text.lower()
        
        # 检查是否是回顾历史对话
        if any(kw in user_question for kw in ["回顾历史", "历史对话", "历史问题", "回顾对话", "之前的对话"]):
            try:
                # 从campfire_log.txt读取最近20条对话
                if hasattr(self, 'campfire') and self.campfire:
                    context = self.campfire.get_recent_context(rounds=10)
                    if not context:
                        return "暂无历史对话记录。"
                    
                    return f"""以下是最近的对话历史：

{context}

---
_共显示最近10轮对话_"""
                
                # 如果campfire未初始化，临时创建
                from infrastructure.logger import CampfireLogger
                temp_logger = CampfireLogger()
                context = temp_logger.get_recent_context(rounds=10)
                
                if not context:
                    return "暂无历史对话记录。"
                
                return f"""以下是最近的对话历史：

{context}

---
_共显示最近10轮对话_"""
                
            except Exception as e:
                logger.error(f"读取历史对话失败: {e}")
                return "抱歉，无法读取历史对话记录。"
        
        # 其他记忆查询（记住、忘记等）
        return "我目前只能记住当前对话中的内容。如果需要回顾历史对话，请说'回顾历史对话'。"
    
    def _report_capability_boundary(self) -> str:
        """报告能力边界"""
        try:
            from infrastructure.health_dashboard import health_dashboard
            from infrastructure.model_capability import model_capability
            
            # 获取健康度
            aphi = health_dashboard.calculate_aphi()
            
            # 获取能力矩阵
            cap_stats = model_capability.export_stats()
            
            # 可用模型
            models = list(self.adapters.keys())
            
            # 构建报告
            report = f"""
╔══════════════════════════════════════════════════════════╗
║              联盟拓荒者能力边界报告                        ║
╚══════════════════════════════════════════════════════════╝

📊 健康状态
- APHI指数: {aphi['aphi']}/100
- 运行模式: {aphi['mode']}
- 任务成功率: {aphi['task_success_rate']}%
- 用户满意度: {aphi['user_satisfaction']}%

🤖 可用模型 ({len(models)}个)
"""
            for model in models:
                report += f"  • {model}\n"
            
            report += f"""
🧠 能力矩阵
- 已注册模型: {cap_stats.get('total_models', 0)}
- 能力维度: {cap_stats.get('total_dimensions', 0)}
- 平均置信度: {cap_stats.get('avg_confidence', 0):.2f}

🛠️ 工具系统
  ✅ 数学计算器 (支持高精度计算、动态常量)
  ✅ 代码执行器 (安全沙盒)
  ✅ 文件操作工具
  ✅ 文本提取工具
  ✅ 日期时间工具

🎯 意图识别能力
  ✅ code - 代码生成、算法实现
  ✅ question - 问题解答、知识查询
  ✅ calculation - 数学计算、数值处理
  ✅ document - 文档处理、信息提取
  ✅ meta - 元认知、自我反思
  ✅ memory - 记忆管理、上下文理解
  ✅ feedback - 用户反馈、质量评估

⚡ 当前限制
- 最大上下文: 4096 tokens
- 并发任务数: 3个
- 资源限制: CPU<80%, Memory<4GB
- 单次超时: 60秒

🔄 自我进化能力
  ✅ 能力矩阵动态更新
  ✅ 反事实模拟优化
  ✅ 失败案例学习
  ✅ 规则自动归纳
  ✅ 健康度监控

💡 我可以通过以下方式扩展能力边界：
1. 积累更多对话经验，提升意图识别准确率
2. 从用户反馈中学习，优化模型路由策略
3. 自动生成新工具，扩展功能覆盖
4. 通过反事实模拟探索更优决策路径
"""
            return report
            
        except Exception as e:
            logger.error(f"能力边界报告生成失败: {e}")
            return "抱歉，我暂时无法获取完整的能力边界信息。请稍后再试。"
    
    def _report_self_assessment(self) -> str:
        """报告自我评估体系"""
        try:
            from infrastructure.health_dashboard import health_dashboard
            from infrastructure.counterfactual_simulator import counterfactual_simulator
            
            aphi = health_dashboard.calculate_aphi()
            cf_stats = counterfactual_simulator.get_statistics()
            
            return f"""
╔══════════════════════════════════════════════════════════╗
║              自我评估体系报告                              ║
╚══════════════════════════════════════════════════════════╝

🎯 评估体系架构

1️⃣ 健康度仪表盘 (APHI)
   综合指标: {aphi['aphi']}/100
   ├─ 能力覆盖率: {aphi['capability_coverage']}%
   ├─ 任务成功率: {aphi['task_success_rate']}%
   ├─ 资源可用性: {aphi['resource_availability']}%
   ├─ 进化活力: {aphi['evolution_vitality']}%
   └─ 用户满意度: {aphi['user_satisfaction']}%

2️⃣ 反事实模拟器
   ├─ 总模拟次数: {cf_stats.get('total_simulations', 0)}
   ├─ 已应用洞察: {cf_stats.get('applied_insights', 0)}
   └─ 平均提升: {cf_stats.get('avg_improvement', 0):.2f}分

3️⃣ 能力矩阵
   ├─ 多维度评估: reasoning, coding, math, creative...
   ├─ 动态更新: 每次调用后自动调整
   └─ 时效衰减: 旧数据权重降低

4️⃣ 章程守护线程
   ├─ 每6小时健康检查
   ├─ 每日失败回顾
   ├─ 每日功能监控
   └─ 每周经验归档

🔄 决策流程

用户输入
  → 意图识别 (置信度评估)
  → 健康度检查 (APHI < 60? 降级模式)
  → 能力矩阵查询 (最佳模型选择)
  → 模型调用
  → 质量评估
  → 反事实模拟 (异步探索更优解)
  → 能力矩阵更新
  → 经验记录

💡 我通过"评估即驱动"的理念：
- 所有指标都形成闭环
- 评估结果反馈到决策
- 指标映射到具体行动
- 优化方向与长期目标对齐
"""
        except Exception as e:
            logger.error(f"自我评估报告生成失败: {e}")
            return "抱歉，我暂时无法获取评估体系信息。请稍后再试。"
    
    def _evaluate_recent_dialogs(self) -> str:
        """评价最近对话"""
        try:
            import sqlite3
            conn = sqlite3.connect('data/experience_pool.db')
            cur = conn.execute('''
                SELECT intent_type, raw_input, quality_score, success, model_name
                FROM experiences
                ORDER BY timestamp DESC
                LIMIT 10
            ''')
            recent = cur.fetchall()
            conn.close()
            
            if not recent:
                return "暂无最近对话记录。"
            
            report = """
╔══════════════════════════════════════════════════════════╗
║              最近对话评价报告                              ║
╚══════════════════════════════════════════════════════════╝

"""
            for i, (intent_type, raw_input, quality, success, model) in enumerate(recent, 1):
                status = "✅" if success else "❌"
                quality_val = quality if quality is not None else 0.0
                model_val = model if model is not None else "未知"
                report += f"{i}. {status} [{intent_type}] {raw_input[:30]}...\n"
                report += f"   质量: {quality_val:.1f}分 | 模型: {model_val}\n\n"
            
            qualities = [r[2] for r in recent if r[2] is not None]
            avg_quality = sum(qualities) / len(qualities) if qualities else 0.0
            success_rate = sum(1 for r in recent if r[3]) / len(recent) * 100
            
            report += f"""
📊 统计摘要
- 平均质量: {avg_quality:.1f}分
- 成功率: {success_rate:.1f}%
- 对话数: {len(recent)}

💡 改进建议
"""
            if avg_quality < 70:
                report += "- 质量偏低，建议检查意图识别准确率\n"
            if success_rate < 80:
                report += "- 成功率不足，建议回顾失败案例并创建学习任务\n"
            if avg_quality >= 70 and success_rate >= 80:
                report += "- 整体表现良好，继续保持！\n"
            
            return report
            
        except Exception as e:
            logger.error(f"对话评价失败: {e}")
            return "抱歉，无法获取对话评价信息。"
    
    def _estimate_self_confidence(self, intent: Intent) -> float:
        """评估系统对当前任务的理解置信度 (0~1)"""
        # 1. 意图识别置信度
        intent_conf = intent.confidence
        
        # 2. 历史相似任务成功率
        try:
            conn = sqlite3.connect('data/experience_pool.db')
            cursor = conn.execute('''
                SELECT success FROM experiences
                WHERE intent_type = ?
                ORDER BY timestamp DESC
                LIMIT 5
            ''', (intent.type,))
            
            similar = cursor.fetchall()
            success_rate = sum(1 for row in similar if row[0]) / max(len(similar), 1)
            conn.close()
        except:
            success_rate = 0.5
        
        # 3. 任务复杂度
        complexity = min(1.0, len(intent.raw_text) / 500)
        
        # 4. 是否有匹配规则
        has_rule = self._match_learning_rule(intent) is not None
        
        # 加权计算
        confidence = (
            0.4 * intent_conf +
            0.3 * success_rate +
            0.2 * (1 - complexity) +
            0.1 * (1.0 if has_rule else 0.0)
        )
        
        return min(0.95, max(0.05, confidence))
    
    def _try_tool_first(self, intent: Intent) -> Optional[str]:
        """【第1层防御】工具优先调用策略
        
        当意图类型明确且存在对应工具时，优先调用工具而非模型。
        这避免了模型"我不知道"的尴尬，直接给出精确答案。
        
        Returns:
            工具执行结果，失败返回None
        """
        try:
            from tools.registry import registry
            from tools.base import ToolCategory
            
            # 意图到工具类别的映射
            intent_to_category = {
                "calculation": ToolCategory.CALCULATION,
                "code": ToolCategory.CODE,
                "document": ToolCategory.FILE,
            }
            
            category = intent_to_category.get(intent.type)
            if not category:
                return None
            
            # 查找最佳工具
            best_tool = registry.get_best_tool(category, min_success_rate=0.5)
            if not best_tool:
                # 降级：列出所有该类别工具
                tools = registry.list_tools(category)
                if not tools:
                    return None
                best_tool = tools[0]
            
            logger.info(f"【第1层防御】工具优先: {best_tool.name} for {intent.type}")
            
            # 执行工具
            result = registry.execute(best_tool.name, expression=intent.raw_text)
            
            if result.success and result.output:
                # 格式化输出
                if isinstance(result.output, (int, float)):
                    return f"计算结果: {result.output}"
                elif isinstance(result.output, str):
                    return result.output
                else:
                    return str(result.output)
            
            return None
            
        except Exception as e:
            logger.debug(f"工具调用失败: {e}")
            return None
    
    def _try_knowledge_retrieval(self, intent: Intent) -> Optional[str]:
        """【第3层防御】知识库检索（经验复用）
        
        当问题在知识库中有记录时，直接返回历史答案。
        这避免了重复调用模型，实现"一次学习，终身受益"。
        
        Returns:
            历史答案，未找到返回None
        """
        try:
            from infrastructure.knowledge_injector import knowledge_injector
            
            result = knowledge_injector.retrieve_knowledge(
                question=intent.raw_text,
                intent_type=intent.type,
                min_quality=70.0
            )
            
            if result:
                answer, confidence = result
                logger.info(f"【第3层防御】知识库命中 (置信度: {confidence:.2f})")
                
                # 高置信度直接返回
                if confidence > 0.8:
                    return answer
                # 中等置信度添加提示
                else:
                    return f"{answer}\n\n_(基于历史经验，置信度: {confidence:.0%})_"
            
            return None
            
        except Exception as e:
            logger.debug(f"知识检索失败: {e}")
            return None
    
    def _expert_collaboration(self, intent: Intent, confidence: float) -> str:
        """调用外部模型进行结构化分析（外脑协作）"""
        
        # 选择专家（优先远程模型）
        expert = None
        if "remote_gpt4" in self.adapters:
            expert = self.adapters["remote_gpt4"]
        elif "deepseek-chat" in self.adapters:
            expert = self.adapters["deepseek-chat"]
        elif "deepcoder" in self.adapters:
            expert = self.adapters["deepcoder"]
        else:
            expert = next(iter(self.adapters.values()))
        
        logger.info(f"外脑协作专家: {expert.model_name}")
        
        # 构建分析请求
        prompt = f"""用户问题：{intent.raw_text}

当前系统理解：
- 意图类型：{intent.type}（置信度{confidence:.2f}）
- 系统整体置信度：{confidence:.2f}

【系统内部思考 - 不展示给用户】
请分析这个问题并给出建议：
1. 用户的真实意图是什么？
2. 这个问题可能存在哪些歧义？
3. 系统应该如何处理？

【输出要求】
直接给出答案，不要展示分析过程。
不要问用户更多问题，直接基于当前信息回答。
如果不确定，给出最可能的答案并说明可能的其他理解。"""
        
        try:
            response = expert.generate(prompt, task_type="analysis")
            
            if isinstance(response, tuple):
                response, _ = response
            
            # 存储专家分析（为未来逆向学习预留）
            self._store_expert_analysis(intent, response, confidence, expert.model_name)
            
            return response
            
        except Exception as e:
            logger.error(f"外脑协作失败: {e}")
            # 降级到普通生成
            return self._normal_generate(intent)
    
    def _store_expert_analysis(self, intent: Intent, analysis: str, confidence: float, expert_model: str):
        """存储专家分析（为逆向学习预留）"""
        try:
            conn = sqlite3.connect('data/experience_pool.db')
            conn.execute('''
                INSERT INTO experiences
                (intent_type, raw_input, plan, model_name, 
                 quality_score, user_feedback, success, 
                 response, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                intent.type,
                intent.raw_text,
                f"expert_collaboration:{expert_model}",
                expert_model,
                0,  # 待评估
                0,
                False,
                analysis,
                time.time()
            ))
            conn.commit()
            conn.close()
            logger.debug(f"已存储专家分析 (置信度: {confidence:.2f})")
        except Exception as e:
            logger.warning(f"存储专家分析失败: {e}")
    
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
            
            # 正确处理异步调用
            try:
                # 尝试获取运行中的事件循环
                loop = asyncio.get_running_loop()
                # 如果有运行中的循环，使用nest_asyncio
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    result = asyncio.run(_run_federated_call())
                except ImportError:
                    # nest_asyncio未安装，使用线程池执行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _run_federated_call())
                        result = future.result(timeout=60)
            except RuntimeError:
                # 没有运行中的事件循环，直接运行
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
    
    def _check_reflex_level(self, intent: Intent) -> Optional[str]:
        """【反射级】硬编码快速响应（最高优先级）
        
        Returns:
            拦截消息，None表示通过
        """
        try:
            from infrastructure.reflex_engine import reflex_engine
            
            reflex_context = {
                "user_input": intent.raw_text,
                "recent_failures": len(self.failure_history.get(intent.type, []))
            }
            
            try:
                import psutil
                reflex_context["memory_percent"] = psutil.virtual_memory().percent
            except:
                pass
            
            reflex_result = reflex_engine.check(reflex_context)
            if reflex_result:
                logger.warning(f"【反射级】触发拦截")
                return reflex_result
                
        except Exception as e:
            logger.debug(f"反射检查失败: {e}")
        
        return None
    
    def _infer_emotion(self, intent: Intent) -> Dict:
        """【情绪推断】理解用户状态
        
        Returns:
            情绪推断结果
        """
        try:
            from infrastructure.emotion_inferencer import emotion_inferencer
            
            emotion_result = emotion_inferencer.infer(
                intent.raw_text,
                {"recent_failures": len(self.failure_history.get(intent.type, []))}
            )
            
            if emotion_inferencer.should_simplify_response(emotion_result):
                logger.info(f"用户状态: {emotion_result['emotion']} (耐心: {emotion_result['patience']:.2f})")
            
            return emotion_result
            
        except Exception as e:
            logger.debug(f"情绪推断失败: {e}")
            return {"emotion": "neutral", "patience": 1.0}
    
    def _check_system_state(self) -> Optional[str]:
        """【系统状态检查】健康度+资源检查
        
        Returns:
            状态异常消息，None表示正常
        """
        # 健康度检查（只在严重情况下才拦截）
        try:
            from infrastructure.health_dashboard import health_dashboard
            mode = health_dashboard.mode
            # 只有在critical模式下才拦截
            if mode == "critical":
                logger.warning(f"系统健康度严重不足，当前模式: {mode}")
                return "系统状态不佳，正在自我修复中。部分功能可能受限。"
        except Exception as e:
            logger.debug(f"健康度检查失败: {e}")
        
        # 资源检查（放宽限制，只在极端情况下拦截）
        try:
            from infrastructure.charter_executor import charter_executor
            resource_check = charter_executor.check_resource_limits()
            
            # 只有在严重超限（多个资源同时超限）时才拦截
            violations = resource_check.get('violations', [])
            if len(violations) >= 2:  # 至少2个资源同时超限才拦截
                logger.warning(f"多个资源超限: {violations}")
                return "系统资源紧张，已暂缓处理。请稍后重试。"
        except Exception as e:
            logger.debug(f"资源检查失败: {e}")
        
        return None
    
    def _apply_five_layer_defense(self, intent: Intent) -> Optional[str]:
        """【五层防御机制】
        
        第1层: 工具优先调用
        第2层: 任务智能分解（在normal_flow中处理）
        第3层: 知识库检索
        第4层: 主动用户求助（在normal_flow异常中处理）
        第5层: 失败学习机制（在normal_flow异常中处理）
        
        Returns:
            防御层结果，None表示需要进入normal_flow
        """
        # 第1层：工具优先调用
        tool_result = self._try_tool_first(intent)
        if tool_result:
            logger.info(f"【第1层】工具调用成功")
            return tool_result
        
        # 第3层：知识库检索
        knowledge_result = self._try_knowledge_retrieval(intent)
        if knowledge_result:
            logger.info(f"【第3层】知识库命中")
            return knowledge_result
        
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
        if intent.type == "meta":
            logger.info("处理元认知问题")
            response = self._handle_meta_question(intent.raw_text)
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
        
        # 1. 置信度评估与外脑协作
        if response := self._try_expert_collaboration(intent):
            return
        
        # 2. 联邦调度流程
        if response := self._try_federation_flow(intent):
            return
        
        # 3. 向量检索复用
        if response := self._try_vector_reuse(intent):
            return
        
        # 4. 学习规则路由
        if response := self._try_rule_based_routing(intent):
            return
        
        # 5. 单模型降级
        self._single_model_fallback(intent)
    
    def _try_expert_collaboration(self, intent: Intent) -> Optional[str]:
        """尝试外脑协作（低置信度时）"""
        confidence = self._estimate_self_confidence(intent)
        
        if confidence < 0.6:
            logger.info(f"自我置信度低({confidence:.2f})，启用外脑协作模式")
            response = self._expert_collaboration(intent, confidence)
            bus.publish("plan_executed", response)
            return response
        
        return None
    
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
    
    def _try_vector_reuse(self, intent: Intent) -> Optional[str]:
        """尝试向量检索复用"""
        if not VECTOR_AVAILABLE:
            return None
        
        try:
            similar = vector_retriever.find_similar_plan(intent.raw_text, intent.type)
            if similar and similar.get('plan', {}).get('quality_score', 0) >= 70:
                logger.info(f"✓ 复用相似成功案例(相似度:{similar.get('similarity', 0):.2f})")
                response = similar.get('plan', {}).get('response', '')
                if response:
                    bus.publish("plan_executed", response)
                    return response
        except (KeyError, TypeError) as e:
            logger.debug(f"向量检索数据格式错误: {e}")
        except Exception as e:
            logger.error(f"向量检索未知错误: {type(e).__name__}: {e}")
        
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
    
    def _single_model_fallback(self, intent: Intent):
        """单模型降级处理"""
        # 原有的单模型逻辑
        # ...（保持原有代码）
        pass
        
        # 尝试并行调度（多模型联邦）
        parallel_enabled = config.get("parallel_scheduling.enabled", True)
        if parallel_enabled and len(self.adapters) >= 2:
            try:
                response = self._parallel_schedule(intent)
                if response:
                    bus.publish("plan_executed", response)
                    return
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning(f"并行调度网络错误，降级到单模型: {e}")
            except Exception as e:
                logger.error(f"并行调度未知错误: {type(e).__name__}: {e}")
        
        # 优先检查向量检索是否有相似成功案例
        if VECTOR_AVAILABLE:
            try:
                similar = vector_retriever.find_similar_plan(intent.raw_text, intent.type)
                if similar and similar.get('plan', {}).get('quality_score', 0) >= 70:
                    logger.info(f"✓ 复用相似成功案例(相似度:{similar.get('similarity', 0):.2f})")
                    response = similar.get('plan', {}).get('response', '')
                    if response:
                        bus.publish("plan_executed", response)
                        return
            except (KeyError, TypeError) as e:
                logger.debug(f"向量检索数据格式错误: {e}")
            except Exception as e:
                logger.error(f"向量检索未知错误: {type(e).__name__}: {e}")
        
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
            
            # 在线反思（新增）
            if quality < 40:
                try:
                    from infrastructure.online_reflector import online_reflector
                    online_reflector.reflect(
                        intent_type=intent.type,
                        raw_input=intent.raw_text,
                        model_name=model.model_name,
                        quality_score=quality,
                        response=response
                    )
                except Exception as e:
                    logger.debug(f"在线反思失败: {e}")
            
            # 记录到统计库 (新增)
            try:
                input_tokens = len(full_prompt.split())
                output_tokens = len(response.split())
                self.stats.record_call(
                    model_name=model.model_name,
                    task_type=intent.type,
                    duration=duration,
                    success=quality >= 50,
                    quality_score=quality,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
            except Exception as stats_error:
                logger.warning(f"统计记录失败: {stats_error}")
            
            # 触发反事实模拟（异步）
            try:
                import asyncio
                from infrastructure.counterfactual_simulator import counterfactual_simulator
                
                task_id = f"{intent.type}_{int(time.time())}"
                asyncio.create_task(
                    counterfactual_simulator.simulate_alternatives(
                        task_id=task_id,
                        actual_model=model.model_name,
                        actual_score=quality,
                        task_input=intent.raw_text,
                        task_type=intent.type,
                        adapters=self.adapters
                    )
                )
            except Exception as cf_error:
                logger.debug(f"反事实模拟触发失败: {cf_error}")
            
            # 更新能力矩阵
            self._update_capability_from_result(
                model.model_name,
                intent.type,
                quality / 100.0,
                success=True
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
                
                # 【第4层】主动向用户求助
                help_msg = self._request_user_help(intent, str(e))
                if help_msg:
                    bus.publish("plan_executed", help_msg)
                else:
                    bus.publish("plan_executed", error_msg)
                
                # 【第5层】失败学习机制
                self._trigger_failure_learning(intent, str(e))
    
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
            logger.debug(f"求助消息生成失败: {e}")
            return None
    
    def _trigger_failure_learning(self, intent: Intent, error: str):
        """【第5层防御】失败学习机制
        
        记录失败案例，触发归纳总结，生成学习规则。
        """
        try:
            from infrastructure.knowledge_injector import knowledge_injector
            
            # 记录失败（质量分为0）
            knowledge_injector.inject_knowledge(
                question=intent.raw_text,
                answer=f"[失败] {error}",
                source="failure_record",
                intent_type=intent.type,
                metadata={"error": error, "timestamp": datetime.now().isoformat()}
            )
            
            logger.info(f"【第5层防御】失败已记录，等待学习")
            
            # 触发归纳总结（如果有归纳器）
            try:
                from meta.induction import induction_scheduler
                induction_scheduler.trigger_induction()
            except:
                pass
            
            # 【新增】触发主动学习器
            try:
                from infrastructure.active_learner import active_learner
                active_learner.record_event("intent_failure", {
                    "intent": intent.type,
                    "query": intent.raw_text,
                    "error": error
                })
            except Exception as al_error:
                logger.debug(f"主动学习器触发失败: {al_error}")
            
        except Exception as e:
            logger.debug(f"失败学习触发失败: {e}")
    
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
                "raw_input": intent.raw_text,
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
        """
        logger.info("进入认知模式")
        
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
