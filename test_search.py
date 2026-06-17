"""
测试搜索功能
"""
import sys
sys.path.insert(0, ".")

from core.learning_loop import learning_loop

print("\n" + "="*60)
print("测试搜索功能")
print("="*60)

# 测试搜索
question = "天空为什么是蓝的"
print(f"\n搜索问题: {question}")

results = learning_loop._search_and_learn(question)

print(f"\n搜索结果: {len(results)}条")
for i, r in enumerate(results, 1):
    print(f"\n{i}. {r.get('title', '无标题')[:80]}")
    print(f"   摘要: {r.get('body', '')[:150]}...")
    print(f"   来源: {r.get('source', 'unknown')}")
    print(f"   链接: {r.get('href', '')[:80]}")

print("\n" + "="*60)
if results:
    print("✅ 搜索功能正常")
else:
    print("❌ 搜索失败")
print("="*60)