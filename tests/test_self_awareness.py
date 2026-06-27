"""
自我认知能力验证测试
验证决策链、内省引擎、能力缺口诊断器
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_decision_chain():
    """测试决策链"""
    print("\n" + "=" * 70)
    print("  测试1: 决策链记录系统")
    print("=" * 70)
    
    from core.decision_chain import DecisionChainManager
    
    manager = DecisionChainManager()
    
    # 开始新决策链
    chain = manager.start_new_chain()
    
    # 添加决策步骤
    chain.add_step(
        layer="L1",
        layer_name="感知层",
        input_data="用户问: 什么是AI?",
        output_data="识别为知识问答",
        reasoning="关键词匹配: '什么是', 'AI'",
        confidence=0.9
    )
    
    chain.add_step(
        layer="L2",
        layer_name="理解层",
        input_data="知识问答: AI",
        output_data="查询事实库",
        reasoning="事实性问题，需要客观知识",
        confidence=0.85
    )
    
    chain.add_step(
        layer="L3",
        layer_name="推理层",
        input_data="查询结果: AI定义",
        output_data="AI是人工智能...",
        reasoning="从事实库检索到定义",
        confidence=0.8
    )
    
    chain.set_final_output("AI是人工智能，是计算机科学的一个分支。", 0.85)
    
    # 完成决策链
    manager.complete_chain()
    
    # 可视化
    print(chain.visualize(detailed=True))
    
    # 统计
    stats = manager.get_statistics()
    print(f"\n决策链统计: {stats}")
    
    print("\n✅ 决策链测试通过")
    return True


def test_introspection_engine():
    """测试内省引擎"""
    print("\n" + "=" * 70)
    print("  测试2: 内省引擎")
    print("=" * 70)
    
    from core.learning_reflector import LearningReflector
    
    engine = LearningReflector(db_path="data/test_reflection.db")
    
    # 记录学习事件
    event1 = engine.record_learning_event(
        event_type="external_learn",
        question="什么是深度学习?",
        action_taken="从Wikipedia获取知识",
        result="success",
        knowledge_gained=2,
        confidence_before=30.0,
        confidence_after=60.0
    )
    print(f"✓ 学习事件已记录: {event1}")
    
    event2 = engine.record_learning_event(
        event_type="injection",
        question="Python有什么特点?",
        action_taken="注入知识到事实库",
        result="partial",
        knowledge_gained=1,
        confidence_before=40.0,
        confidence_after=50.0
    )
    print(f"✓ 学习事件已记录: {event2}")
    
    # 反思单个事件
    reflection = engine.reflect_on_learning(event1)
    print(f"\n✓ 事件反思:")
    print(f"  效果评分: {reflection['effectiveness']['rating']}")
    print(f"  改进建议: {reflection['improvement_suggestions']}")
    
    # 生成学习报告
    report = engine.generate_learning_report(period="day")
    print(f"\n{engine.format_report(report)}")
    
    print("\n✅ 内省引擎测试通过")
    return True


def test_capability_gap_diagnoser():
    """测试能力缺口诊断器"""
    print("\n" + "=" * 70)
    print("  测试3: 能力缺口诊断器")
    print("=" * 70)
    
    from core.capability_gap_diagnoser import CapabilityGapDiagnoser
    
    diagnoser = CapabilityGapDiagnoser(db_path="data/test_gaps.db")
    
    # 记录一些交互
    test_interactions = [
        ("请识别这张图片中的文字", False, 0.2),
        ("帮我分析这张照片", False, 0.1),
        ("听这段音频说什么", False, 0.0),
        ("运行这段Python代码", False, 0.3),
        ("计算这个积分", False, 0.4),
        ("什么是机器学习?", True, 0.8),
        ("推荐一本AI书籍", False, 0.5),
    ]
    
    for question, success, confidence in test_interactions:
        diagnoser.record_interaction(
            question=question,
            response="测试回答" if success else "无法回答",
            success=success,
            confidence=confidence,
            failure_type=None if success else "capability_gap"
        )
    
    print(f"✓ 已记录 {len(test_interactions)} 次交互")
    
    # 诊断
    report = diagnoser.diagnose(period="day")
    print(f"\n{diagnoser.format_report(report)}")
    
    print("\n✅ 能力缺口诊断器测试通过")
    return True


def test_introspection_commands():
    """测试内省命令"""
    print("\n" + "=" * 70)
    print("  测试4: 内省命令")
    print("=" * 70)
    
    from core.introspection_commands import introspection_commands
    
    # 测试 :help
    result = introspection_commands.handle_command(":help")
    print(f"\n【:help 命令】")
    print(result[:300] + "...")
    
    # 测试 :stats
    result = introspection_commands.handle_command(":stats")
    print(f"\n【:stats 命令】")
    print(result)
    
    # 测试 :reflect
    result = introspection_commands.handle_command(":reflect day")
    print(f"\n【:reflect day 命令】")
    print(result[:400] + "...")
    
    print("\n✅ 内省命令测试通过")
    return True


def test_full_integration():
    """测试完整集成"""
    print("\n" + "=" * 70)
    print("  测试5: 完整集成测试")
    print("=" * 70)
    
    from core.decision_chain import decision_chain_manager
    from core.learning_reflector import learning_reflector
    from core.capability_gap_diagnoser import capability_gap_diagnoser
    
    # 模拟一次完整交互
    chain = decision_chain_manager.start_new_chain()
    
    # L1: 感知
    chain.add_step(
        layer="L1",
        layer_name="感知层",
        input_data="用户: 什么是强化学习?",
        output_data="意图: 知识问答",
        reasoning="关键词: '什么是', '强化学习'",
        confidence=0.9
    )
    
    # L2: 理解
    chain.add_step(
        layer="L2",
        layer_name="理解层",
        input_data="知识问答: 强化学习",
        output_data="需要外部知识",
        reasoning="事实库未找到，需要学习",
        confidence=0.7
    )
    
    # L3: 学习
    chain.add_step(
        layer="L3",
        layer_name="学习层",
        input_data="查询: 强化学习",
        output_data="获取Wikipedia知识",
        reasoning="触发外部学习器",
        confidence=0.8
    )
    
    # L4: 推理
    chain.add_step(
        layer="L4",
        layer_name="推理层",
        input_data="知识: 强化学习定义",
        output_data="生成回答",
        reasoning="整合知识生成回答",
        confidence=0.85
    )
    
    chain.set_final_output(
        "强化学习是机器学习的一种方法，通过与环境交互学习最优策略。",
        0.82
    )
    
    decision_chain_manager.complete_chain()
    
    # 记录学习事件
    learning_reflector.record_learning_event(
        event_type="external_learn",
        question="什么是强化学习?",
        action_taken="从Wikipedia获取知识并注入",
        result="success",
        knowledge_gained=1,
        confidence_before=30.0,
        confidence_after=82.0
    )
    
    # 记录交互
    capability_gap_diagnoser.record_interaction(
        question="什么是强化学习?",
        response=chain.final_output,
        success=True,
        confidence=0.82
    )
    
    print("✓ 完整交互流程已记录")
    
    # 查看决策链
    print(f"\n【决策链】")
    last_chain = decision_chain_manager.get_last_chain()
    print(last_chain.visualize())
    
    # 查看统计
    print(f"\n【统计信息】")
    chain_stats = decision_chain_manager.get_statistics()
    print(f"  决策链: {chain_stats['total_chains']} 条")
    print(f"  平均置信度: {chain_stats['avg_confidence']:.2f}")
    
    print("\n✅ 完整集成测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  自我认知能力验证测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("决策链记录系统", test_decision_chain),
        ("内省引擎", test_introspection_engine),
        ("能力缺口诊断器", test_capability_gap_diagnoser),
        ("内省命令", test_introspection_commands),
        ("完整集成", test_full_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ 通过", None))
        except Exception as e:
            results.append((name, "❌ 失败", str(e)))
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)
    
    for name, status, error in results:
        print(f"{status} {name}")
        if error:
            print(f"     错误: {error[:100]}")
    
    passed = sum(1 for _, status, _ in results if "通过" in status)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)