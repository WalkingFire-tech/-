"""
测试七大核心机制
"""
import pytest
from datetime import datetime, timedelta

from core.learning.incremental_perception import (
    IncrementalPerception,
    Signal,
    SignalType,
)
from core.learning.feedback_loop import (
    LearningFeedbackLoop,
    Feedback,
    FeedbackType,
)
from core.learning.error_alchemy import (
    ErrorAlchemy,
    LearningSignal,
    LearningSignalType,
    ErrorCategory,
)
from core.learning.tool_builder import (
    ToolSelfBuilder,
    ToolNeed,
    Tool,
    ToolStatus,
    NeedPriority,
)
from core.learning.knowledge_weaver import (
    KnowledgeWeaver,
    Node,
    Connection,
    ConnectionType,
    NodeType,
)
from core.learning.rhythm_controller import (
    CognitiveRhythmController,
    LearningPhase,
    LearningState,
)
from core.learning.meta_learning import (
    MetaLearner,
    LearningStrategy,
    StrategyType,
    EvaluationMetric,
)


class TestIncrementalPerception:
    """测试增量感知学习"""
    
    def test_perceive_single_signal(self):
        perception = IncrementalPerception()
        
        signal = Signal(
            type=SignalType.SUCCESS,
            content={"action": "test", "result": True},
            source="test_case",
        )
        
        result = perception.perceive(signal)
        
        assert result.signals_absorbed == 1
        assert len(perception.signals) == 1
        assert result.confidence >= 0
    
    def test_perceive_batch_signals(self):
        perception = IncrementalPerception()
        
        signals = [
            Signal(type=SignalType.SUCCESS, content=f"test_{i}")
            for i in range(5)
        ]
        
        result = perception.perceive_batch(signals)
        
        assert result.signals_absorbed == 5
        assert len(perception.signals) == 5
    
    def test_pattern_detection(self):
        perception = IncrementalPerception(pattern_threshold=3)
        
        for i in range(5):
            signal = Signal(
                type=SignalType.SUCCESS,
                content={"pattern": "repeated"},
            )
            perception.perceive(signal)
        
        patterns = perception.get_patterns()
        assert len(patterns) > 0
    
    def test_knowledge_extraction(self):
        perception = IncrementalPerception()
        
        signal = Signal(
            type=SignalType.SUCCESS,
            content="important_knowledge",
            context={"key": "value"},
        )
        
        perception.perceive(signal)
        
        knowledge = perception.get_knowledge()
        assert knowledge is not None
        assert len(knowledge) > 0
    
    def test_export_import_state(self):
        perception = IncrementalPerception()
        
        for i in range(3):
            perception.perceive(Signal(
                type=SignalType.SUCCESS,
                content=f"test_{i}",
            ))
        
        state = perception.export_state()
        
        perception2 = IncrementalPerception()
        perception2.import_state(state)
        
        assert perception2.get_knowledge() == perception.get_knowledge()


class TestLearningFeedbackLoop:
    """测试经验反馈回路"""
    
    def test_register_knowledge(self):
        loop = LearningFeedbackLoop()
        
        loop.register_knowledge("k1", "test knowledge", 0.5)
        
        assert "k1" in loop.knowledge_store
        assert loop.knowledge_store["k1"]["confidence"] == 0.5
    
    def test_validate_positive_feedback(self):
        loop = LearningFeedbackLoop()
        loop.register_knowledge("k1", "test", 0.5)
        
        feedback = Feedback(
            type=FeedbackType.POSITIVE,
            knowledge_id="k1",
            expected_outcome="result",
            actual_outcome="result",
        )
        
        result = loop.validate(feedback)
        
        assert result.validated
        assert result.accuracy >= 0.5
        assert loop.knowledge_store["k1"]["confidence"] > 0.5
    
    def test_validate_negative_feedback(self):
        loop = LearningFeedbackLoop()
        loop.register_knowledge("k1", "test", 0.5)
        
        feedback = Feedback(
            type=FeedbackType.NEGATIVE,
            knowledge_id="k1",
            expected_outcome="expected",
            actual_outcome="different",
        )
        
        result = loop.validate(feedback)
        
        assert result.accuracy < 1.0
    
    def test_feedback_summary(self):
        loop = LearningFeedbackLoop()
        loop.register_knowledge("k1", "test", 0.5)
        
        for i in range(5):
            feedback = Feedback(
                type=FeedbackType.POSITIVE,
                knowledge_id="k1",
                expected_outcome=f"result_{i}",
                actual_outcome=f"result_{i}",
            )
            loop.validate(feedback)
        
        summary = loop.get_feedback_summary()
        
        assert summary["total"] == 5
        assert summary["positive_rate"] > 0


class TestErrorAlchemy:
    """测试失败的炼金术"""
    
    def test_record_error(self):
        alchemy = ErrorAlchemy()
        
        error = ValueError("test error")
        error_id = alchemy.record_error(error, {"context": "test"})
        
        assert error_id in alchemy.error_records
        assert alchemy.error_records[error_id].category == ErrorCategory.LOGIC
    
    def test_alchemize_error(self):
        alchemy = ErrorAlchemy()
        
        error = ValueError("test error")
        error_id = alchemy.record_error(error)
        
        result = alchemy.alchemize(error_id)
        
        assert result.error_id == error_id
        assert len(result.signals_extracted) > 0
        assert result.gold_extracted
    
    def test_avoid_patterns(self):
        alchemy = ErrorAlchemy()
        
        for i in range(3):
            error = ValueError(f"repeated error")
            alchemy.record_error(error)
        
        patterns = alchemy.get_avoid_patterns()
        
        assert len(patterns) > 0
    
    def test_lessons_learned(self):
        alchemy = ErrorAlchemy()
        
        errors = [
            ValueError("error1"),
            TypeError("error2"),
            RuntimeError("error3"),
        ]
        
        for error in errors:
            error_id = alchemy.record_error(error)
            alchemy.alchemize(error_id)
        
        lessons = alchemy.get_lessons_learned()
        
        assert lessons["total_errors"] == 3
        assert len(lessons["error_categories"]) > 0


class TestToolSelfBuilder:
    """测试工具自我构建"""
    
    def test_observe_need(self):
        builder = ToolSelfBuilder()
        
        need_key = builder.observe_need(
            "需要数据转换功能",
            NeedPriority.HIGH,
        )
        
        assert need_key in builder.needs
        assert builder.needs[need_key].frequency == 1
    
    def test_need_accumulation(self):
        builder = ToolSelfBuilder()
        
        for i in range(5):
            builder.observe_need("需要数据转换功能")
        
        opportunities = builder.identify_tool_opportunities()
        
        assert len(opportunities) > 0
    
    def test_build_tool(self):
        builder = ToolSelfBuilder(need_threshold=2)
        
        for i in range(3):
            builder.observe_need("需要验证功能")
        
        needs = builder.identify_tool_opportunities()
        if needs:
            result = builder.build_tool(needs[0], template_type="validator")
            
            assert result.tool is not None
            assert result.tool.status in [ToolStatus.DRAFT, ToolStatus.TESTING, ToolStatus.ACTIVE]
    
    def test_use_tool(self):
        builder = ToolSelfBuilder()
        
        builder.observe_need("测试工具", NeedPriority.HIGH)
        needs = builder.identify_tool_opportunities()
        
        if needs:
            build_result = builder.build_tool(
                needs[0],
                custom_code='''
def test_tool(input_data):
    return input_data
''',
            )
            
            if build_result.success and build_result.tool:
                tool_id = build_result.tool.tool_id
                result = builder.use_tool(tool_id, "test")
                
                assert result == "test"
                assert builder.tools[tool_id].usage_count == 1


class TestKnowledgeWeaver:
    """测试知识网络编织"""
    
    def test_add_node(self):
        weaver = KnowledgeWeaver()
        
        node_id = weaver.add_node(
            "测试概念",
            NodeType.CONCEPT,
        )
        
        assert node_id in weaver.nodes
        assert weaver.nodes[node_id].type == NodeType.CONCEPT
    
    def test_connect_nodes(self):
        weaver = KnowledgeWeaver()
        
        node1 = weaver.add_node("概念1", NodeType.CONCEPT)
        node2 = weaver.add_node("概念2", NodeType.CONCEPT)
        
        success = weaver.connect(
            node1,
            node2,
            ConnectionType.RELATED_TO,
        )
        
        assert success
        assert len(weaver.connections) > 0
    
    def test_weave_batch(self):
        weaver = KnowledgeWeaver()
        
        nodes = [
            ("概念A", NodeType.CONCEPT),
            ("概念B", NodeType.CONCEPT),
            ("概念C", NodeType.CONCEPT),
        ]
        
        result = weaver.weave(nodes)
        
        assert result.nodes_added == 3
        assert result.connections_added >= 0
    
    def test_query_network(self):
        weaver = KnowledgeWeaver()
        
        node1 = weaver.add_node("核心概念", NodeType.CONCEPT)
        node2 = weaver.add_node("相关概念", NodeType.CONCEPT)
        weaver.connect(node1, node2, ConnectionType.RELATED_TO)
        
        query_result = weaver.query(node1)
        
        assert query_result["node"] is not None
        assert len(query_result["neighbors"]) > 0
    
    def test_find_path(self):
        weaver = KnowledgeWeaver()
        
        node1 = weaver.add_node("A", NodeType.CONCEPT)
        node2 = weaver.add_node("B", NodeType.CONCEPT)
        node3 = weaver.add_node("C", NodeType.CONCEPT)
        
        weaver.connect(node1, node2, ConnectionType.RELATED_TO)
        weaver.connect(node2, node3, ConnectionType.RELATED_TO)
        
        path = weaver.find_path(node1, node3)
        
        assert len(path) == 3
        assert path[0] == node1
        assert path[-1] == node3


class TestCognitiveRhythmController:
    """测试认知节奏控制器"""
    
    def test_initial_state(self):
        controller = CognitiveRhythmController()
        
        assert controller.current_phase == LearningPhase.EXPLORATION
        assert controller.current_state == LearningState.ACTIVE
        assert controller.energy_level == 1.0
    
    def test_tick_updates_state(self):
        controller = CognitiveRhythmController()
        
        snapshot = controller.tick()
        
        assert snapshot.state in LearningState
        assert snapshot.phase in LearningPhase
        assert 0 <= snapshot.energy_level <= 1.0
    
    def test_record_metric(self):
        controller = CognitiveRhythmController()
        
        for i in range(10):
            controller.record_metric("success_rate", 0.8)
            controller.tick()
        
        assert len(controller.learning_metrics["success_rate"]) == 10
    
    def test_phase_transition(self):
        controller = CognitiveRhythmController()
        
        for i in range(30):
            controller.record_metric("success_rate", 0.8)
            controller.tick()
        
        assert len(controller.phase_transitions) >= 0
    
    def test_get_recommended_actions(self):
        controller = CognitiveRhythmController()
        
        actions = controller.get_recommended_actions()
        
        assert len(actions) > 0
        assert all(isinstance(a, str) for a in actions)
    
    def test_force_phase(self):
        controller = CognitiveRhythmController()
        
        controller.force_phase(LearningPhase.MASTERY, "测试切换")
        
        assert controller.current_phase == LearningPhase.MASTERY


class TestMetaLearner:
    """测试元学习策略优化"""
    
    def test_default_strategies(self):
        learner = MetaLearner()
        
        assert len(learner.strategies) > 0
        assert "spaced_repetition" in learner.strategies
    
    def test_evaluate_strategy(self):
        learner = MetaLearner()
        
        learner.evaluate_strategy(
            "spaced_repetition",
            EvaluationMetric.ACCURACY,
            0.8,
        )
        
        assert len(learner.evaluations["spaced_repetition"]) == 1
    
    def test_recommend_strategy(self):
        learner = MetaLearner()
        
        context = {"task_type": "记忆", "recent_accuracy": 0.5}
        recommendations = learner.recommend_strategy(context)
        
        assert len(recommendations) > 0
        assert all(hasattr(r, "strategy") for r in recommendations)
    
    def test_optimize_parameters(self):
        learner = MetaLearner()
        
        for i in range(10):
            learner.evaluate_strategy(
                "spaced_repetition",
                EvaluationMetric.ACCURACY,
                0.6,
            )
        
        optimized = learner.optimize_parameters("spaced_repetition")
        
        assert isinstance(optimized, dict)
    
    def test_learn_from_experience(self):
        learner = MetaLearner()
        
        outcome = {
            "accuracy": 0.8,
            "speed": 0.7,
            "retention": 0.9,
            "context": {"task": "test"},
        }
        
        learner.learn_from_experience("spaced_repetition", outcome)
        
        assert len(learner.evaluations["spaced_repetition"]) > 0
    
    def test_strategy_stats(self):
        learner = MetaLearner()
        
        for i in range(5):
            learner.evaluate_strategy(
                "spaced_repetition",
                EvaluationMetric.ACCURACY,
                0.7 + i * 0.05,
            )
        
        stats = learner.get_strategy_stats("spaced_repetition")
        
        assert "name" in stats
        assert "metrics" in stats
    
    def test_compare_strategies(self):
        learner = MetaLearner()
        
        for i in range(5):
            learner.evaluate_strategy("spaced_repetition", EvaluationMetric.ACCURACY, 0.8)
            learner.evaluate_strategy("elaboration", EvaluationMetric.ACCURACY, 0.6)
        
        comparison = learner.compare_strategies(
            ["spaced_repetition", "elaboration"],
            EvaluationMetric.ACCURACY,
        )
        
        assert len(comparison) == 2
        assert comparison["spaced_repetition"] > comparison["elaboration"]


class TestIntegration:
    """集成测试：测试七大机制的协作"""
    
    def test_full_learning_cycle(self):
        perception = IncrementalPerception()
        feedback_loop = LearningFeedbackLoop()
        error_alchemy = ErrorAlchemy()
        rhythm = CognitiveRhythmController()
        meta_learner = MetaLearner()
        
        for i in range(10):
            signal = Signal(
                type=SignalType.SUCCESS,
                content=f"learning_{i}",
            )
            perception.perceive(signal)
            
            rhythm.record_metric("success_rate", 0.8)
            rhythm.tick()
            
            meta_learner.evaluate_strategy(
                "spaced_repetition",
                EvaluationMetric.ACCURACY,
                0.8,
            )
        
        assert len(perception.signals) == 10
        assert len(rhythm.state_history) == 10
        assert len(meta_learner.evaluations["spaced_repetition"]) == 10
    
    def test_error_to_learning(self):
        error_alchemy = ErrorAlchemy()
        perception = IncrementalPerception()
        
        error = ValueError("test error")
        error_id = error_alchemy.record_error(error)
        result = error_alchemy.alchemize(error_id)
        
        for signal in result.signals_extracted:
            learning_signal = Signal(
                type=SignalType.PATTERN,
                content=signal.content,
            )
            perception.perceive(learning_signal)
        
        assert len(perception.signals) == len(result.signals_extracted)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])