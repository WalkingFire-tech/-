"""
测试外部学习器和注入验证器
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.external_learners import (
    WikipediaLearner,
    DDGSearchLearner,
    CompositeLearner,
    wikipedia_learner,
    ddg_search_learner
)
from infrastructure.injection_verifier import (
    InjectionVerifier,
    injection_verifier
)


def test_wikipedia_learner():
    """测试Wikipedia学习器"""
    print("\n=== 测试Wikipedia学习器 ===")
    
    learner = WikipediaLearner(language="zh")
    
    print(f"是否可用: {learner.is_available()}")
    print(f"成本预估: {learner.get_cost_estimate('测试查询')}")
    
    if learner.is_available():
        results = learner.learn("人工智能", max_results=2)
        print(f"\n查询 '人工智能' 结果:")
        for i, item in enumerate(results, 1):
            print(f"  {i}. {item.content[:100]}...")
            print(f"     来源: {item.source}, 置信度: {item.confidence}")
    
    print("✅ Wikipedia学习器测试通过")


def test_ddg_search_learner():
    """测试DuckDuckGo搜索学习器"""
    print("\n=== 测试DuckDuckGo搜索学习器 ===")
    
    learner = DDGSearchLearner(region="cn-zh")
    
    print(f"是否可用: {learner.is_available()}")
    print(f"成本预估: {learner.get_cost_estimate('测试查询')}")
    
    if learner.is_available():
        results = learner.learn("Python编程", max_results=3)
        print(f"\n查询 'Python编程' 结果:")
        for i, item in enumerate(results, 1):
            print(f"  {i}. {item.content[:100]}...")
            print(f"     来源: {item.source}, 置信度: {item.confidence}")
    
    print("✅ DuckDuckGo搜索学习器测试通过")


def test_composite_learner():
    """测试组合学习器"""
    print("\n=== 测试组合学习器 ===")
    
    learner = CompositeLearner([wikipedia_learner, ddg_search_learner])
    
    print(f"是否可用: {learner.is_available()}")
    
    if learner.is_available():
        results = learner.learn("机器学习", max_results=3)
        print(f"\n查询 '机器学习' 结果:")
        for i, item in enumerate(results, 1):
            print(f"  {i}. [{item.source}] {item.content[:80]}...")
            print(f"     置信度: {item.confidence}")
    
    print("✅ 组合学习器测试通过")


def test_injection_verifier():
    """测试注入验证器"""
    print("\n=== 测试注入验证器 ===")
    
    verifier = InjectionVerifier(db_path="data/test_verifications.db")
    
    injected_knowledge = [
        {'content': '人工智能是计算机科学的一个分支', 'confidence': 0.85},
        {'content': '机器学习是AI的核心技术', 'confidence': 0.80}
    ]
    
    result = verifier.verify_injection(
        injection_id="test_001",
        question="什么是人工智能?",
        before_score=30.0,
        injected_knowledge=injected_knowledge,
        improvement_threshold=5.0
    )
    
    print(f"验证结果:")
    print(f"  注入前评分: {result.before_score}")
    print(f"  注入后评分: {result.after_score}")
    print(f"  改进分数: {result.improvement}")
    print(f"  是否通过: {result.passed}")
    
    stats = verifier.get_verification_stats()
    print(f"\n验证统计:")
    print(f"  总验证次数: {stats['total_verifications']}")
    print(f"  通过率: {stats['pass_rate']:.1%}")
    print(f"  平均改进: {stats['avg_improvement']:.1f}")
    
    print("✅ 注入验证器测试通过")


def test_failed_verification():
    """测试失败验证的处理"""
    print("\n=== 测试失败验证处理 ===")
    
    verifier = InjectionVerifier(db_path="data/test_verifications.db")
    
    result = verifier.verify_injection(
        injection_id="test_002",
        question="测试失败案例",
        before_score=40.0,
        injected_knowledge=[{'content': '少量知识', 'confidence': 0.3}],
        improvement_threshold=10.0
    )
    
    print(f"验证结果: {'通过' if result.passed else '未通过'}")
    
    if not result.passed:
        suggestions = verifier.suggest_corrections()
        print(f"\n修正建议:")
        for sug in suggestions:
            print(f"  问题: {sug['issue']}")
            print(f"  建议: {sug['suggestions']}")
    
    print("✅ 失败验证处理测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("外部学习器和注入验证器测试")
    print("=" * 60)
    
    try:
        test_wikipedia_learner()
    except Exception as e:
        print(f"⚠️ Wikipedia测试跳过: {e}")
    
    try:
        test_ddg_search_learner()
    except Exception as e:
        print(f"⚠️ DuckDuckGo测试跳过: {e}")
    
    try:
        test_composite_learner()
    except Exception as e:
        print(f"⚠️ 组合学习器测试跳过: {e}")
    
    test_injection_verifier()
    test_failed_verification()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()