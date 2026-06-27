"""
端到端能力验证测试
验证完整的"感知→学习→验证→修正"闭环
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import json


def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_1_fact_store():
    """测试1: 事实库存储和检索"""
    print_section("测试1: 事实库存储和检索")
    
    from infrastructure.fact_store import fact_store
    
    test_assertion = {
        'subject': '端到端测试',
        'predicate': '测试类型',
        'object': '验证测试',
        'confidence': 0.95,
        'source': 'e2e_test'
    }
    
    assertion_id = fact_store.assert_fact(**test_assertion)
    print(f"✓ 断言已存储: ID={assertion_id}")
    
    retrieved = fact_store.get_assertion(assertion_id)
    print(f"✓ 断言已检索: {retrieved['subject']} -> {retrieved['predicate']} -> {retrieved['object']}")
    print(f"  置信度: {retrieved['confidence']}, 来源: {retrieved['source']}")
    
    stats = fact_store.get_stats()
    print(f"✓ 事实库统计: 总计{stats['total_assertions']}条断言")
    
    return True


def test_2_triple_extractor():
    """测试2: 三元组提取"""
    print_section("测试2: 三元组提取")
    
    from infrastructure.triple_extractor import triple_extractor
    
    test_cases = [
        "Python是一种编程语言",
        "机器学习是人工智能的核心技术",
        "深度学习使用神经网络进行特征学习"
    ]
    
    for text in test_cases:
        triples = triple_extractor.extract(text)
        print(f"✓ 文本: {text}")
        for triple in triples:
            print(f"  三元组: ({triple['subject']}, {triple['predicate']}, {triple['object']})")
    
    return True


def test_3_fitness_evaluator():
    """测试3: 适应度评估"""
    print_section("测试3: 适应度评估 (客观分60% + 主观分40%)")
    
    from infrastructure.fitness_evaluator import FitnessEvaluator
    
    evaluator = FitnessEvaluator()
    
    test_cases = [
        {
            'question': "Python的创始人是谁？",
            'response': "Python的创始人是Guido van Rossum，他在1991年发布了Python。",
            'feedback': 1
        },
        {
            'question': "什么是机器学习？",
            'response': "机器学习是人工智能的一个分支，通过数据训练模型。",
            'feedback': 0
        },
        {
            'question': "今天天气怎么样？",
            'response': "这是一个开放性问题，需要具体位置信息。",
            'feedback': 0
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        result = evaluator.evaluate(
            question=case['question'],
            response=case['response'],
            user_feedback=case['feedback']
        )
        
        print(f"\n案例{i}: {case['question'][:30]}...")
        print(f"  客观分: {result.objective_score:.1f} (权重60%)")
        print(f"  主观分: {result.subjective_score:.1f} (权重40%)")
        print(f"  总分: {result.final_score:.1f}")
        print(f"  事实性问题: {result.is_factual_question}")
    
    return True


def test_4_feedback_classifier():
    """测试4: 反馈分类器"""
    print_section("测试4: 反馈分类 (识别纠错/补充/确认)")
    
    from infrastructure.feedback_classifier import FeedbackClassifier
    
    classifier = FeedbackClassifier()
    
    test_feedbacks = [
        "不对，Python是1991年发布的，不是1990年",
        "补充一点，Python还支持函数式编程",
        "回答正确，很详细",
        "这个答案有问题，机器学习不只是AI的分支",
        "好的，谢谢"
    ]
    
    for feedback in test_feedbacks:
        result = classifier.classify(feedback)
        print(f"\n反馈: {feedback[:40]}...")
        print(f"  类型: {result['type']}")
        print(f"  置信度: {result['confidence']:.2f}")
        if result.get('correction_content'):
            print(f"  纠错内容: {result['correction_content'][:50]}")
    
    return True


def test_5_external_learners():
    """测试5: 外部学习器"""
    print_section("测试5: 外部学习器 (Wikipedia + DuckDuckGo)")
    
    from infrastructure.external_learners import (
        WikipediaLearner,
        DDGSearchLearner,
        CompositeLearner
    )
    
    wiki = WikipediaLearner(language="zh")
    ddg = DDGSearchLearner(region="cn-zh")
    composite = CompositeLearner([wiki, ddg])
    
    print(f"\nWikipedia可用: {wiki.is_available()}")
    print(f"DuckDuckGo可用: {ddg.is_available()}")
    print(f"组合学习器可用: {composite.is_available()}")
    
    if composite.is_available():
        results = composite.learn("人工智能", max_results=3)
        print(f"\n查询 '人工智能' 获取到 {len(results)} 条知识:")
        for i, item in enumerate(results, 1):
            print(f"  {i}. [{item.source}] {item.content[:60]}...")
            print(f"     置信度: {item.confidence:.2f}")
    
    return True


def test_6_injection_verifier():
    """测试6: 注入效果验证"""
    print_section("测试6: 注入效果验证")
    
    from infrastructure.injection_verifier import InjectionVerifier
    
    verifier = InjectionVerifier(db_path="data/e2e_verifications.db")
    
    test_cases = [
        {
            'id': 'e2e_test_001',
            'question': '什么是深度学习？',
            'before': 25.0,
            'knowledge': [
                {'content': '深度学习是机器学习的分支', 'confidence': 0.9},
                {'content': '深度学习使用多层神经网络', 'confidence': 0.85}
            ]
        },
        {
            'id': 'e2e_test_002',
            'question': 'Python有什么特点？',
            'before': 35.0,
            'knowledge': [
                {'content': 'Python是动态类型语言', 'confidence': 0.8}
            ]
        }
    ]
    
    for case in test_cases:
        result = verifier.verify_injection(
            injection_id=case['id'],
            question=case['question'],
            before_score=case['before'],
            injected_knowledge=case['knowledge'],
            improvement_threshold=5.0
        )
        
        print(f"\n验证ID: {result.injection_id}")
        print(f"  问题: {result.question}")
        print(f"  注入前: {result.before_score:.1f} → 注入后: {result.after_score:.1f}")
        print(f"  改进: {result.improvement:.1f} 分")
        print(f"  通过: {'✅' if result.passed else '❌'}")
    
    stats = verifier.get_verification_stats()
    print(f"\n验证统计:")
    print(f"  总验证: {stats['total_verifications']} 次")
    print(f"  通过率: {stats['pass_rate']:.1%}")
    print(f"  平均改进: {stats['avg_improvement']:.1f} 分")
    
    return True


def test_7_full_loop():
    """测试7: 完整学习闭环"""
    print_section("测试7: 完整学习闭环 (感知→学习→验证→修正)")
    
    from infrastructure.fitness_evaluator import FitnessEvaluator
    from infrastructure.knowledge_injector_trigger import KnowledgeInjector
    from infrastructure.injection_verifier import injection_verifier
    
    evaluator = FitnessEvaluator()
    injector = KnowledgeInjector(enable_verification=True)
    
    question = "什么是强化学习？"
    response = "强化学习是一种机器学习方法。"
    
    print(f"\n【步骤1: 感知】")
    print(f"问题: {question}")
    print(f"回答: {response}")
    
    print(f"\n【步骤2: 评估】")
    fitness = evaluator.evaluate(question=question, response=response, user_feedback=0)
    print(f"客观分: {fitness.objective_score:.1f}")
    print(f"总分: {fitness.final_score:.1f}")
    
    print(f"\n【步骤3: 判断】")
    should_inject, reason = injector.should_inject(
        objective_score=fitness.objective_score,
        total_score=fitness.final_score
    )
    print(f"需要注入: {should_inject}")
    print(f"原因: {reason}")
    
    if should_inject:
        print(f"\n【步骤4: 学习】")
        result = injector.inject_for_question(
            question=question,
            response=response,
            objective_score=fitness.objective_score,
            source="e2e_full_test"
        )
        print(f"执行动作: {result['actions_taken']}")
        print(f"注入知识数: {result.get('knowledge_count', 0)}")
        
        if 'verification' in result:
            print(f"\n【步骤5: 验证】")
            ver = result['verification']
            print(f"验证通过: {'✅' if ver['passed'] else '❌'}")
            print(f"改进分数: {ver['improvement']:.1f}")
            
            if not ver['passed']:
                print(f"\n【步骤6: 修正】")
                suggestions = injection_verifier.suggest_corrections()
                print(f"修正建议: {len(suggestions)} 条")
    
    return True


def test_8_fact_store_v2():
    """测试8: 版本控制事实库"""
    print_section("测试8: 版本控制事实库 (覆盖机制)")
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2(db_path="data/e2e_fact_store_v2.db")
    
    print(f"\n【测试覆盖机制】")
    
    id1 = store.assert_fact(
        subject="测试实体",
        predicate="属性",
        obj="旧值",
        confidence=0.7,
        source="initial"
    )
    print(f"✓ 初始断言: ID={id1}, 值='旧值', 置信度=0.7")
    
    id2 = store.assert_fact(
        subject="测试实体",
        predicate="属性",
        obj="新值",
        confidence=0.9,
        source="correction"
    )
    print(f"✓ 覆盖断言: ID={id2}, 值='新值', 置信度=0.9")
    
    current = store.get_current_fact("测试实体", "属性")
    print(f"✓ 当前值: {current['object']} (置信度={current['confidence']})")
    
    history = store.get_fact_history("测试实体", "属性")
    print(f"✓ 历史版本: {len(history)} 条")
    for h in history:
        print(f"  - {h['object']} (来源={h['source']}, 置信度={h['confidence']})")
    
    return True


def test_9_integration_stats():
    """测试9: 集成统计"""
    print_section("测试9: 集成统计")
    
    from infrastructure.fact_store import fact_store
    from infrastructure.injection_verifier import injection_verifier
    
    fact_stats = fact_store.get_stats()
    print(f"\n事实库统计:")
    print(f"  总断言数: {fact_stats['total_assertions']}")
    print(f"  来源分布: {fact_stats.get('sources', {})}")
    
    ver_stats = injection_verifier.get_verification_stats()
    print(f"\n验证统计:")
    print(f"  总验证数: {ver_stats['total_verifications']}")
    print(f"  通过率: {ver_stats['pass_rate']:.1%}")
    print(f"  平均改进: {ver_stats['avg_improvement']:.1f}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  端到端能力验证测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("事实库存储", test_1_fact_store),
        ("三元组提取", test_2_triple_extractor),
        ("适应度评估", test_3_fitness_evaluator),
        ("反馈分类", test_4_feedback_classifier),
        ("外部学习器", test_5_external_learners),
        ("注入验证", test_6_injection_verifier),
        ("完整闭环", test_7_full_loop),
        ("版本控制", test_8_fact_store_v2),
        ("集成统计", test_9_integration_stats),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ 通过", None))
        except Exception as e:
            results.append((name, "❌ 失败", str(e)))
    
    print_section("测试结果汇总")
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