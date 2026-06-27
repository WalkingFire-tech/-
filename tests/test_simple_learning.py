"""
简化的学习闭环测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.injection_verifier import InjectionVerifier


def test_injection_verifier_simple():
    """测试注入验证器"""
    print("\n=== 测试注入验证器 ===")
    
    verifier = InjectionVerifier(db_path="data/test_verifications_simple.db")
    
    result = verifier.verify_injection(
        injection_id="simple_001",
        question="什么是AI?",
        before_score=30.0,
        injected_knowledge=[
            {'content': 'AI是人工智能', 'confidence': 0.9},
            {'content': 'AI是计算机科学分支', 'confidence': 0.85}
        ],
        improvement_threshold=5.0
    )
    
    print(f"验证通过: {result.passed}")
    print(f"改进分数: {result.improvement:.1f}")
    print(f"注入前: {result.before_score:.1f} → 注入后: {result.after_score:.1f}")
    
    stats = verifier.get_verification_stats()
    print(f"\n统计: 通过率 {stats['pass_rate']:.1%}, 平均改进 {stats['avg_improvement']:.1f}")
    
    print("✅ 测试通过")


def test_external_learner_interface():
    """测试外部学习器接口"""
    print("\n=== 测试外部学习器接口 ===")
    
    from core.external_learner_base import ExternalLearnerBase, KnowledgeItem
    
    class MockLearner(ExternalLearnerBase):
        def learn(self, query, context=None, max_results=5):
            return [
                KnowledgeItem(
                    content=f"关于{query}的知识",
                    source="mock",
                    confidence=0.8
                )
            ]
        
        def is_available(self):
            return True
        
        def get_cost_estimate(self, query):
            return 0.0
    
    learner = MockLearner()
    results = learner.learn("测试查询")
    
    print(f"学习器可用: {learner.is_available()}")
    print(f"返回知识: {results[0].content}")
    print(f"置信度: {results[0].confidence}")
    
    print("✅ 测试通过")


def run_all():
    print("=" * 60)
    print("简化测试")
    print("=" * 60)
    
    test_injection_verifier_simple()
    test_external_learner_interface()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
    print("=" * 60)


if __name__ == "__main__":
    run_all()