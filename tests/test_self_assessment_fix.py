"""
测试持续自我评估模块的修复

验证：
- P4: 持久化存储
- P1: 多信号评估逻辑
- P6: 系统集成
- P2: 问题检测逻辑
- P3: 单例实现
- P5: 配置化阈值
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime
import tempfile
import os


def test_p4_persistence():
    """测试P4: 持久化存储"""
    print("\n" + "="*60)
    print("测试 P4: 持久化存储")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_assessment.db"
    
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    assessor = ContinuousSelfAssessment()
    assessor._db_path = db_path
    assessor._init_database()
    
    result = assessor.assess_conversation(
        conversation_id="test_001",
        user_input="什么是机器学习？",
        system_response="机器学习是人工智能的一个分支，它使计算机系统能够从数据中学习和改进，而无需明确编程。",
        context={},
        user_feedback=0.8
    )
    
    assert result.overall_score > 0, "评估结果应该有分数"
    assert db_path.exists(), "数据库文件应该被创建"
    
    from core.presence.self_assessment import get_self_assessment
    new_assessor = ContinuousSelfAssessment()
    new_assessor._db_path = db_path
    new_assessor._load_history_from_db()
    
    assert len(new_assessor.history.results) > 0, "应该能从数据库加载历史"
    
    print("✅ P4 持久化存储测试通过")
    
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_p1_multi_signal_evaluation():
    """测试P1: 多信号评估逻辑"""
    print("\n" + "="*60)
    print("测试 P1: 多信号评估逻辑")
    print("="*60)
    
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    assessor = ContinuousSelfAssessment()
    
    result1 = assessor.assess_conversation(
        conversation_id="test_002",
        user_input="什么是AI？",
        system_response="AI是人工智能。",
        context={'validation': {'status': 'pass'}},
        user_feedback=0.9
    )
    
    result2 = assessor.assess_conversation(
        conversation_id="test_003",
        user_input="什么是AI？",
        system_response="AI是人工智能。",
        context={'validation': {'status': 'fail'}},
        user_feedback=0.3
    )
    
    assert result1.overall_score > result2.overall_score, \
        "校验通过的评估分数应该高于失败的"
    
    result3 = assessor.assess_conversation(
        conversation_id="test_004",
        user_input="什么是AI？",
        system_response="AI是人工智能，包括机器学习、深度学习等技术...",
        context={'knowledge_match': 0.95, 'has_factual_content': True},
        user_feedback=None
    )
    
    assert result3.metrics['accuracy'] > 0.7, \
        "高知识匹配度应该产生高准确性分数"
    
    print("✅ P1 多信号评估逻辑测试通过")


def test_p2_question_detection():
    """测试P2: 问题检测逻辑"""
    print("\n" + "="*60)
    print("测试 P2: 问题检测逻辑")
    print("="*60)
    
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    assessor = ContinuousSelfAssessment()
    
    result = assessor.assess_conversation(
        conversation_id="test_005",
        user_input="如何学习Python？",
        system_response="好的",
        context={},
        user_feedback=None
    )
    
    has_question_insight = any(
        "提问" in insight or "简短" in insight 
        for insight in result.insights
    )
    
    assert has_question_insight, "应该检测到用户提问但响应简短的情况"
    
    print("✅ P2 问题检测逻辑测试通过")


def test_p3_singleton():
    """测试P3: 单例实现"""
    print("\n" + "="*60)
    print("测试 P3: 单例实现")
    print("="*60)
    
    from core.presence.self_assessment import get_self_assessment, _self_assessment
    
    import core.presence.self_assessment as module
    module._self_assessment = None
    
    instance1 = get_self_assessment()
    instance2 = get_self_assessment()
    
    assert instance1 is instance2, "单例应该返回同一个实例"
    
    print("✅ P3 单例实现测试通过")


def test_p5_configurable_thresholds():
    """测试P5: 配置化阈值"""
    print("\n" + "="*60)
    print("测试 P5: 配置化阈值")
    print("="*60)
    
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    custom_config = {
        'score_thresholds': {
            'excellent': 0.9,
            'good': 0.7,
            'needs_improvement': 0.5
        },
        'metric_weights': {
            'accuracy': 0.4,
            'relevance': 0.2,
            'helpfulness': 0.2,
            'clarity': 0.1,
            'timeliness': 0.1
        },
        'min_response_length': 50,
        'question_words': ["?", "吗", "如何"]
    }
    
    assessor = ContinuousSelfAssessment(config=custom_config)
    
    assert assessor.config['score_thresholds']['excellent'] == 0.9, \
        "应该使用自定义阈值"
    assert assessor.config['min_response_length'] == 50, \
        "应该使用自定义最小响应长度"
    
    print("✅ P5 配置化阈值测试通过")


def test_p6_integration():
    """测试P6: 系统集成"""
    print("\n" + "="*60)
    print("测试 P6: 系统集成")
    print("="*60)
    
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    assessor = ContinuousSelfAssessment()
    
    result = assessor.assess_conversation(
        conversation_id="test_006",
        user_input="测试集成",
        system_response="这是一个测试响应，用于验证系统集成功能。",
        context={},
        user_feedback=0.8
    )
    
    assert result is not None, "评估应该成功完成"
    assert len(result.learning_points) > 0, "应该生成学习点"
    
    print("✅ P6 系统集成测试通过")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("持续自我评估模块修复验证")
    print("="*60)
    
    tests = [
        ("P4: 持久化存储", test_p4_persistence),
        ("P1: 多信号评估", test_p1_multi_signal_evaluation),
        ("P2: 问题检测", test_p2_question_detection),
        ("P3: 单例实现", test_p3_singleton),
        ("P5: 配置化阈值", test_p5_configurable_thresholds),
        ("P6: 系统集成", test_p6_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} 测试失败: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: {passed}/{len(tests)} 通过")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)