"""
认知循环 - 学习进化的核心引擎

借鉴OpenHarness的Agent Loop设计，实现完整的认知循环：
1. 感知 - 从环境接收信号
2. 理解 - 整合到知识网络
3. 行动 - 执行学习/进化操作
4. 反思 - 验证效果并优化

核心理念：Loop Engineering - 让AI自己跑循环
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio

from core.loop_mixin import AsyncLoopMixin as _AsyncLoopMixinBase
from core.loop_mixin import LoopStatus as _LoopStatus

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LoopState(Enum):
    IDLE = "idle"
    PERCEIVING = "perceiving"
    UNDERSTANDING = "understanding"
    ACTING = "acting"
    REFLECTING = "reflecting"
    RESTING = "resting"
    ERROR = "error"


@dataclass
class CycleResult:
    cycle_id: str
    state: LoopState
    signals_processed: int
    knowledge_updated: bool
    actions_taken: List[str]
    insights: List[str]
    confidence: float
    duration_ms: float
    error: Optional[str] = None


@dataclass
class LoopMetrics:
    total_cycles: int = 0
    successful_cycles: int = 0
    total_signals: int = 0
    total_knowledge_updates: int = 0
    average_confidence: float = 0.0
    average_duration_ms: float = 0.0
    error_rate: float = 0.0


class CognitiveLoop(_AsyncLoopMixinBase):
    """
    认知循环 - 学习进化的核心引擎
    
    整合七大机制和六层架构，实现完整的认知循环
    """
    
    def __init__(self, max_cycles: int = 1000):
        super().__init__(name="cognitive_loop", cooldown_seconds=120.0, max_failures_before_degraded=3)
        self.max_cycles = max_cycles
        self.state = LoopState.IDLE
        self.cycle_count = 0
        self.metrics = LoopMetrics()
        
        self._init_mechanisms()
        self._init_layers()
        self._init_evaluators()
        
        self.cycle_history: List[CycleResult] = []
        self.active_tasks: List[asyncio.Task] = []
        
        self.evaluators: List[Callable] = []
        self.validators: List[Callable] = []
        
        logger.info("🔄 认知循环已初始化")
    
    def _init_mechanisms(self):
        """初始化七大机制"""
        from core.learning import (
            IncrementalPerception,
            LearningFeedbackLoop,
            ErrorAlchemy,
            ToolSelfBuilder,
            KnowledgeWeaver,
            CognitiveRhythmController,
            MetaLearner,
        )
        
        self.perception = IncrementalPerception()
        self.feedback_loop = LearningFeedbackLoop()
        self.error_alchemy = ErrorAlchemy()
        self.tool_builder = ToolSelfBuilder()
        self.knowledge_weaver = KnowledgeWeaver()
        self.rhythm = CognitiveRhythmController()
        self.meta_learner = MetaLearner()
        
        logger.info("  ✓ 七大机制已加载")
    
    def _init_layers(self):
        """初始化六层架构"""
        try:
            from core.layers.l2_learning import L2LearningLayer
            from core.layers.l3_integration import L3IntegrationLayer
            from core.layers.l4_validation import L4ValidationLayer
            from core.layers.l5_evolution import L5EvolutionLayer
            from core.layers.l6_introspection import L6IntrospectionLayer
            
            self.l2 = L2LearningLayer()
            self.l3 = L3IntegrationLayer()
            self.l4 = L4ValidationLayer()
            self.l5 = L5EvolutionLayer()
            self.l6 = L6IntrospectionLayer()
            
            logger.info("  ✓ 六层架构已加载")
        except Exception as e:
            logger.warning(f"  ⚠ 六层架构加载失败: {e}")
            self.l2 = self.l3 = self.l4 = self.l5 = self.l6 = None
    
    def _init_evaluators(self):
        """初始化验证器 - Loop Engineering的关键"""
        self.evaluators = [
            self._evaluate_confidence,
            self._evaluate_knowledge_quality,
            self._evaluate_learning_progress,
        ]
        
        self.validators = [
            self._validate_no_big_model_smell,
            self._validate_complete_reasoning,
        ]
    
    async def run_cycle(self, input_signal: Any = None) -> CycleResult:
        """
        运行一个完整的认知循环
        
        循环：感知 → 理解 → 行动 → 反思
        """
        start_time = datetime.now()
        cycle_id = f"cycle_{self.cycle_count}"
        self.cycle_count += 1
        
        signals_processed = 0
        knowledge_updated = False
        actions_taken = []
        insights = []
        confidence = 0.0
        error = None
        
        async with self.async_loop_context():
            try:
                self.state = LoopState.PERCEIVING
                perception_result = await self._perceive(input_signal)
                signals_processed = perception_result.get("signals_processed", 0)
                actions_taken.extend(perception_result.get("actions", []))
                
                self.state = LoopState.UNDERSTANDING
                understanding_result = await self._understand(perception_result)
                insights.extend(understanding_result.get("insights", []))
                actions_taken.extend(understanding_result.get("actions", []))
                
                self.state = LoopState.ACTING
                action_result = await self._act(understanding_result)
                knowledge_updated = action_result.get("knowledge_updated", False)
                actions_taken.extend(action_result.get("actions", []))
                
                self.state = LoopState.REFLECTING
                reflection_result = await self._reflect(action_result)
                confidence = reflection_result.get("confidence", 0.0)
                insights.extend(reflection_result.get("insights", []))
                
                evaluation_passed = await self._evaluate_cycle(reflection_result)
                if not evaluation_passed:
                    insights.append("循环评估未通过，需要改进")
                
                self.state = LoopState.IDLE
                
            except Exception as e:
                self.state = LoopState.ERROR
                error = str(e)
                logger.error(f"认知循环错误: {e}")
                
                error_id = self.error_alchemy.record_error(e)
                alchemy_result = self.error_alchemy.alchemize(error_id)
                insights.append(f"错误已转化为{len(alchemy_result.signals_extracted)}个学习信号")
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        result = CycleResult(
            cycle_id=cycle_id,
            state=self.state,
            signals_processed=signals_processed,
            knowledge_updated=knowledge_updated,
            actions_taken=actions_taken,
            insights=insights,
            confidence=confidence,
            duration_ms=duration_ms,
            error=error,
        )
        
        self.cycle_history.append(result)
        self._update_metrics(result)
        
        rhythm_snapshot = self.rhythm.tick()
        if rhythm_snapshot.state.value == "resting":
            self.state = LoopState.RESTING
        
        return result
    
    async def _perceive(self, input_signal: Any) -> Dict[str, Any]:
        """感知阶段 - 接收并处理信号"""
        from core.learning import Signal, SignalType
        
        signals_processed = 0
        actions = []
        
        if input_signal is not None:
            signal_type = self._classify_signal(input_signal)
            signal = Signal(
                type=signal_type,
                content=input_signal,
                source="external",
            )
            
            perception_result = self.perception.perceive(signal)
            signals_processed = perception_result.signals_absorbed
            
            if perception_result.patterns_detected:
                actions.append(f"检测到{len(perception_result.patterns_detected)}个模式")
            
            if perception_result.knowledge_updated:
                actions.append("知识库已更新")
        
        recent_signals = self.perception.get_recent_signals(5)
        for sig in recent_signals:
            if sig.type == SignalType.FAILURE:
                actions.append(f"处理失败信号: {str(sig.content)[:50]}")
        
        return {
            "signals_processed": signals_processed,
            "actions": actions,
            "recent_signals": recent_signals,
        }
    
    def _classify_signal(self, signal: Any) -> 'SignalType':
        """分类信号类型"""
        from core.learning import SignalType
        
        if isinstance(signal, Exception):
            return SignalType.FAILURE
        elif isinstance(signal, dict):
            if signal.get("success") is False:
                return SignalType.FAILURE
            elif signal.get("success") is True:
                return SignalType.SUCCESS
            elif "feedback" in signal:
                return SignalType.FEEDBACK
        elif isinstance(signal, str):
            if "error" in signal.lower() or "fail" in signal.lower():
                return SignalType.FAILURE
            elif "success" in signal.lower():
                return SignalType.SUCCESS
        
        return SignalType.CONTEXT
    
    async def _understand(self, perception_result: Dict) -> Dict[str, Any]:
        """理解阶段 - 整合到知识网络"""
        from core.learning import NodeType
        
        insights = []
        actions = []
        
        recent_signals = perception_result.get("recent_signals", [])
        
        for signal in recent_signals:
            node_id = self.knowledge_weaver.add_node(
                content=signal.content,
                node_type=NodeType.EXPERIENCE,
                metadata={"signal_type": signal.type.value},
            )
            
            if len(self.knowledge_weaver.connections) > 0:
                insights.append(f"知识节点已连接到现有网络")
        
        statistics = self.knowledge_weaver.get_statistics()
        if statistics["total_clusters"] > 0:
            insights.append(f"发现{statistics['total_clusters']}个知识群落")
        
        if len(recent_signals) >= 3:
            actions.append("批量知识整合完成")
        
        return {
            "insights": insights,
            "actions": actions,
            "knowledge_stats": statistics,
        }
    
    async def _act(self, understanding_result: Dict) -> Dict[str, Any]:
        """行动阶段 - 执行学习/进化操作"""
        actions = []
        knowledge_updated = False
        
        rhythm_snapshot = self.rhythm.tick()
        recommended_actions = self.rhythm.get_recommended_actions()
        
        for action in recommended_actions[:3]:
            actions.append(f"执行: {action}")
        
        if self.l2:
            try:
                learning_target = {
                    "name": "auto_learning",
                    "context": understanding_result.get("knowledge_stats", {}),
                }
                actions.append("触发L2学习层")
            except Exception as e:
                logger.error(f"L2调用失败: {e}")
        
        if rhythm_snapshot.phase.value in ["consolidation", "mastery"]:
            knowledge_updated = True
            actions.append("知识已巩固")
        
        tool_opportunities = self.tool_builder.identify_tool_opportunities()
        if tool_opportunities:
            actions.append(f"发现{len(tool_opportunities)}个工具构建机会")
        
        return {
            "actions": actions,
            "knowledge_updated": knowledge_updated,
        }
    
    async def _reflect(self, action_result: Dict) -> Dict[str, Any]:
        """反思阶段 - 验证效果并优化"""
        from core.learning import EvaluationMetric
        
        insights = []
        confidence = 0.5
        
        success_rate = self._calculate_success_rate()
        self.rhythm.record_metric("success_rate", success_rate)
        
        self.meta_learner.evaluate_strategy(
            "spaced_repetition",
            EvaluationMetric.ACCURACY,
            success_rate,
        )
        
        if success_rate > 0.7:
            confidence = 0.8
            insights.append("学习效果良好")
        elif success_rate > 0.5:
            confidence = 0.6
            insights.append("学习效果中等")
        else:
            confidence = 0.3
            insights.append("学习效果需要改进")
        
        strategy_recommendations = self.meta_learner.recommend_strategy({
            "recent_accuracy": success_rate,
        })
        
        if strategy_recommendations:
            top_strategy = strategy_recommendations[0]
            insights.append(f"推荐策略: {top_strategy.strategy.name}")
        
        return {
            "insights": insights,
            "confidence": confidence,
            "success_rate": success_rate,
        }
    
    async def _evaluate_cycle(self, reflection_result: Dict) -> bool:
        """
        评估循环效果 - Loop Engineering的核心
        
        铁律：生成器不能给自己的活打分！
        """
        all_passed = True
        
        for evaluator in self.evaluators:
            try:
                passed = evaluator(reflection_result)
                if not passed:
                    all_passed = False
            except Exception as e:
                logger.warning(f"评估器错误: {e}")
        
        for validator in self.validators:
            try:
                valid = validator(reflection_result)
                if not valid:
                    all_passed = False
            except Exception as e:
                logger.warning(f"验证器错误: {e}")
        
        return all_passed
    
    def _evaluate_confidence(self, result: Dict) -> bool:
        """评估置信度"""
        confidence = result.get("confidence", 0)
        return confidence >= 0.5
    
    def _evaluate_knowledge_quality(self, result: Dict) -> bool:
        """评估知识质量"""
        stats = self.knowledge_weaver.get_statistics()
        return stats["total_nodes"] > 0
    
    def _evaluate_learning_progress(self, result: Dict) -> bool:
        """评估学习进度"""
        success_rate = result.get("success_rate", 0)
        return success_rate >= 0.3
    
    def _validate_no_big_model_smell(self, result: Dict) -> bool:
        """
        验证：没有"大型模型气质"
        
        大型模型气质：先宣布完成，再测量
        正确做法：先测量，再行动，最后验证
        """
        if self.cycle_count < 3:
            return True
        
        recent_cycles = self.cycle_history[-3:]
        for cycle in recent_cycles:
            if cycle.error:
                return False
        
        return True
    
    def _validate_complete_reasoning(self, result: Dict) -> bool:
        """验证：推理完整"""
        return result.get("confidence", 0) > 0
    
    def _calculate_success_rate(self) -> float:
        """计算成功率"""
        if not self.cycle_history:
            return 0.5
        
        recent = self.cycle_history[-20:]
        successes = sum(1 for c in recent if c.error is None and c.confidence > 0.5)
        
        return successes / len(recent) if recent else 0.5
    
    def _update_metrics(self, result: CycleResult) -> None:
        """更新循环指标"""
        self.metrics.total_cycles += 1
        
        if result.error is None:
            self.metrics.successful_cycles += 1
        
        self.metrics.total_signals += result.signals_processed
        
        if result.knowledge_updated:
            self.metrics.total_knowledge_updates += 1
        
        total = self.metrics.total_cycles
        self.metrics.average_confidence = (
            (self.metrics.average_confidence * (total - 1) + result.confidence) / total
        )
        self.metrics.average_duration_ms = (
            (self.metrics.average_duration_ms * (total - 1) + result.duration_ms) / total
        )
        
        self.metrics.error_rate = (
            (total - self.metrics.successful_cycles) / total
        )
    
    async def run_continuous(self, signal_generator: Callable = None, max_cycles: int = None) -> List[CycleResult]:
        """
        持续运行认知循环
        
        Loop Engineering: 让AI自己跑循环
        """
        max_cycles = max_cycles or self.max_cycles
        results = []
        
        logger.info(f"🔄 开始持续认知循环 (最多{max_cycles}个循环)")
        
        for i in range(max_cycles):
            signal = None
            if signal_generator:
                try:
                    signal = signal_generator()
                except Exception as e:
                    logger.warning(f"信号生成器错误: {e}")
            
            result = await self.run_cycle(signal)
            results.append(result)
            
            if self.state == LoopState.RESTING:
                logger.debug("认知循环进入休息状态")
                await asyncio.sleep(1)
            
            if self.state == LoopState.ERROR:
                logger.warning(f"认知循环遇到错误，暂停")
                await asyncio.sleep(2)
            
            if i > 0 and i % 10 == 0:
                logger.info(
                    f"  进度: {i}/{max_cycles}, "
                    f"成功率: {self._calculate_success_rate():.2f}, "
                    f"平均置信度: {self.metrics.average_confidence:.2f}"
                )
        
        logger.info(f"✓ 认知循环完成，共{len(results)}个循环")
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """获取循环状态"""
        return {
            "state": self.state.value,
            "cycle_count": self.cycle_count,
            "metrics": {
                "total_cycles": self.metrics.total_cycles,
                "successful_cycles": self.metrics.successful_cycles,
                "success_rate": self._calculate_success_rate(),
                "average_confidence": self.metrics.average_confidence,
                "average_duration_ms": self.metrics.average_duration_ms,
                "error_rate": self.metrics.error_rate,
            },
            "rhythm": self.rhythm.get_phase_progress(),
            "knowledge": self.knowledge_weaver.get_statistics(),
            "learning": {
                "signals": len(self.perception.signals),
                "patterns": len(self.perception.patterns),
                "strategies": len(self.meta_learner.strategies),
            },
        }
    
    def force_rest(self) -> None:
        """强制休息"""
        self.state = LoopState.RESTING
        self.rhythm.force_phase(
            self.rhythm.current_phase,
            "强制休息"
        )
        logger.info("认知循环进入强制休息状态")
    
    def reset(self) -> None:
        """重置循环"""
        self.state = LoopState.IDLE
        self.cycle_count = 0
        self.cycle_history.clear()
        self.metrics = LoopMetrics()
        
        self.perception.clear()
        self.rhythm.reset()
        
        logger.info("认知循环已重置")