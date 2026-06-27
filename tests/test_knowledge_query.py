"""快速测试知识查询"""
from infrastructure.versioned_fact_store import VersionedFactStore
from infrastructure.question_matcher import QuestionMatcher

store = VersionedFactStore()

test_questions = [
    "什么是机器学习?",
    "机器学习是什么?",
    "机器学习的定义",
    "监督学习的特点",
    "深度学习的应用",
]

print("=" * 60)
print("知识查询测试")
print("=" * 60)

for question in test_questions:
    variants = QuestionMatcher.normalize_question(question)
    print(f"\n问题: {question}")
    print(f"查询变体: {variants[:3]}")
    
    # 尝试所有变体
    facts = []
    for variant in variants:
        facts = store.get_active_assertions(variant)
        if facts:
            print(f"✅ 匹配到: {variant}")
            break
    
    if facts:
        for fact in facts[:2]:
            print(f"   {fact['subject']} -> {fact['predicate']} -> {fact['object'][:50]}...")
    else:
        print("❌ 未找到知识")