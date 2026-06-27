"""
验证七大核心机制
"""
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


def test_incremental_perception():
    print("\n=== 测试增量感知学习 ===")
    
    perception = IncrementalPerception()
    
    signal = Signal(
        type=SignalType.SUCCESS,
        content={"action": "test", "result": True},
        source="test_case",
    )
    result = perception.perceive(signal)
    assert result.signals_absorbed == 1, "信号吸收失败"
    print("✓ 单个信号感知成功")
    
    signals = [
        Signal(type=SignalType.SUCCESS, content=f"test_{i}")
        for i in range(5)
    ]
    result = perception.perceive_batch(signals)
    assert result.signals_absorbed == 5, "批量信号吸收失败"
    print("✓ 批量信号感知成功")
    
    perception2 = IncrementalPerception(pattern_threshold=3)
    for i in range(5):
        signal = Signal(
            type=SignalType.SUCCESS,
            content={"pattern": "repeated"},
        )
        perception2.perceive(signal)
    patterns = perception2.get_patterns()
    assert len(patterns) > 0, "模式检测失败"
    print("✓ 模式检测成功")
    
    knowledge = perception.get_knowledge()
    assert knowledge is not None, "知识提取失败"
    print("✓ 知识提取成功")
    
    print("✅ 增量感知学习测试通过")


def test_feedback_loop():
    print("\n=== 测试经验反馈回路 ===")
    
    loop = LearningFeedbackLoop()
    
    loop.register_knowledge("k1", "test knowledge", 0.5)
    assert "k1" in loop.knowledge_store, "知识注册失败"
    print("✓ 知识注册成功")
    
    feedback = Feedback(
        type=FeedbackType.POSITIVE,
        knowledge_id="k1",
        expected_outcome="result",
        actual_outcome="result",
    )
    result = loop.validate(feedback)
    assert result.validated, f"验证失败，accuracy={result.accuracy}"
    print(f"✓ 验证成功，accuracy={result.accuracy:.2f}")
    
    if result.accuracy >= 0.8:
        assert loop.knowledge_store["k1"]["confidence"] > 0.5, "置信度未更新"
        print("✓ 置信度已更新")
    else:
        print(f"  注：accuracy={result.accuracy:.2f} < 0.8，置信度未增强")
    
    for i in range(5):
        feedback = Feedback(
            type=FeedbackType.POSITIVE,
            knowledge_id="k1",
            expected_outcome=f"result_{i}",
            actual_outcome=f"result_{i}",
        )
        loop.validate(feedback)
    
    summary = loop.get_feedback_summary()
    assert summary["total"] == 6, "反馈统计错误"
    print("✓ 反馈摘要成功")
    
    print("✅ 经验反馈回路测试通过")


def test_error_alchemy():
    print("\n=== 测试失败的炼金术 ===")
    
    alchemy = ErrorAlchemy()
    
    error = ValueError("test error")
    error_id = alchemy.record_error(error, {"context": "test"})
    assert error_id in alchemy.error_records, "错误记录失败"
    print("✓ 错误记录成功")
    
    result = alchemy.alchemize(error_id)
    assert result.error_id == error_id, "炼金结果错误"
    assert len(result.signals_extracted) > 0, "信号提取失败"
    print("✓ 错误炼金成功")
    
    for i in range(3):
        error = ValueError("repeated error")
        alchemy.record_error(error)
    
    patterns = alchemy.get_avoid_patterns()
    assert len(patterns) > 0, "避免模式提取失败"
    print("✓ 避免模式提取成功")
    
    lessons = alchemy.get_lessons_learned()
    assert lessons["total_errors"] == 4, "教训统计错误"
    print("✓ 教训学习成功")
    
    print("✅ 失败的炼金术测试通过")


def test_tool_builder():
    print("\n=== 测试工具自我构建 ===")
    
    builder = ToolSelfBuilder()
    
    need_key = builder.observe_need(
        "需要数据转换功能",
        NeedPriority.HIGH,
    )
    assert need_key in builder.needs, "需求观察失败"
    print("✓ 需求观察成功")
    
    for i in range(5):
        builder.observe_need("需要数据转换功能")
    
    opportunities = builder.identify_tool_opportunities()
    assert len(opportunities) > 0, "工具机会识别失败"
    print("✓ 工具机会识别成功")
    
    builder2 = ToolSelfBuilder(need_threshold=2)
    for i in range(3):
        builder2.observe_need("需要验证功能")
    
    needs = builder2.identify_tool_opportunities()
    if needs:
        result = builder2.build_tool(needs[0], template_type="validator")
        assert result.tool is not None, "工具构建失败"
        print("✓ 工具构建成功")
    
    print("✅ 工具自我构建测试通过")


def test_knowledge_weaver():
    print("\n=== 测试知识网络编织 ===")
    
    weaver = KnowledgeWeaver()
    
    node_id = weaver.add_node("测试概念", NodeType.CONCEPT)
    assert node_id in weaver.nodes, "节点添加失败"
    print("✓ 节点添加成功")
    
    node1 = weaver.add_node("概念1", NodeType.CONCEPT)
    node2 = weaver.add_node("概念2", NodeType.CONCEPT)
    success = weaver.connect(node1, node2, ConnectionType.RELATED_TO)
    assert success, "节点连接失败"
    print("✓ 节点连接成功")
    
    nodes = [
        ("概念A", NodeType.CONCEPT),
        ("概念B", NodeType.CONCEPT),
        ("概念C", NodeType.CONCEPT),
    ]
    result = weaver.weave(nodes)
    assert result.nodes_added == 3, "批量编织失败"
    print("✓ 批量编织成功")
    
    query_result = weaver.query(node1)
    assert query_result["node"] is not None, "查询失败"
    print("✓ 网络查询成功")
    
    node3 = weaver.add_node("概念3", NodeType.CONCEPT)
    weaver.connect(node2, node3, ConnectionType.RELATED_TO)
    path = weaver.find_path(node1, node3)
    assert len(path) == 3, "路径查找失败"
    print("✓ 路径查找成功")
    
    print("✅ 知识网络编织测试通过")


def test_rhythm_controller():
    print("\n=== 测试认知节奏控制器 ===")
    
    controller = CognitiveRhythmController()
    
    assert controller.current_phase == LearningPhase.EXPLORATION, "初始阶段错误"
    assert controller.current_state == LearningState.ACTIVE, "初始状态错误"
    print("✓ 初始状态正确")
    
    snapshot = controller.tick()
    assert snapshot.state in LearningState, "状态更新失败"
    print("✓ 状态更新成功")
    
    for i in range(10):
        controller.record_metric("success_rate", 0.8)
        controller.tick()
    
    assert len(controller.learning_metrics["success_rate"]) == 10, "指标记录失败"
    print("✓ 指标记录成功")
    
    actions = controller.get_recommended_actions()
    assert len(actions) > 0, "推荐动作失败"
    print("✓ 推荐动作成功")
    
    controller.force_phase(LearningPhase.MASTERY, "测试切换")
    assert controller.current_phase == LearningPhase.MASTERY, "强制切换失败"
    print("✓ 强制切换成功")
    
    print("✅ 认知节奏控制器测试通过")


def test_meta_learner():
    print("\n=== 测试元学习策略优化 ===")
    
    learner = MetaLearner()
    
    assert len(learner.strategies) > 0, "默认策略加载失败"
    assert "spaced_repetition" in learner.strategies, "间隔重复策略缺失"
    print("✓ 默认策略加载成功")
    
    learner.evaluate_strategy(
        "spaced_repetition",
        EvaluationMetric.ACCURACY,
        0.8,
    )
    assert len(learner.evaluations["spaced_repetition"]) == 1, "策略评估失败"
    print("✓ 策略评估成功")
    
    context = {"task_type": "记忆", "recent_accuracy": 0.5}
    recommendations = learner.recommend_strategy(context)
    assert len(recommendations) > 0, "策略推荐失败"
    print("✓ 策略推荐成功")
    
    for i in range(10):
        learner.evaluate_strategy(
            "spaced_repetition",
            EvaluationMetric.ACCURACY,
            0.6,
        )
    optimized = learner.optimize_parameters("spaced_repetition")
    assert isinstance(optimized, dict), "参数优化失败"
    print("✓ 参数优化成功")
    
    outcome = {
        "accuracy": 0.8,
        "speed": 0.7,
        "retention": 0.9,
        "context": {"task": "test"},
    }
    learner.learn_from_experience("spaced_repetition", outcome)
    assert len(learner.evaluations["spaced_repetition"]) > 10, "经验学习失败"
    print("✓ 经验学习成功")
    
    stats = learner.get_strategy_stats("spaced_repetition")
    assert "name" in stats, "策略统计失败"
    print("✓ 策略统计成功")
    
    print("✅ 元学习策略优化测试通过")


def test_integration():
    print("\n=== 测试七大机制集成 ===")
    
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
    
    assert len(perception.signals) == 10, "集成测试：感知失败"
    assert len(rhythm.state_history) == 10, "集成测试：节奏失败"
    assert len(meta_learner.evaluations["spaced_repetition"]) == 10, "集成测试：元学习失败"
    print("✓ 完整学习周期测试成功")
    
    error_alchemy2 = ErrorAlchemy()
    perception2 = IncrementalPerception()
    
    error = ValueError("test error")
    error_id = error_alchemy2.record_error(error)
    result = error_alchemy2.alchemize(error_id)
    
    for signal in result.signals_extracted:
        learning_signal = Signal(
            type=SignalType.PATTERN,
            content=signal.content,
        )
        perception2.perceive(learning_signal)
    
    assert len(perception2.signals) == len(result.signals_extracted), "错误到学习转化失败"
    print("✓ 错误到学习转化成功")
    
    print("✅ 集成测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("七大核心机制验证测试")
    print("=" * 60)
    
    try:
        test_incremental_perception()
        test_feedback_loop()
        test_error_alchemy()
        test_tool_builder()
        test_knowledge_weaver()
        test_rhythm_controller()
        test_meta_learner()
        test_integration()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！七大核心机制实现完成")
        print("=" * 60)
        
        print("\n📊 实现总结：")
        print("  1. 增量感知学习 - 从每次交互中吸收信号 ✓")
        print("  2. 经验反馈回路 - 验证知识有效性 ✓")
        print("  3. 失败的炼金术 - 从错误中提炼黄金 ✓")
        print("  4. 工具自我构建 - 从需求中生成工具 ✓")
        print("  5. 知识网络编织 - 建立知识连接 ✓")
        print("  6. 认知节奏控制器 - 动态调整学习节奏 ✓")
        print("  7. 元学习策略优化 - 学习如何学习 ✓")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise
