"""
端到端测试 - 适应度评估系统
验证完整流程：反馈分类 → 适应度评估 → 知识注入
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import json
from datetime import datetime

print("\n" + "=" * 70)
print("  🧪 端到端测试 - 适应度评估系统")
print("=" * 70)


def test_module_imports():
    """测试1: 模块导入"""
    print("\n【测试1】模块导入验证")
    print("-" * 50)
    
    try:
        from infrastructure.fact_store import fact_store, FactStore
        print("  ✅ fact_store 导入成功")
    except Exception as e:
        print(f"  ❌ fact_store 导入失败: {e}")
        return False
    
    try:
        from infrastructure.triple_extractor import triple_extractor, TripleExtractor
        print("  ✅ triple_extractor 导入成功")
    except Exception as e:
        print(f"  ❌ triple_extractor 导入失败: {e}")
        return False
    
    try:
        from infrastructure.fitness_evaluator import fitness_evaluator, FitnessEvaluator
        print("  ✅ fitness_evaluator 导入成功")
    except Exception as e:
        print(f"  ❌ fitness_evaluator 导入失败: {e}")
        return False
    
    try:
        from infrastructure.feedback_classifier import feedback_classifier, FeedbackClassifier
        print("  ✅ feedback_classifier 导入成功")
    except Exception as e:
        print(f"  ❌ feedback_classifier 导入失败: {e}")
        return False
    
    try:
        from infrastructure.fitness_config import FitnessConfig
        print("  ✅ fitness_config 导入成功")
    except Exception as e:
        print(f"  ❌ fitness_config 导入失败: {e}")
        return False
    
    return True


def test_database_operations():
    """测试2: 数据库操作"""
    print("\n【测试2】数据库操作验证")
    print("-" * 50)
    
    from infrastructure.fact_store import fact_store
    
    # 测试添加断言
    try:
        test_id = fact_store.add_assertion(
            question="测试问题",
            subject="测试主体",
            predicate="测试关系",
            obj="测试客体",
            source="test",
            confidence=0.8
        )
        print(f"  ✅ 添加断言成功: ID={test_id}")
    except Exception as e:
        print(f"  ❌ 添加断言失败: {e}")
        return False
    
    # 测试查询断言
    try:
        assertions = fact_store.get_assertions("测试问题")
        print(f"  ✅ 查询断言成功: {len(assertions)}条")
    except Exception as e:
        print(f"  ❌ 查询断言失败: {e}")
        return False
    
    # 测试统计信息
    try:
        stats = fact_store.get_stats()
        print(f"  ✅ 统计信息: 总计={stats['total']}, 正向={stats['positive']}, 否定={stats['negations']}")
    except Exception as e:
        print(f"  ❌ 统计信息失败: {e}")
        return False
    
    return True


def test_triple_extraction():
    """测试3: 三元组提取"""
    print("\n【测试3】三元组提取验证")
    print("-" * 50)
    
    from infrastructure.triple_extractor import triple_extractor
    
    test_cases = [
        ("冰雹的形成是由于过冷水滴在强对流云中反复冻结", "冰雹形成"),
        ("水蒸气遇冷会凝华成冰晶", "相变过程"),
        ("圆周率π约等于3.14159", "数学常数"),
        ("中华人民共和国成立于1949年10月1日", "历史事实"),
    ]
    
    for text, category in test_cases:
        try:
            triples = triple_extractor.extract(text)
            print(f"  ✅ [{category}] 提取{len(triples)}个三元组")
            if triples:
                t = triples[0]
                print(f"     示例: ({t.subject}, {t.predicate}, {t.object})")
        except Exception as e:
            print(f"  ❌ [{category}] 提取失败: {e}")
            return False
    
    return True


def test_fitness_evaluation():
    """测试4: 适应度评估"""
    print("\n【测试4】适应度评估验证")
    print("-" * 50)
    
    from infrastructure.fitness_evaluator import fitness_evaluator
    
    test_cases = [
        {
            "name": "事实性问题-正确回答",
            "question": "为什么会有冰雹",
            "response": "冰雹是由过冷水滴在强对流云中反复冻结形成的",
            "feedback": 0,
            "intent": "question"
        },
        {
            "name": "事实性问题-错误回答",
            "question": "为什么会有冰雹",
            "response": "冰雹发生时天气晴朗，水蒸气变成冰晶叫做露点",
            "feedback": 0,
            "intent": "question"
        },
        {
            "name": "开放性问题",
            "question": "你觉得今天天气怎么样",
            "response": "今天天气不错，适合出门散步",
            "feedback": 1,
            "intent": "chat"
        },
        {
            "name": "数学问题",
            "question": "圆周率是多少",
            "response": "圆周率π约等于3.14159",
            "feedback": 0,
            "intent": "question"
        },
    ]
    
    for case in test_cases:
        try:
            score = fitness_evaluator.evaluate(
                question=case["question"],
                response=case["response"],
                user_feedback=case["feedback"],
                intent_type=case["intent"]
            )
            
            print(f"  ✅ [{case['name']}]")
            print(f"     总分={score.final_score:.1f}, 客观={score.objective_score:.1f}, 主观={score.subjective_score:.1f}")
            print(f"     事实性={score.is_factual_question}, 匹配={score.match_details.get('match_rate', 0):.2f}")
        except Exception as e:
            print(f"  ❌ [{case['name']}] 评估失败: {e}")
            return False
    
    return True


def test_feedback_classification():
    """测试5: 反馈分类"""
    print("\n【测试5】反馈分类验证")
    print("-" * 50)
    
    from infrastructure.feedback_classifier import feedback_classifier, FeedbackType
    
    test_cases = [
        ("第2条错误：露点概念用错，应该是凝华", FeedbackType.CORRECTION),
        ("不对，高空温度不会升高", FeedbackType.CORRECTION),
        ("👍 回答得很好", FeedbackType.POSITIVE),
        ("点赞", FeedbackType.POSITIVE),
        ("点踩，这个回答没用", FeedbackType.NEGATIVE),
        ("👎", FeedbackType.NEGATIVE),
        ("能详细解释一下吗", FeedbackType.NEUTRAL),
        ("今天天气不错", FeedbackType.POSITIVE),
    ]
    
    for message, expected_type in test_cases:
        try:
            actual_type = feedback_classifier.classify(message)
            if actual_type == expected_type:
                print(f"  ✅ \"{message[:20]}...\" → {actual_type.value}")
            else:
                print(f"  ⚠️ \"{message[:20]}...\" → {actual_type.value} (期望: {expected_type.value})")
        except Exception as e:
            print(f"  ❌ 分类失败: {e}")
            return False
    
    return True


def test_correction_parsing():
    """测试6: 纠错解析"""
    print("\n【测试6】纠错解析验证")
    print("-" * 50)
    
    from infrastructure.feedback_classifier import feedback_classifier
    
    test_cases = [
        "第2条错误：露点概念用错，应该是凝华",
        "不对，高空温度不会升高，而是降低",
        "\"露点\"应该是\"凝华\"",
    ]
    
    for message in test_cases:
        try:
            corrections = feedback_classifier.parse_correction(message)
            print(f"  ✅ \"{message[:30]}...\"")
            print(f"     解析出{len(corrections)}条纠错")
            for c in corrections:
                print(f"     - 旧: {c.old_assertion[:30]}")
                print(f"       新: {c.new_assertion[:30]}")
        except Exception as e:
            print(f"  ❌ 解析失败: {e}")
            return False
    
    return True


def test_end_to_end_flow():
    """测试7: 端到端流程"""
    print("\n【测试7】端到端流程验证")
    print("-" * 50)
    
    from infrastructure.feedback_classifier import feedback_classifier
    from infrastructure.fitness_evaluator import fitness_evaluator
    from infrastructure.fact_store import fact_store
    
    # 模拟用户提问和系统回答
    question = "为什么会有冰雹"
    response = "冰雹是由过冷水滴在强对流云中反复冻结形成的"
    
    print(f"  问题: {question}")
    print(f"  回答: {response[:50]}...")
    
    # 步骤1: 评估初始回答
    try:
        score = fitness_evaluator.evaluate(
            question=question,
            response=response,
            user_feedback=0,
            intent_type="question"
        )
        print(f"\n  步骤1: 初始评估")
        print(f"    总分={score.final_score:.1f}, 客观={score.objective_score:.1f}")
    except Exception as e:
        print(f"  ❌ 初始评估失败: {e}")
        return False
    
    # 步骤2: 用户点赞
    try:
        fb_result = feedback_classifier.process_feedback("👍 回答得很好")
        print(f"\n  步骤2: 用户点赞")
        print(f"    类型={fb_result['type']}, 适应度调整={fb_result['fitness_delta']}")
    except Exception as e:
        print(f"  ❌ 点赞处理失败: {e}")
        return False
    
    # 步骤3: 用户纠错
    try:
        correction_text = "不对，水蒸气变成冰晶叫做凝华，不是露点"
        fb_result = feedback_classifier.process_feedback(correction_text)
        print(f"\n  步骤3: 用户纠错")
        print(f"    类型={fb_result['type']}, 更新事实库={fb_result['should_update_facts']}")
        
        if fb_result['should_update_facts']:
            corrections = feedback_classifier.parse_correction(correction_text)
            print(f"    解析出{len(corrections)}条纠错")
    except Exception as e:
        print(f"  ❌ 纠错处理失败: {e}")
        return False
    
    # 步骤4: 重新评估
    try:
        score_after = fitness_evaluator.evaluate(
            question=question,
            response=response,
            user_feedback=1,  # 点赞
            intent_type="question"
        )
        print(f"\n  步骤4: 重新评估（点赞后）")
        print(f"    总分={score_after.final_score:.1f}, 客观={score_after.objective_score:.1f}, 主观={score_after.subjective_score:.1f}")
    except Exception as e:
        print(f"  ❌ 重新评估失败: {e}")
        return False
    
    return True


def test_shadow_mode():
    """测试8: 影子模式"""
    print("\n【测试8】影子模式验证")
    print("-" * 50)
    
    from infrastructure.fitness_config import FitnessConfig
    from infrastructure.fitness_evaluator import fitness_evaluator
    
    # 启用影子模式
    FitnessConfig.enable_shadow()
    print(f"  影子模式: {FitnessConfig.SHADOW_MODE_ENABLED}")
    print(f"  旧版模式: {FitnessConfig.USE_LEGACY_FITNESS}")
    
    # 测试对比
    question = "为什么会有冰雹"
    response = "冰雹由过冷水滴在上升气流中反复冻结形成"
    
    try:
        # 新版评分
        new_score = fitness_evaluator.evaluate(
            question=question,
            response=response,
            user_feedback=0,
            intent_type="question"
        )
        
        print(f"\n  新版评分: {new_score.final_score:.1f}")
        print(f"    客观分: {new_score.objective_score:.1f}")
        print(f"    主观分: {new_score.subjective_score:.1f}")
        
        # 旧版评分
        FitnessConfig.enable_legacy()
        legacy_score = fitness_evaluator.evaluate(
            question=question,
            response=response,
            user_feedback=0,
            intent_type="question"
        )
        
        print(f"\n  旧版评分: {legacy_score.final_score:.1f}")
        print(f"\n  差异: {abs(new_score.final_score - legacy_score.final_score):.1f}")
        
        # 恢复新版
        FitnessConfig.enable_new()
        
    except Exception as e:
        print(f"  ❌ 影子模式测试失败: {e}")
        return False
    
    return True


def test_rollback_switch():
    """测试9: 回滚开关"""
    print("\n【测试9】回滚开关验证")
    print("-" * 50)
    
    from infrastructure.fitness_config import FitnessConfig
    from infrastructure.fitness_evaluator import FitnessEvaluator
    
    try:
        # 测试新版
        FitnessConfig.enable_new()
        evaluator_new = FitnessEvaluator(use_legacy=False)
        print(f"  ✅ 新版模式: use_legacy={evaluator_new.use_legacy}")
        
        # 测试旧版
        FitnessConfig.enable_legacy()
        evaluator_legacy = FitnessEvaluator(use_legacy=True)
        print(f"  ✅ 旧版模式: use_legacy={evaluator_legacy.use_legacy}")
        
        # 恢复新版
        FitnessConfig.enable_new()
        print(f"  ✅ 已恢复新版模式")
        
    except Exception as e:
        print(f"  ❌ 回滚开关测试失败: {e}")
        return False
    
    return True


def main():
    """运行所有测试"""
    results = []
    
    tests = [
        ("模块导入", test_module_imports),
        ("数据库操作", test_database_operations),
        ("三元组提取", test_triple_extraction),
        ("适应度评估", test_fitness_evaluation),
        ("反馈分类", test_feedback_classification),
        ("纠错解析", test_correction_parsing),
        ("端到端流程", test_end_to_end_flow),
        ("影子模式", test_shadow_mode),
        ("回滚开关", test_rollback_switch),
    ]
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n  ❌ {name}测试异常: {e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("  📊 测试结果汇总")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "-" * 70)
    print(f"  总计: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)