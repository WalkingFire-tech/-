"""测试种子知识"""
from infrastructure.versioned_fact_store import VersionedFactStore

store = VersionedFactStore()

# 测试检索
questions = [
    "什么是机器学习?",
    "什么是深度学习?",
    "Python是什么?",
]

print("知识检索测试:")
for q in questions:
    assertions = store.get_active_assertions(q)
    print(f"\n  问题: {q}")
    print(f"  结果: {len(assertions)}条知识")
    if assertions:
        print(f"  内容: {assertions[0]['object'][:50]}...")