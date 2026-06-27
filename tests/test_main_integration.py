"""
主流程集成测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_main_flow():
    """测试主流程"""
    print("\n" + "=" * 70)
    print("  测试: 主流程集成")
    print("=" * 70)
    
    from main_integrated import AlliancePioneer
    
    pioneer = AlliancePioneer()
    
    # 测试1: 处理问题
    print("\n【测试1】处理问题")
    result1 = pioneer.process_question("什么是机器学习?", enable_metacognition=True)
    
    print(f"  问题: {result1['question']}")
    print(f"  回答: {result1['response'][:80]}...")
    print(f"  客观分: {result1['objective_score']:.1f}")
    print(f"  意图: {result1['intent']}")
    print(f"  元认知: {'已运行' if result1['metacognition'] else '未运行'}")
    
    # 测试2: 处理反馈
    print("\n【测试2】处理反馈")
    feedback_result = pioneer.handle_feedback(
        question="什么是机器学习?",
        response=result1['response'],
        feedback="回答不错",
        objective_score=result1['objective_score']
    )
    print(f"  反馈类型: {feedback_result['feedback_type']}")
    print(f"  已记录: {feedback_result['recorded']}")
    
    # 测试3: 纠错反馈
    print("\n【测试3】纠错反馈")
    result2 = pioneer.process_question("Python什么时候发布的?", enable_metacognition=False)
    
    correction_result = pioneer.handle_feedback(
        question="Python什么时候发布的?",
        response=result2['response'],
        feedback="不对，应该是1991年发布的",
        objective_score=result2['objective_score']
    )
    print(f"  反馈类型: {correction_result['feedback_type']}")
    print(f"  纠错结果: {correction_result.get('correction_result', {}).get('success', False)}")
    
    # 测试4: 显示统计
    print("\n【测试4】系统统计")
    print(pioneer.show_stats())
    
    # 测试5: 导出训练数据
    print("\n【测试5】导出训练数据")
    count = pioneer.export_training_data("data/test_main_training.json")
    print(f"  导出数量: {count}")
    
    print("\n✅ 主流程集成测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  主流程集成测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        success = test_main_flow()
        print("\n" + "=" * 70)
        print("  ✅ 所有测试通过")
        print("=" * 70)
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)