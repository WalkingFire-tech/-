from infrastructure.versioned_fact_store import VersionedFactStore

store = VersionedFactStore()

# 用完整问题查询
results = store.get_active_assertions('机器学习的定义')
print(f"查询'机器学习的定义': {len(results)}条结果")
for r in results:
    print(f"  {r['subject']} -> {r['predicate']} -> {r['object']}")

# 用另一个问题查询
results2 = store.get_active_assertions('什么是机器学习?')
print(f"\n查询'什么是机器学习?': {len(results2)}条结果")
for r in results2:
    print(f"  {r['subject']} -> {r['predicate']} -> {r['object']}")