"""
元认知循环测试
验证完整的"学生自我复盘→老师评估→方法论提炼"流程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_self_reflection():
    """测试自我复盘"""
    print("\n" + "=" * 70)
    print("  测试: 系统自我复盘")
    print("=" * 70)
    
    from core.self_reflection import SelfReflection
    
    reflection = SelfReflection()
    
    # 场景1: 高质量回答
    print("\n【场景1】高质量回答")
    result1 = reflection.reflect_on_interaction(
        question="什么是机器学习?",
        response="机器学习是人工智能的一个分支，通过数据训练模型，使计算机能够从数据中学习规律并做出预测。它包括监督学习、无监督学习、强化学习等多种方法。",
        decision_chain=[
            {'layer': 'L1', 'reasoning': '识别为知识问答'},
            {'layer': 'L2', 'reasoning': '检索事实库'},
            {'layer': 'L3', 'reasoning': '整合知识生成回答'}
        ],
        knowledge_used=['fact_store', 'external_learn'],
        objective_score=80.0
    )
    
    print(f"  做得好的地方: {result1.what_i_did_well}")
    print(f"  可改进的地方: {result1.what_i_could_improve}")
    print(f"  替代方案: {result1.alternative_approaches[:2]}")
    print(f"  不确定性: {result1.uncertainties}")
    print(f"  下次策略: {result1.next_time_strategy}")
    print(f"  置信度: {result1.confidence_level:.2f}")
    print(f"  反思深度: {result1.reflection_depth}")
    
    # 场景2: 低质量回答
    print("\n【场景2】低质量回答")
    result2 = reflection.reflect_on_interaction(
        question="为什么会有冰雹?",
        response="冰雹是一种天气现象。",
        decision_chain=[{'layer': 'L1', 'reasoning': '识别问题'}],
        knowledge_used=[],
        objective_score=30.0
    )
    
    print(f"  做得好的地方: {result2.what_i_did_well}")
    print(f"  可改进的地方: {result2.what_i_could_improve}")
    print(f"  置信度: {result2.confidence_level:.2f}")
    print(f"  反思深度: {result2.reflection_depth}")
    
    print("\n✅ 自我复盘测试通过")
    return True


def test_teacher_interface():
    """测试老师接口"""
    print("\n" + "=" * 70)
    print("  测试: 老师接口（本地评估）")
    print("=" * 70)
    
    from core.teacher_interface import TeacherInterface
    from core.self_reflection import SelfReflection
    
    teacher = TeacherInterface()  # 无API Key，使用本地评估
    reflection = SelfReflection()
    
    # 先自我复盘
    self_result = reflection.reflect_on_interaction(
        question="Python有什么特点?",
        response="Python是一种编程语言。",
        objective_score=40.0
    )
    
    # 转换为字典
    self_dict = reflection.to_dict(self_result)
    
    # 请求老师评估
    print("\n【请求老师评估】")
    feedback = teacher.request_feedback(
        question="Python有什么特点?",
        response="Python是一种编程语言。",
        self_reflection=self_dict,
        objective_score=40.0
    )
    
    print(f"  问题拆解能力: {feedback.get('problem_decomposition', 'N/A')}")
    print(f"  分析框架: {feedback.get('analysis_framework', 'N/A')}")
    print(f"  假设检验: {feedback.get('hypothesis_testing', 'N/A')}")
    print(f"  知识运用: {feedback.get('knowledge_application', 'N/A')}")
    print(f"  改进建议: {feedback.get('improvement_suggestions', [])}")
    print(f"  学习方向: {feedback.get('learning_directions', [])}")
    
    print("\n✅ 老师接口测试通过")
    return True


def test_methodology_extraction():
    """测试方法论提取"""
    print("\n" + "=" * 70)
    print("  测试: 方法论提取")
    print("=" * 70)
    
    from core.methodology_extractor import MethodologyExtractor
    from core.self_reflection import SelfReflection
    
    extractor = MethodologyExtractor(db_path="data/test_methodologies.db")
    reflection = SelfReflection()
    
    # 模拟老师反馈
    teacher_feedback = {
        'problem_decomposition': 5,
        'analysis_framework': 6,
        'hypothesis_testing': 7,
        'knowledge_application': 6,
        'improvement_suggestions': [
            "需要更好地拆解复杂问题",
            "建立更清晰的分析框架"
        ],
        'learning_directions': ["加强逻辑思维训练"],
        'methodology': "系统化分析问题"
    }
    
    # 自我复盘
    self_result = reflection.reflect_on_interaction(
        question="为什么会有冰雹?",
        response="冰雹是一种天气现象。",
        objective_score=40.0
    )
    
    # 提取方法论
    print("\n【提取方法论】")
    methodologies = extractor.extract_methodology(
        teacher_feedback=teacher_feedback,
        question="为什么会有冰雹?",
        response="冰雹是一种天气现象。",
        self_reflection=reflection.to_dict(self_result)
    )
    
    print(f"  提取数量: {len(methodologies)}")
    
    for i, method in enumerate(methodologies, 1):
        print(f"\n  方法论{i}: {method.name}")
        print(f"    描述: {method.description}")
        print(f"    触发条件: {method.trigger_conditions[:2]}")
        print(f"    应用步骤: {method.application_steps[:2]}")
    
    # 获取相关方法论
    print("\n【获取相关方法论】")
    relevant = extractor.get_relevant_methodologies("为什么会有冰雹?")
    print(f"  相关方法论数: {len(relevant)}")
    
    # 统计
    stats = extractor.get_statistics()
    print(f"\n【统计】")
    print(f"  总方法论数: {stats['total_methodologies']}")
    print(f"  平均效果分: {stats['avg_effectiveness']:.2f}")
    
    print("\n✅ 方法论提取测试通过")
    return True


def test_full_metacognition_loop():
    """测试完整的元认知循环"""
    print("\n" + "=" * 70)
    print("  测试: 完整元认知循环")
    print("=" * 70)
    
    from core.self_reflection import SelfReflection
    from core.teacher_interface import TeacherInterface
    from core.methodology_extractor import MethodologyExtractor
    
    reflection = SelfReflection()
    teacher = TeacherInterface()
    extractor = MethodologyExtractor(db_path="data/test_metacognition.db")
    
    question = "深度学习和机器学习有什么区别?"
    response = "深度学习是机器学习的一种。"
    
    # 步骤1: 自我复盘
    print("\n【步骤1】系统自我复盘")
    self_result = reflection.reflect_on_interaction(
        question=question,
        response=response,
        objective_score=50.0
    )
    print(f"  反思深度: {self_result.reflection_depth}")
    print(f"  可改进: {len(self_result.what_i_could_improve)} 点")
    
    # 步骤2: 老师评估
    print("\n【步骤2】老师评估")
    feedback = teacher.request_feedback(
        question=question,
        response=response,
        self_reflection=reflection.to_dict(self_result),
        objective_score=50.0
    )
    print(f"  问题拆解: {feedback.get('problem_decomposition', 'N/A')}/10")
    print(f"  分析框架: {feedback.get('analysis_framework', 'N/A')}/10")
    
    # 步骤3: 提炼方法论
    print("\n【步骤3】提炼方法论")
    methodologies = extractor.extract_methodology(
        teacher_feedback=feedback,
        question=question,
        response=response,
        self_reflection=reflection.to_dict(self_result)
    )
    print(f"  提炼数量: {len(methodologies)}")
    
    # 步骤4: 制定下次策略
    print("\n【步骤4】下次策略")
    print(f"  {self_result.next_time_strategy}")
    
    print("\n✅ 完整元认知循环测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  元认知循环测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("自我复盘", test_self_reflection),
        ("老师接口", test_teacher_interface),
        ("方法论提取", test_methodology_extraction),
        ("完整元认知循环", test_full_metacognition_loop),
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