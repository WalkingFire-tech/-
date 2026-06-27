"""调试纠错流程"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.versioned_fact_store import VersionedFactStore

store = VersionedFactStore()

print("测试直接添加知识:")

# 直接添加
id, action = store.add_assertion(
    question="测试问题",
    subject="测试",
    predicate="答案",
    obj="这是测试答案",
    source="test",
    confidence=0.9
)

print(f"添加结果: ID={id}, 动作={action}")

# 检索
assertions = store.get_active_assertions("测试问题")
print(f"检索结果: {len(assertions)}条")

if assertions:
    print(f"内容: {assertions[0]}")
else:
    print("❌ 没有检索到！")
    
# 统计
stats = store.get_statistics()
print(f"\n统计: {stats}")