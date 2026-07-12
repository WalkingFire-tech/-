"""
系统编排器 (System Orchestrator)

整合所有层与横向机制的中央协调器
让系统成为一个有机整体，而非松散组件的堆砌
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio
import threading
import time
import json
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SystemState(Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    IDLE = "idle"
    LOW_POWER = "low_power"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class SystemMetrics:
    """系统级指标"""
    uptime_seconds: float = 0.0
    total_interactions: int = 0
    successful_interactions: int = 0
    learning_events: int = 0
    evolution_events: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_layers: int = 0
    health_score: float = 1.0
    last_activity: datetime = None


@dataclass
class LayerStatus:
    """层状态"""
    name: str
    healthy: bool = True
    active: bool = False
    last_activity: datetime = None
    error_count: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class SystemOrchestrator:
    """
    系统编排器
    
    职责：
    1. 整合所有层（L2-L6 + 存在层）
    2. 协调七大核心机制
    3. 管理认知循环
    4. 统一资源管理
    5. 提供系统级API
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.state = SystemState.INITIALIZING
        self.metrics = SystemMetrics()
        self.metrics.last_activity = datetime.now()
        
        self.layers: Dict[str, Any] = {}
        self.mechanisms: Dict[str, Any] = {}
        self.layer_status: Dict[str, LayerStatus] = {}
        
        self._init_layers()
        self._init_mechanisms()
        self._init_horizontal_mechanisms()
        
        self.running = False
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._orchestration_thread: Optional[threading.Thread] = None
        
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.state_change_callbacks: List[Callable] = []
        
        self.persistence_dir = Path(self.config.get("persistence_dir", "data/orchestrator"))
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("🎯 系统编排器已初始化")
    
    def _init_layers(self):
        """初始化所有层"""
        try:
            from core.layers.l2_learning import L2LearningLayer
            self.layers["l2"] = L2LearningLayer()
            self.layer_status["l2"] = LayerStatus(name="L2学习层")
            logger.info("✓ L2学习层已加载")
        except Exception as e:
            logger.warning(f"L2学习层加载失败: {e}")
        
        try:
            from core.layers.l3_integration import L3IntegrationLayer
            self.layers["l3"] = L3IntegrationLayer()
            self.layer_status["l3"] = LayerStatus(name="L3整合层")
            logger.info("✓ L3整合层已加载")
        except Exception as e:
            logger.warning(f"L3整合层加载失败: {e}")
        
        try:
            from core.layers.l4_validation import L4ValidationLayer
            self.layers["l4"] = L4ValidationLayer()
            self.layer_status["l4"] = LayerStatus(name="L4校验层")
            logger.info("✓ L4校验层已加载")
        except Exception as e:
            logger.warning(f"L4校验层加载失败: {e}")
        
        try:
            from core.layers.l5_evolution import L5EvolutionLayer
            self.layers["l5"] = L5EvolutionLayer()
            self.layer_status["l5"] = LayerStatus(name="L5进化层")
            logger.info("✓ L5进化层已加载")
        except Exception as e:
            logger.warning(f"L5进化层加载失败: {e}")
        
        try:
            from core.layers.l6_introspection import L6IntrospectionLayer
            self.layers["l6"] = L6IntrospectionLayer()
            self.layer_status["l6"] = LayerStatus(name="L6内省层")
            logger.info("✓ L6内省层已加载")
        except Exception as e:
            logger.warning(f"L6内省层加载失败: {e}")
        
        try:
            from core.presence.existence_layer import ExistenceLayer
            self.layers["existence"] = ExistenceLayer()
            self.layer_status["existence"] = LayerStatus(name="存在层")
            logger.info("✓ 存在层已加载")
        except Exception as e:
            logger.warning(f"存在层加载失败: {e}")
        
        self.metrics.active_layers = len(self.layers)
    
    def _init_mechanisms(self):
        """初始化七大核心机制"""
        try:
            from core.learning.incremental_perception import IncrementalPerception
            self.mechanisms["incremental_perception"] = IncrementalPerception()
            logger.info("✓ 增量感知学习已加载")
        except Exception as e:
            logger.warning(f"增量感知学习加载失败: {e}")
        
        try:
            from core.learning.feedback_loop import LearningFeedbackLoop
            self.mechanisms["feedback_loop"] = LearningFeedbackLoop()
            logger.info("✓ 经验反馈回路已加载")
        except Exception as e:
            logger.warning(f"经验反馈回路加载失败: {e}")
        
        try:
            from core.learning.error_alchemy import ErrorAlchemy
            self.mechanisms["error_alchemy"] = ErrorAlchemy()
            logger.info("✓ 失败的炼金术已加载")
        except Exception as e:
            logger.warning(f"失败的炼金术加载失败: {e}")
        
        try:
            from core.learning.tool_builder import ToolSelfBuilder
            self.mechanisms["tool_builder"] = ToolSelfBuilder()
            logger.info("✓ 工具自我构建已加载")
        except Exception as e:
            logger.warning(f"工具自我构建加载失败: {e}")
        
        try:
            from core.learning.knowledge_weaver import KnowledgeWeaver
            self.mechanisms["knowledge_weaver"] = KnowledgeWeaver()
            logger.info("✓ 知识网络编织已加载")
        except Exception as e:
            logger.warning(f"知识网络编织加载失败: {e}")
        
        try:
            from core.learning.rhythm_controller import CognitiveRhythmController
            self.mechanisms["rhythm_controller"] = CognitiveRhythmController()
            logger.info("✓ 认知节奏控制器已加载")
        except Exception as e:
            logger.warning(f"认知节奏控制器加载失败: {e}")
        
        try:
            from core.learning.meta_learning import MetaLearner
            self.mechanisms["meta_learner"] = MetaLearner()
            logger.info("✓ 元学习策略优化已加载")
        except Exception as e:
            logger.warning(f"元学习策略优化加载失败: {e}")
    
    def _init_horizontal_mechanisms(self):
        """初始化横向贯穿机制"""
        try:
            from core.reporting.state_collector import StateCollector
            self.mechanisms["state_collector"] = StateCollector()
            logger.info("✓ 状态收集器已加载")
        except Exception as e:
            logger.warning(f"状态收集器加载失败: {e}")
        
        try:
            from core.introspection.heartbeat import HeartbeatManager
            self.mechanisms["heartbeat"] = HeartbeatManager()
            logger.info("✓ 心跳管理器已加载")
        except Exception as e:
            logger.warning(f"心跳管理器加载失败: {e}")
        
        try:
            from core.cognitive_loop import CognitiveLoop
            self.mechanisms["cognitive_loop"] = CognitiveLoop()
            logger.info("✓ 认知循环已加载")
        except Exception as e:
            logger.warning(f"认知循环加载失败: {e}")
    
    def start(self):
        """启动系统"""
        if self.running:
            logger.warning("系统已在运行")
            return
        
        logger.info("🚀 启动系统编排器...")
        self.running = True
        self.state = SystemState.READY
        
        for name, layer in self.layers.items():
            try:
                if hasattr(layer, 'start'):
                    layer.start()
                self.layer_status[name].active = True
                self.layer_status[name].last_activity = datetime.now()
            except Exception as e:
                logger.error(f"启动层 {name} 失败: {e}")
                self.layer_status[name].healthy = False
                self.layer_status[name].error_count += 1
        
        if "heartbeat" in self.mechanisms:
            try:
                self.mechanisms["heartbeat"].start()
            except Exception as e:
                logger.warning(f"心跳管理器启动失败: {e}")
        
        if "existence" in self.layers:
            try:
                self.layers["existence"].start()
            except Exception as e:
                logger.warning(f"存在层启动失败: {e}")
        
        def orchestration_loop():
            while self.running:
                try:
                    self._orchestration_tick()
                    time.sleep(1.0)
                except Exception as e:
                    logger.error(f"编排循环错误: {e}")
        
        self._orchestration_thread = threading.Thread(
            target=orchestration_loop,
            daemon=True,
            name="OrchestrationLoop"
        )
        self._orchestration_thread.start()
        
        self.state = SystemState.ACTIVE
        logger.info("✅ 系统编排器已启动")
    
    def stop(self):
        """停止系统"""
        if not self.running:
            return
        
        logger.info("🛑 停止系统编排器...")
        self.state = SystemState.SHUTTING_DOWN
        self.running = False
        
        for name, layer in self.layers.items():
            try:
                if hasattr(layer, 'stop'):
                    layer.stop()
                self.layer_status[name].active = False
            except Exception as e:
                logger.error(f"停止层 {name} 失败: {e}")
        
        if "heartbeat" in self.mechanisms:
            try:
                self.mechanisms["heartbeat"].stop()
            except Exception:
                pass
        
        if self._orchestration_thread:
            self._orchestration_thread.join(timeout=5.0)
        
        self._save_state()
        logger.info("✅ 系统编排器已停止")
    
    def _orchestration_tick(self):
        """编排循环的单次执行"""
        self.metrics.uptime_seconds += 1.0
        
        self._check_layer_health()
        
        self._collect_metrics()
        
        if self.metrics.uptime_seconds % 60 == 0:
            self._save_state()
    
    def _check_layer_health(self):
        """检查各层健康状态"""
        healthy_count = 0
        for name, status in self.layer_status.items():
            if status.healthy and status.active:
                healthy_count += 1
        
        if self.metrics.active_layers > 0:
            self.metrics.health_score = healthy_count / self.metrics.active_layers
        else:
            self.metrics.health_score = 0.0
    
    def _collect_metrics(self):
        """收集系统指标"""
        try:
            import psutil
            process = psutil.Process()
            self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.metrics.cpu_usage_percent = process.cpu_percent(interval=0.1)
        except Exception:
            pass
        
        if "state_collector" in self.mechanisms:
            try:
                collector = self.mechanisms["state_collector"]
                if hasattr(collector, 'get_all_states'):
                    states = collector.get_all_states()
                    for layer_name, state in states.items():
                        if layer_name in self.layer_status:
                            self.layer_status[layer_name].metrics = state
            except Exception:
                pass
    
    def _save_state(self):
        """保存系统状态"""
        try:
            state_data = {
                "timestamp": datetime.now().isoformat(),
                "state": self.state.value,
                "metrics": {
                    "uptime_seconds": self.metrics.uptime_seconds,
                    "total_interactions": self.metrics.total_interactions,
                    "successful_interactions": self.metrics.successful_interactions,
                    "learning_events": self.metrics.learning_events,
                    "evolution_events": self.metrics.evolution_events,
                    "health_score": self.metrics.health_score,
                },
                "layers": {
                    name: {
                        "healthy": status.healthy,
                        "active": status.active,
                        "error_count": status.error_count,
                    }
                    for name, status in self.layer_status.items()
                }
            }
            
            state_file = self.persistence_dir / "system_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存状态失败: {e}")
    
    async def process_input(self, input_data: Any) -> Dict[str, Any]:
        """
        处理输入 - 统一入口
        
        流程：
        1. 存在层感知
        2. L2学习层接收
        3. L3整合层整合
        4. L4校验层验证
        5. L5进化层进化
        6. L6内省层反思
        """
        self.metrics.total_interactions += 1
        self.metrics.last_activity = datetime.now()
        
        result = {
            "input": input_data,
            "layers": {},
            "mechanisms": {},
            "success": False,
            "confidence": 0.0,
        }
        
        try:
            if "existence" in self.layers:
                existence = self.layers["existence"]
                if hasattr(existence, 'perceive'):
                    existence_result = existence.perceive(input_data)
                    result["layers"]["existence"] = existence_result
            
            if "l2" in self.layers:
                l2 = self.layers["l2"]
                if hasattr(l2, 'learn'):
                    l2_result = l2.learn(input_data)
                    result["layers"]["l2"] = l2_result
                    self.metrics.learning_events += 1
            
            if "l3" in self.layers:
                l3 = self.layers["l3"]
                if hasattr(l3, 'integrate'):
                    l3_result = l3.integrate(result["layers"].get("l2", {}))
                    result["layers"]["l3"] = l3_result
            
            if "l4" in self.layers:
                l4 = self.layers["l4"]
                if hasattr(l4, 'validate'):
                    l4_result = l4.validate(result["layers"].get("l3", {}))
                    result["layers"]["l4"] = l4_result
                    result["confidence"] = l4_result.get("confidence", 0.0)
            
            if "l5" in self.layers:
                l5 = self.layers["l5"]
                if hasattr(l5, 'evolve'):
                    l5_result = l5.evolve(result["layers"].get("l4", {}))
                    result["layers"]["l5"] = l5_result
                    self.metrics.evolution_events += 1
            
            if "l6" in self.layers:
                l6 = self.layers["l6"]
                if hasattr(l6, 'introspect'):
                    l6_result = l6.introspect(result["layers"])
                    result["layers"]["l6"] = l6_result
            
            result["success"] = True
            self.metrics.successful_interactions += 1
            
        except Exception as e:
            logger.error(f"处理输入失败: {e}")
            result["error"] = str(e)
            
            if "error_alchemy" in self.mechanisms:
                try:
                    self.mechanisms["error_alchemy"].transform_error(e, context=input_data)
                except Exception:
                    pass
        
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "state": self.state.value,
            "running": self.running,
            "uptime_seconds": self.metrics.uptime_seconds,
            "health_score": self.metrics.health_score,
            "total_interactions": self.metrics.total_interactions,
            "successful_interactions": self.metrics.successful_interactions,
            "learning_events": self.metrics.learning_events,
            "evolution_events": self.metrics.evolution_events,
            "memory_usage_mb": self.metrics.memory_usage_mb,
            "cpu_usage_percent": self.metrics.cpu_usage_percent,
            "layers": {
                name: {
                    "healthy": status.healthy,
                    "active": status.active,
                    "error_count": status.error_count,
                }
                for name, status in self.layer_status.items()
            },
            "mechanisms": list(self.mechanisms.keys()),
        }
    
    def trigger_learning(self, topic: str, priority: str = "normal") -> Dict[str, Any]:
        """触发学习任务"""
        result = {"topic": topic, "priority": priority, "success": False}
        
        try:
            if "incremental_perception" in self.mechanisms:
                from core.learning.incremental_perception import Signal, SignalType
                signal = Signal(
                    type=SignalType.KNOWLEDGE_GAP,
                    content=topic,
                    metadata={"priority": priority}
                )
                perception_result = self.mechanisms["incremental_perception"].perceive(signal)
                result["perception"] = perception_result
            
            if "l2" in self.layers:
                l2_result = self.layers["l2"].learn(topic)
                result["l2"] = l2_result
                self.metrics.learning_events += 1
            
            result["success"] = True
            logger.info(f"✓ 学习任务已触发: {topic}")
            
        except Exception as e:
            logger.error(f"学习任务失败: {e}")
            result["error"] = str(e)
        
        return result
    
    def trigger_evolution(self, focus: str = "accuracy") -> Dict[str, Any]:
        """触发进化"""
        result = {"focus": focus, "success": False}
        
        try:
            if "l5" in self.layers:
                l5_result = self.layers["l5"].evolve({"focus": focus})
                result["l5"] = l5_result
                self.metrics.evolution_events += 1
            
            if "meta_learner" in self.mechanisms:
                from core.learning.meta_learning import EvaluationMetric
                metric_map = {
                    "accuracy": EvaluationMetric.ACCURACY,
                    "efficiency": EvaluationMetric.EFFICIENCY,
                    "novelty": EvaluationMetric.NOVELTY,
                }
                metric = metric_map.get(focus, EvaluationMetric.ACCURACY)
                meta_result = self.mechanisms["meta_learner"].evaluate_strategy(
                    "adaptive",
                    metric,
                    0.8
                )
                result["meta_learning"] = meta_result
            
            result["success"] = True
            logger.info(f"✓ 进化已触发: {focus}")
            
        except Exception as e:
            logger.error(f"进化失败: {e}")
            result["error"] = str(e)
        
        return result
    
    def enter_low_power_mode(self):
        """进入低功耗模式"""
        logger.info("🔋 进入低功耗模式...")
        self.state = SystemState.LOW_POWER
        
        if "rhythm_controller" in self.mechanisms:
            try:
                self.mechanisms["rhythm_controller"].enter_phase("resting")
            except Exception:
                pass
        
        if "existence" in self.layers:
            try:
                if hasattr(self.layers["existence"], 'enter_state'):
                    from core.presence.existence_layer import PresenceState
                    self.layers["existence"].enter_state(PresenceState.RESTING)
            except Exception:
                pass
    
    def exit_low_power_mode(self):
        """退出低功耗模式"""
        logger.info("⚡ 退出低功耗模式")
        self.state = SystemState.ACTIVE
        
        if "rhythm_controller" in self.mechanisms:
            try:
                self.mechanisms["rhythm_controller"].enter_phase("exploration")
            except Exception:
                pass
        
        if "existence" in self.layers:
            try:
                if hasattr(self.layers["existence"], 'enter_state'):
                    from core.presence.existence_layer import PresenceState
                    self.layers["existence"].enter_state(PresenceState.AWAKE)
            except Exception:
                pass
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: str, data: Any):
        """发射事件"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"事件处理器错误: {e}")


orchestrator = SystemOrchestrator()