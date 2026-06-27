"""
最终集成验证
测试完整的适应度评估系统
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "=" * 70)
print("  🎯 最终集成验证")
print("=" * 70)


def test_all_modules():
    """测试所有模块导入"""
    print("\n【模块导入测试】")
    print("-" * 50)
    
    modules = [
        ("config.config_loader", "config_loader"),
        ("infrastructure.fact_store", "fact_store"),
        ("infrastructure.fact_store_v2", "fact_store_v2"),
        ("infrastructure.triple_extractor", "triple_extractor"),
        ("infrastructure.fitness_evaluator", "fitness_evaluator"),
        ("infrastructure.feedback_classifier", "feedback_classifier"),
        ("infrastructure.knowledge_injector_trigger", "knowledge_injector"),
        ("infrastructure.fitness_config", "FitnessConfig"),
    ]
    
    passed = 0
    for module_path, attr in modules:
        try:
            module = __import__(module_path, fromlist=[attr])
            getattr(module, attr)
            print(f"  ✅ {module_path}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {module_path}: {e}")
    
    print(f"\n  结果: {passed}/{len(modules)} 通过")
    return passed == len(modules)


def test_complete_flow():
    """测试完整流程"""
    print("\n【完整流程测试】")
    print("-" * 50)
    
    from infrastructure.fitness_evaluator import FitnessEvaluator
    from infrastructure.feedback_classifier import feedback_classifier
    from infrastructure.fact_store_v2 import fact_store_v2
    
    # 创建评估器
    evaluator = FitnessEvaluator()
    print(f"  ✅ 评估器创建成功")
    print(f"     客观分权重: {evaluator.objective_weight}")
    print(f"     主观分权重: {evaluator.subjective_weight}")
    print(f"     客观分阈值: {evaluator.objective_threshold}")
    print(f"     总分阈值: {evaluator.total_threshold}")
    
    # 测试场景
    question = "为什么会有冰雹"
    response = "冰雹是由过冷水滴在强对流云中反复冻结形成的"
    
    # 评估
    score = evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=0,
        intent_type="question"
    )
    
    print(f"\n  评估结果:")
    print(f"     总分: {score.final_score:.1f}")
    print(f"     客观分: {score.objective_score:.1f}")
    print(f"     主观分: {score.subjective_score:.1f}")
    print(f"     事实性: {score.is_factual_question}")
    
    # 反馈分类
    fb_result = feedback_classifier.process_feedback("👍 回答很好")
    print(f"\n  反馈分类:")
    print(f"     类型: {fb_result['type']}")
    print(f"     适应度调整: {fb_result['fitness_delta']}")
    
    return True


def test_evolution():
    """测试知识进化"""
    print("\n【知识进化测试】")
    print("-" * 50)
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2()
    
    # 种子数据
    store.add_assertion(
        question="进化测试",
        subject="测试",
        predicate="值",
        obj="初始值",
        source="seed",
        confidence=0.85,
        is_seed=True
    )
    print(f"  ✅ 添加种子数据: conf=0.85")
    
    # 用户纠错
    store.add_assertion(
        question="进化测试",
        subject="测试",
        predicate="值",
        obj="纠错值",
        source="user_correction",
        confidence=0.95
    )
    print(f"  ✅ 添加用户纠错: conf=0.95")
    
    # 查询
    assertions = store.get_assertions("进化测试")
    print(f"\n  当前断言: {len(assertions)}条")
    for a in assertions:
        print(f"     - {a['object']} (source={a['source']}, conf={a['confidence']:.2f})")
    
    # 历史
    history = store.get_assertion_history("进化测试", "测试", "值")
    print(f"\n  历史版本: {len(history)}条")
    for h in history:
        status = "被覆盖" if h['is_overridden'] else "活跃"
        print(f"     - v{h['version']}: {h['object']} [{status}]")
    
    return True


def test_config():
    """测试配置"""
    print("\n【配置测试】")
    print("-" * 50)
    
    from config.config_loader import config_loader
    
    config = config_loader.get_fitness_config()
    
    print(f"  客观分权重: {config.get('objective_weight')}")
    print(f"  主观分权重: {config.get('subjective_weight')}")
    print(f"  客观分阈值: {config.get('objective_threshold')}")
    print(f"  总分阈值: {config.get('total_threshold')}")
    print(f"  使用旧版: {config.get('use_legacy')}")
    print(f"  影子模式: {config.get('enable_shadow')}")
    
    return True


def main():
    """运行所有测试"""
    tests = [
        ("模块导入", test_all_modules),
        ("完整流程", test_complete_flow),
        ("知识进化", test_evolution),
        ("配置", test_config),
    ]
    
    results = []
    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总
    print("\n" + "=" * 70)
    print("  📊 最终验证结果")
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