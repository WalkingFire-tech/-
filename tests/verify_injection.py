from infrastructure.versioned_fact_store import VersionedFactStore

store = VersionedFactStore()

# 查询机器学习相关
results = store.get_active_assertions('机器学习')
print(f"查询'机器学习': {len(results)}条结果")
for r in results[:5]:
    print(f"  - {r['subject']} -> {r['predicate']} -> {r['object']}")

# 查询监督学习
results2 = store.get_active_assertions('监督学习')
print(f"\n查询'监督学习': {len(results2)}条结果")
for r in results2[:3]:
    print(f"  - {r['subject']} -> {r['predicate']} -> {r['object']}")

# 统计
stats = store.get_statistics()
print(f"\n统计: {stats}")