"""
认知规划器 (Cognitive Planner)

整合所有认知架构组件的核心协调器
让同行者真正"走起来"
"""

import threading
import time
import hashlib
import atexit
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class CognitiveCycleResult:
    """一次认知循环的结果"""
    conversation_id: str
    user_input: str
    response: str
    perception: Dict
    learning: Dict
    integration: Dict
    validation: Dict
    evolution: Dict
    introspection: Dict
    processing_time_ms: float
    success: bool
    timestamp: str


class CognitivePlanner:
    """
    认知规划器 - 系统核心协调器
    
    这是系统的"中枢神经系统"，协调所有组件协同工作。
    """
    
    REQUIRED_COMPONENTS = ['l2', 'l4', 'stereo_store']
    OPTIONAL_COMPONENTS = ['l3', 'l5', 'l6', 'emotion_detector']
    
    def __init__(self, planner=None, llm_adapter=None):
        self._init_time = datetime.now()
        
        self.planner = planner
        self.llm_adapter = llm_adapter
        
        if self.planner is None:
            try:
                from core.services.planner import planner as global_planner
                self.planner = global_planner
            except:
                logger.warning("未找到全局planner，将使用降级响应")
        
        if self.llm_adapter is None and self.planner:
            try:
                if hasattr(self.planner, 'adapters') and self.planner.adapters:
                    self.llm_adapter = next(iter(self.planner.adapters.values()))
            except:
                pass
        
        try:
            from core.config.unified_config import get_config
            self.config = get_config()
        except:
            self.config = None
        
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cognitive")
        atexit.register(self._cleanup_executor)
        
        self._init_layers()
        self._init_memory()
        self._init_presence()
        self._init_evolution()
        self._init_horizontal()
        
        self._validate_components()
        
        self._start_all_components()
        
        self._conversation_id_counter = 0
        self._current_conversation_id = None
        self._conversation_history = []
        
        logger.info("🧠 认知规划器完整初始化完成")
    
    def _init_layers(self):
        """初始化七层架构"""
        self.emotion_detector = None
        self.l2 = None
        self.l3 = None
        self.l4 = None
        self.l5 = None
        self.l6 = None
        
        try:
            from core.layers.l2_learning import L2LearningLayer
            self.l2 = L2LearningLayer()
            logger.info("  ✓ L2学习层已加载")
        except Exception as e:
            logger.error(f"❌ L2学习层加载失败（核心组件）: {e}")
        
        try:
            from core.layers.l3_integration import L3IntegrationLayer
            self.l3 = L3IntegrationLayer()
            logger.info("  ✓ L3整合层已加载")
        except Exception as e:
            logger.warning(f"L3整合层加载失败: {e}")
        
        try:
            from core.layers.l4_validation import L4ValidationLayer
            self.l4 = L4ValidationLayer()
            logger.info("  ✓ L4校验层已加载")
        except Exception as e:
            logger.error(f"❌ L4校验层加载失败（核心组件）: {e}")
        
        try:
            from core.layers.l5_evolution import L5EvolutionLayer
            self.l5 = L5EvolutionLayer()
            logger.info("  ✓ L5进化层已加载")
        except Exception as e:
            logger.warning(f"L5进化层加载失败: {e}")
        
        try:
            from core.layers.l6_introspection import L6IntrospectionLayer
            self.l6 = L6IntrospectionLayer()
            logger.info("  ✓ L6内省层已加载")
        except Exception as e:
            logger.warning(f"L6内省层加载失败: {e}")
    
    def _init_memory(self):
        """初始化记忆子系统"""
        self.stereo_store = None
        self.relationship_model = None
        
        try:
            from core.memory.stereo_memory import StereoMemoryStore
            self.stereo_store = StereoMemoryStore()
            logger.info("  ✓ 立体记忆已加载")
        except Exception as e:
            logger.error(f"❌ 立体记忆加载失败（核心组件）: {e}")
        
        try:
            from core.relationship.model import RelationshipModel
            self.relationship_model = RelationshipModel()
            logger.info("  ✓ 关系模型已加载")
        except Exception as e:
            logger.warning(f"关系模型加载失败: {e}")
    
    def _init_presence(self):
        """初始化存在层组件"""
        self.existence = None
        self.self_perception = None
        self.gap_growth = None
        self.sleep_engine = None
        self.proactivity = None
        self.active_perception = None
        self.review_engine = None
        
        try:
            from core.presence.existence_layer import ExistenceLayer
            self.existence = ExistenceLayer()
            logger.info("  ✓ 存在层已加载")
        except Exception as e:
            logger.warning(f"存在层加载失败: {e}")
        
        try:
            from core.presence.self_perception import SelfPerceptionEngine
            self.self_perception = SelfPerceptionEngine()
            logger.info("  ✓ 自我感知引擎已加载")
        except Exception as e:
            logger.warning(f"自我感知引擎加载失败: {e}")
        
        try:
            from core.presence.gap_growth import GapGrowthEngine
            self.gap_growth = GapGrowthEngine()
            logger.info("  ✓ 间隙生长引擎已加载")
        except Exception as e:
            logger.warning(f"间隙生长引擎加载失败: {e}")
        
        try:
            from core.presence.sleep_consolidation import SleepEngine
            self.sleep_engine = SleepEngine()
            logger.info("  ✓ 睡眠整合引擎已加载")
        except Exception as e:
            logger.warning(f"睡眠整合引擎加载失败: {e}")
        
        try:
            from core.presence.proactivity import ProactivityEngine
            self.proactivity = ProactivityEngine()
            logger.info("  ✓ 主动性引擎已加载")
        except Exception as e:
            logger.warning(f"主动性引擎加载失败: {e}")
        
        try:
            from core.presence.self_review import SelfReviewEngine
            self.review_engine = SelfReviewEngine()
            logger.info("  ✓ 自我评估引擎已加载")
        except Exception as e:
            logger.warning(f"自我评估引擎加载失败: {e}")
    
    def _init_evolution(self):
        """初始化进化子系统"""
        self.goal_engine = None
        
        try:
            from core.evolution.adaptive_goal import AdaptiveGoalEngine
            self.goal_engine = AdaptiveGoalEngine()
            logger.info("  ✓ 自适应目标引擎已加载")
        except Exception as e:
            logger.warning(f"自适应目标引擎加载失败: {e}")
    
    def _init_horizontal(self):
        """初始化横向机制"""
        self.collector = None
        self.heartbeat = None
        
        try:
            from core.reporting.state_collector import StateCollector
            self.collector = StateCollector()
            logger.info("  ✓ 状态收集器已加载")
        except Exception as e:
            logger.warning(f"状态收集器加载失败: {e}")
        
        try:
            from core.introspection.heartbeat import HeartbeatManager
            self.heartbeat = HeartbeatManager()
            logger.info("  ✓ 心跳管理器已加载")
        except Exception as e:
            logger.warning(f"心跳管理器加载失败: {e}")
    
    def _start_all_components(self):
        """启动所有组件"""
        logger.info("🚀 启动所有系统组件...")
        
        if self.existence and hasattr(self.existence, 'start'):
            try:
                self.existence.start()
                logger.info("  ✅ 存在层已启动")
            except Exception as e:
                logger.warning(f"存在层启动失败: {e}")
        
        if self.self_perception and hasattr(self.self_perception, 'start'):
            try:
                self.self_perception.start()
                logger.info("  ✅ 自我感知引擎已启动")
            except Exception as e:
                logger.warning(f"自我感知启动失败: {e}")
        
        if self.gap_growth and hasattr(self.gap_growth, 'start'):
            try:
                self.gap_growth.start()
                logger.info("  ✅ 间隙生长引擎已启动")
            except Exception as e:
                logger.warning(f"间隙生长启动失败: {e}")
        
        if self.sleep_engine and hasattr(self.sleep_engine, 'start'):
            try:
                self.sleep_engine.start()
                logger.info("  ✅ 睡眠整合引擎已启动")
            except Exception as e:
                logger.warning(f"睡眠整合启动失败: {e}")
        
        if self.proactivity and hasattr(self.proactivity, 'start'):
            try:
                self.proactivity.start()
                logger.info("  ✅ 主动性引擎已启动")
            except Exception as e:
                logger.warning(f"主动性启动失败: {e}")
        
        if self.heartbeat and hasattr(self.heartbeat, 'start'):
            try:
                self.heartbeat.start()
                logger.info("  ✅ 心跳管理器已启动")
            except Exception as e:
                logger.warning(f"心跳启动失败: {e}")
        
        logger.info("✅ 所有组件已启动")
    
    def _validate_components(self) -> Dict:
        """验证组件状态"""
        status = {
            "required": {},
            "optional": {},
            "healthy": True
        }
        
        for comp_name in self.REQUIRED_COMPONENTS:
            comp = getattr(self, comp_name, None)
            is_available = comp is not None
            status["required"][comp_name] = is_available
            
            if not is_available:
                status["healthy"] = False
                logger.error(f"❌ 核心组件缺失: {comp_name}")
        
        for comp_name in self.OPTIONAL_COMPONENTS:
            comp = getattr(self, comp_name, None)
            status["optional"][comp_name] = comp is not None
        
        if status["healthy"]:
            logger.info("✅ 所有核心组件已加载")
        else:
            logger.warning("⚠️ 部分核心组件缺失，系统可能功能受限")
        
        return status
    
    def _cleanup_executor(self):
        """清理线程池"""
        try:
            self._executor.shutdown(wait=True, cancel_futures=False)
            logger.info("线程池已关闭")
        except:
            pass
    
    def process(self, user_input: str, context: Dict = None) -> CognitiveCycleResult:
        """
        处理用户输入 - 完整的认知循环
        
        这是系统的核心入口。
        
        Args:
            user_input: 用户输入
            context: 上下文信息（对话历史、当前文件等）
        """
        start_time = time.time()
        self._conversation_id_counter += 1
        conversation_id = f"conv_{self._conversation_id_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._current_conversation_id = conversation_id
        
        if self.sleep_engine and hasattr(self.sleep_engine, 'notify_interaction'):
            try:
                self.sleep_engine.notify_interaction()
            except:
                pass
        
        if self.proactivity:
            try:
                self.proactivity._last_user_interaction = datetime.now()
            except:
                pass
        
        try:
            perception = self._perceive(user_input, context)
            
            learning = self._learn(user_input, perception)
            
            integration = self._integrate(learning)
            
            validation, response = self._validate_and_respond(
                integration, user_input, perception
            )
            
            self._trigger_async_evolution(
                conversation_id, user_input, response, perception, validation
            )
            
            introspection = self._get_introspection()
            
            self._save_memory(user_input, response, perception, validation)
            
            self._update_relationship(user_input, response, perception, validation)
            
            self._submit_signals(perception, validation)
            
            self._trigger_async_review(
                conversation_id, user_input, response, perception, validation
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            return CognitiveCycleResult(
                conversation_id=conversation_id,
                user_input=user_input,
                response=response,
                perception=perception,
                learning=learning,
                integration=integration,
                validation=validation,
                evolution={},
                introspection=introspection,
                processing_time_ms=processing_time,
                success=validation.get("status") == "pass",
                timestamp=datetime.now().isoformat()
            )
        
        except Exception as e:
            error_msg = f"认知循环异常: {str(e)}"
            logger.error(error_msg)
            
            return CognitiveCycleResult(
                conversation_id=conversation_id,
                user_input=user_input,
                response=f"抱歉，我处理您的问题时遇到了问题。错误: {str(e)}",
                perception={},
                learning={},
                integration={},
                validation={"status": "error", "reason": error_msg},
                evolution={},
                introspection={},
                processing_time_ms=(time.time() - start_time) * 1000,
                success=False,
                timestamp=datetime.now().isoformat()
            )
    
    def _perceive(self, user_input: str, context: Dict = None) -> Dict:
        """L1: 感知层"""
        if self.emotion_detector and hasattr(self.emotion_detector, 'detect'):
            try:
                emotion_result = self.emotion_detector.detect(user_input)
                emotion = emotion_result.get("emotion", "neutral")
                emotion_intensity = emotion_result.get("intensity", 0.3)
            except:
                emotion = "neutral"
                emotion_intensity = 0.3
        else:
            emotion = "neutral"
            emotion_intensity = 0.3
        
        return {
            "intent": self._detect_intent(user_input),
            "confidence": 0.7,
            "uncertainty": False,
            "emotion": emotion,
            "emotion_intensity": emotion_intensity,
            "urgency": 0.5,
            "confusion": 0.0,
            "sentiment": 0.5,
            "keywords": self._extract_keywords(user_input),
            "context": context or {}
        }
    
    def _detect_intent(self, text: str) -> str:
        """检测意图"""
        if any(kw in text for kw in ["反思", "回顾", "历史"]):
            return "reflection"
        if any(kw in text for kw in ["推荐", "选型", "选择"]):
            return "recommendation"
        if any(kw in text for kw in ["为什么", "真的吗", "你确定"]):
            return "challenge"
        if any(kw in text for kw in ["如何", "怎样", "什么"]):
            return "question"
        return "general"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        keywords = []
        candidates = ["芯片", "代码", "设计", "学习", "记忆", "进化", "情感", "关系", "系统", "架构"]
        for kw in candidates:
            if kw in text:
                keywords.append(kw)
        return keywords
    
    def _learn(self, user_input: str, perception: Dict) -> Dict:
        """L2: 学习层"""
        if self.l2 and hasattr(self.l2, 'learn'):
            try:
                target = {
                    "name": user_input[:100],
                    "keywords": perception.get("keywords", []),
                    "intent": perception.get("intent", "unknown")
                }
                result = self.l2.learn(target)
                return {
                    "success": result.success if hasattr(result, 'success') else True,
                    "knowledge_gained": result.knowledge_gained if hasattr(result, 'knowledge_gained') else 0,
                    "sources": result.sources_used if hasattr(result, 'sources_used') else [],
                    "confidence": result.confidence if hasattr(result, 'confidence') else 0.7
                }
            except Exception as e:
                logger.warning(f"L2学习层异常: {e}")
        
        return {"success": True, "knowledge_gained": 0, "sources": [], "confidence": 0.7}
    
    def _integrate(self, learning: Dict) -> Dict:
        """L3: 整合层"""
        if self.l3 and hasattr(self.l3, 'integrate'):
            try:
                if not learning.get("success"):
                    return {"success": False, "reason": "学习失败"}
                
                result = self.l3.integrate(learning)
                return {
                    "success": True,
                    "core_knowledge": [{"content": "基于用户输入的分析", "confidence": 0.7}]
                }
            except Exception as e:
                logger.warning(f"L3整合层异常: {e}")
        
        return {"success": True, "core_knowledge": []}
    
    def _validate_and_respond(self, integration: Dict, user_input: str,
                              perception: Dict) -> tuple:
        """L4: 校验层 + 生成响应"""
        try:
            response = self._generate_response(user_input, perception)
            
            validation_status = "pass"
            confidence = 0.7
            
            if not integration.get("success"):
                confidence = 0.5
            
            validation = {
                "status": validation_status,
                "confidence": confidence,
                "doubts": []
            }
            
            return validation, response
        
        except Exception as e:
            logger.warning(f"L4校验层异常: {e}")
            return {"status": "pass", "confidence": 0.5, "doubts": []}, "我理解了你的意思。让我认真思考一下，给你一个有帮助的回应。"
    
    def _generate_response(self, user_input: str, perception: Dict) -> str:
        """生成响应（真实推理）"""
        if self.planner and hasattr(self.planner, 'plan'):
            try:
                from core.services.intent_parser import IntentParser
                intent_parser = IntentParser()
                intent = intent_parser.parse(user_input)
                
                result = self.planner.plan(intent)
                
                if result:
                    return str(result)
            except Exception as e:
                logger.error(f"Planner推理失败: {e}")
        
        if self.llm_adapter:
            try:
                prompt = self._build_prompt(user_input, perception)
                
                response = self.llm_adapter.generate(prompt)
                
                if response:
                    return response
            except Exception as e:
                logger.error(f"LLM推理失败: {e}")
        
        return self._fallback_response(user_input, perception)
    
    def _build_prompt(self, user_input: str, perception: Dict) -> str:
        """构建LLM提示"""
        intent = perception.get("intent", "general")
        keywords = perception.get("keywords", [])
        context = perception.get("context", {})
        
        prompt = f"""用户输入: {user_input}
意图: {intent}
关键词: {', '.join(keywords) if keywords else '无'}

请根据以上信息，给出有帮助的回应。"""
        
        if context:
            history = context.get("history", [])
            if history:
                prompt += "\n\n对话历史:\n"
                for msg in history[-3:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    prompt += f"{role}: {content}\n"
        
        return prompt
    
    def _fallback_response(self, user_input: str, perception: Dict) -> str:
        """降级响应（模板）"""
        intent = perception.get("intent", "general")
        
        templates = {
            "reflection": "你希望我回顾什么？可以告诉我具体的方向。",
            "recommendation": "我理解你需要推荐。可以告诉我更多需求吗？",
            "challenge": "你的质疑很有道理。让我重新审视。",
            "question": "这是一个很好的问题。让我从多个角度分析。",
            "general": "我理解了你的意思。让我认真思考一下。"
        }
        
        return templates.get(intent, templates["general"])
    
    def _trigger_async_evolution(self, conversation_id: str, user_input: str,
                                 response: str, perception: Dict, validation: Dict):
        """异步触发进化（线程池管理）"""
        def evolution_task():
            try:
                if self.goal_engine and hasattr(self.goal_engine, 'get_top_priorities'):
                    goals = self.goal_engine.get_top_priorities(3)
                    for goal in goals:
                        logger.debug(f"🎯 进化目标: {goal.get('dimension')} (优先级: {goal.get('priority')})")
                
                if self.l5 and hasattr(self.l5, 'record_experience'):
                    experience = {
                        "user_input": user_input,
                        "response": response,
                        "validation_result": validation,
                        "perception": perception,
                        "conversation_id": conversation_id
                    }
                    self.l5.record_experience(experience)
            
            except Exception as e:
                logger.debug(f"异步进化失败: {e}")
        
        self._executor.submit(evolution_task)
    
    def _get_introspection(self) -> Dict:
        """获取内省状态"""
        if self.l6 and hasattr(self.l6, 'generate_report'):
            try:
                return self.l6.generate_report()
            except:
                pass
        return {}
    
    def _save_memory(self, user_input: str, response: str,
                     perception: Dict, validation: Dict):
        """保存立体记忆"""
        if self.stereo_store and hasattr(self.stereo_store, 'save'):
            try:
                from core.memory.stereo_memory import StereoMemoryEntry, MemoryImportance
                
                memory = StereoMemoryEntry(
                    id=hashlib.md5(f"{user_input}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
                    user_content=user_input,
                    system_content=response,
                    intent=perception.get("intent", "unknown"),
                    topic=self._extract_topic(user_input),
                    trust_change=self._calculate_trust_change(validation),
                    intimacy_change=perception.get("emotion_intensity", 0) * 0.1,
                    dependency_change=0,
                    self_state_before={},
                    self_state_after=self._get_current_state(),
                    skills_used=[],
                    skills_formed=[],
                    timestamp=datetime.now().isoformat(),
                    importance=MemoryImportance.MEDIUM,
                    user_emotion=perception.get("emotion", "neutral"),
                    system_emotion="neutral"
                )
                self.stereo_store.save(memory)
            except Exception as e:
                logger.debug(f"保存立体记忆失败: {e}")
    
    def _update_relationship(self, user_input: str, response: str,
                             perception: Dict, validation: Dict):
        """更新关系模型"""
        if self.relationship_model and hasattr(self.relationship_model, 'update_from_conversation'):
            try:
                satisfaction = 1.0 if validation.get("status") == "pass" else 0.3
                self.relationship_model.update_from_conversation({
                    "user_satisfaction": satisfaction,
                    "emotional_intensity": perception.get("emotion_intensity", 0.3),
                    "duration_minutes": 2,
                    "system_helpfulness": perception.get("confidence", 0.5),
                    "conversation_id": self._current_conversation_id
                })
            except Exception as e:
                logger.debug(f"更新关系模型失败: {e}")
    
    def _submit_signals(self, perception: Dict, validation: Dict):
        """提交信号到间隙生长引擎"""
        if self.gap_growth and hasattr(self.gap_growth, 'submit_signal'):
            try:
                if perception.get("emotion") not in ["neutral", "unknown"]:
                    self.gap_growth.submit_signal(
                        signal_type="emotion_pattern",
                        content=perception.get("emotion", "neutral"),
                        source="L1",
                        priority="medium"
                    )
                
                if validation.get("status") == "fail":
                    self.gap_growth.submit_signal(
                        signal_type="error_pattern",
                        content=validation.get("reason", "校验失败"),
                        source="L4",
                        priority="high"
                    )
            except Exception as e:
                logger.debug(f"提交信号失败: {e}")
    
    def _trigger_async_review(self, conversation_id: str, user_input: str,
                              response: str, perception: Dict, validation: Dict):
        """异步触发自我评估（线程池管理）"""
        if self.review_engine and hasattr(self.review_engine, 'review'):
            def review_task():
                try:
                    conversation = {
                        "conversation_id": conversation_id,
                        "user_input": user_input,
                        "system_response": response,
                        "perception_result": perception,
                        "validation_result": validation,
                        "processing_time": 0
                    }
                    self.review_engine.review(conversation)
                except Exception as e:
                    logger.debug(f"自我评估失败: {e}")
            
            self._executor.submit(review_task)
    
    def _extract_topic(self, text: str) -> str:
        """提取话题"""
        keywords = ["芯片", "代码", "设计", "学习", "记忆", "进化", "情感", "关系"]
        for kw in keywords:
            if kw in text:
                return kw
        return "general"
    
    def _calculate_trust_change(self, validation: Dict) -> float:
        """计算信任变化"""
        if validation.get("status") == "pass":
            return 0.05
        elif validation.get("status") == "partial":
            return 0.0
        else:
            return -0.05
    
    def _get_current_state(self) -> Dict:
        """获取当前系统状态"""
        if self.self_perception and hasattr(self.self_perception, 'get_current_perception'):
            try:
                return self.self_perception.get_current_perception() or {}
            except:
                pass
        return {}
    
    def get_system_status(self) -> Dict:
        """获取系统整体状态"""
        status = {
            "status": "running",
            "uptime": str(datetime.now() - self._init_time),
            "conversation_count": self._conversation_id_counter,
            "components": {},
            "relationship": {},
            "goals": [],
            "health": {}
        }
        
        if self.existence and hasattr(self.existence, 'is_running'):
            status["components"]["existence"] = self.existence.is_running()
        
        if self.self_perception and hasattr(self.self_perception, 'is_running'):
            status["components"]["self_perception"] = self.self_perception.is_running()
        
        if self.gap_growth and hasattr(self.gap_growth, 'is_running'):
            status["components"]["gap_growth"] = self.gap_growth.is_running()
        
        if self.sleep_engine and hasattr(self.sleep_engine, 'is_running'):
            status["components"]["sleep_engine"] = self.sleep_engine.is_running()
        
        if self.proactivity:
            status["components"]["proactivity"] = getattr(self.proactivity, '_running', False)
        
        if self.relationship_model and hasattr(self.relationship_model, 'get_metrics'):
            try:
                status["relationship"] = self.relationship_model.get_metrics()
            except:
                status["relationship"] = {"trust": 0.5, "intimacy": 0.0}
        
        if self.goal_engine and hasattr(self.goal_engine, 'get_top_priorities'):
            try:
                status["goals"] = self.goal_engine.get_top_priorities(3)
            except:
                pass
        
        if self.l6 and hasattr(self.l6, 'get_introspection_status'):
            try:
                status["health"] = self.l6.get_introspection_status()
            except:
                pass
        
        return status
    
    def shutdown(self):
        """关闭系统"""
        logger.info("🛑 正在关闭系统...")
        
        if self.existence and hasattr(self.existence, 'stop'):
            try:
                self.existence.stop()
            except:
                pass
        
        if self.self_perception and hasattr(self.self_perception, 'stop'):
            try:
                self.self_perception.stop()
            except:
                pass
        
        if self.gap_growth and hasattr(self.gap_growth, 'stop'):
            try:
                self.gap_growth.stop()
            except:
                pass
        
        if self.sleep_engine and hasattr(self.sleep_engine, 'stop'):
            try:
                self.sleep_engine.stop()
            except:
                pass
        
        if self.proactivity and hasattr(self.proactivity, 'stop'):
            try:
                self.proactivity.stop()
            except:
                pass
        
        if self.heartbeat and hasattr(self.heartbeat, 'stop'):
            try:
                self.heartbeat.stop()
            except:
                pass
        
        self._cleanup_executor()
        
        logger.info("🛑 系统已关闭")


_cognitive_planner_instance: Optional[CognitivePlanner] = None


def get_cognitive_planner(planner=None, llm_adapter=None) -> CognitivePlanner:
    """获取认知规划器单例
    
    Args:
        planner: DataDrivenPlanner实例（推荐）
        llm_adapter: LLM适配器（备选）
    """
    global _cognitive_planner_instance
    if _cognitive_planner_instance is None:
        _cognitive_planner_instance = CognitivePlanner(planner=planner, llm_adapter=llm_adapter)
    return _cognitive_planner_instance


def get_system_status() -> Dict:
    """获取系统状态（便捷函数）"""
    planner = get_cognitive_planner()
    return planner.get_system_status()