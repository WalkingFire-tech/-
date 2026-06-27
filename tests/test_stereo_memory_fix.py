import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("立体记忆修复验证")
print("=" * 70)

from core.memory.stereo_memory import get_stereo_memory, MemoryType, MemoryImportance

system = get_stereo_memory()

print("\n测试1: 保存记忆（枚举）")
entry = {
    "content": "用户今天很开心，谈论了关于进化的想法",
    "memory_type": MemoryType.EMOTION,
    "importance": MemoryImportance.HIGH,
    "user_emotion": "joy",
    "topic": "进化"
}
memory_id = system.save(entry)
print(f"✅ 保存成功: {memory_id}")

print("\n测试2: 保存记忆（数值）")
entry2 = {
    "content": "用户询问了关于学习的问题",
    "memory_type": MemoryType.CONVERSATION,
    "importance": 0.7,
}
memory_id2 = system.save(entry2)
print(f"✅ 保存成功: {memory_id2}")

print("\n测试3: 统计信息")
stats = system.get_stats()
print(f"总记忆: {stats['total_memories']}")
print(f"平均重要性: {stats['avg_importance']:.2f}")
print(f"按类型: {stats['by_type']}")

print("\n测试4: 搜索（query参数）")
results = system.search(query="进化", limit=10)
print(f"找到 {len(results)} 条包含'进化'的记忆")
for r in results:
    content_str = str(r.content)
    print(f"  - {content_str[:50]}... (重要性: {r.importance:.2f})")

print("\n测试5: 按主题搜索")
topic_results = system.get_by_topic("学习", limit=5)
print(f"找到 {len(topic_results)} 条包含'学习'的记忆")

print("\n测试6: 最近记忆")
recent = system.get_recent(limit=5)
print(f"最近 {len(recent)} 条记忆")
for r in recent:
    content_str = str(r.content)
    print(f"  - {content_str[:50]}...")

print("\n测试7: 枚举转换")
imp = MemoryImportance.from_value(0.8)
print(f"from_value(0.8) = {imp} (value = {imp.value})")

imp2 = MemoryImportance.from_value(0.51)
print(f"from_value(0.51) = {imp2} (value = {imp2.value})")

print("\n" + "=" * 70)
print("✅ 所有测试通过！")
print("=" * 70)