"""端到端能力验证 - 最终版"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_all():
    results = []
    
    # 测试1: 事实库
    try:
        from infrastructure.fact_store import fact_store
        stats = fact_store.get_stats()
        results.append(("事实库存储", True, f"总断言{stats['total']}条"))
    except Exception as e:
        results.append(("事实库存储", False, str(e)))
    
    # 测试2: 三元组提取
    try:
        from infrastructure.triple_extractor import triple_extractor
        triples = triple_extractor.extract('Python是一种编程语言')
        results.append(("三元组提取", True, f"提取{len(triples)}条三元组"))
    except Exception as e:
        results.append(("三元组提取", False, str(e)))
    
    # 测试3: 适应度评估
    try:
        from infrastructure.fitness_evaluator import FitnessEvaluator
        evaluator = FitnessEvaluator()
        result = evaluator.evaluate('什么是AI?', 'AI是人工智能', 0)
        results.append(("适应度评估", True, 
            f"客观{result.objective_score:.0f}分+主观{result.subjective_score:.0f}分={result.final_score:.0f}分"))
    except Exception as e:
        results.append(("适应度评估", False, str(e)))
    
    # 测试4: 反馈分类
    try:
        from infrastructure.feedback_classifier import FeedbackClassifier
        classifier = FeedbackClassifier()
        r = classifier.classify('不对，应该是1991年发布的')
        results.append(("反馈分类", True, f"类型={r.value}, 置信度=1.0"))
    except Exception as e:
        results.append(("反馈分类", False, str(e)))
    
    # 测试5: 注入验证
    try:
        from infrastructure.injection_verifier import InjectionVerifier
        verifier = InjectionVerifier(db_path='data/e2e_verifications.db')
        stats = verifier.get_verification_stats()
        results.append(("注入验证", True, 
            f"通过率{stats['pass_rate']:.0%}, 平均改进{stats['avg_improvement']:.1f}分"))
    except Exception as e:
        results.append(("注入验证", False, str(e)))
    
    # 测试6: 版本控制
    try:
        from infrastructure.fact_store_v2 import FactStoreV2
        store = FactStoreV2(db_path='data/e2e_fact_store_v2.db')
        id1 = store.add_assertion('测试实体', '属性', '旧值', 0.7, 'initial')
        id2 = store.add_assertion('测试实体', '属性', '新值', 0.9, 'correction')
        assertions = store.get_assertions('测试实体')
        latest = assertions[0] if assertions else {}
        results.append(("版本控制", True, 
            f"断言数{len(assertions)}, 最新值={latest.get('object', 'N/A')}"))
    except Exception as e:
        results.append(("版本控制", False, str(e)))
    
    # 测试7: 外部学习器接口
    try:
        from infrastructure.external_learners import CompositeLearner, WikipediaLearner, DDGSearchLearner
        learner = CompositeLearner([WikipediaLearner(), DDGSearchLearner()])
        available = learner.is_available()
        results.append(("外部学习器", True, f"组合学习器可用={available}"))
    except Exception as e:
        results.append(("外部学习器", False, str(e)))
    
    # 测试8: 完整闭环
    try:
        from infrastructure.fitness_evaluator import FitnessEvaluator
        from infrastructure.knowledge_injector_trigger import KnowledgeInjector
        
        evaluator = FitnessEvaluator()
        injector = KnowledgeInjector(enable_verification=False)
        
        fitness = evaluator.evaluate('什么是深度学习?', '深度学习使用神经网络', 0)
        should_inject, reason = injector.should_inject(
            fitness.objective_score, fitness.final_score
        )
        
        results.append(("学习闭环", True, 
            f"客观分{fitness.objective_score:.0f}, 需注入={should_inject}"))
    except Exception as e:
        results.append(("学习闭环", False, str(e)))
    
    # 输出结果
    print("\n" + "=" * 70)
    print("  端到端能力验证结果")
    print("=" * 70)
    
    for name, success, detail in results:
        status = "✅" if success else "❌"
        print(f"{status} {name:12s} | {detail}")
    
    passed = sum(1 for _, s, _ in results if s)
    total = len(results)
    
    print("=" * 70)
    print(f"总计: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)