"""
快速进化测试 - 分批运行
"""
import requests
import sqlite3
import time

def chat(message):
    try:
        r = requests.post("http://localhost:8000/api/chat", 
                         json={"message": message}, timeout=60)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def check_stats():
    conn = sqlite3.connect("data/knowledge_store.db")
    stats = {}
    
    cursor = conn.execute("SELECT COUNT(*) FROM knowledge_items")
    stats['knowledge'] = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM experiences")
    stats['experience'] = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM learning_rules")
    stats['rules'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

# 初始状态
print("\n" + "="*60)
print("🧬 快速进化测试")
print("="*60)

stats = check_stats()
print(f"\n初始状态:")
print(f"  知识: {stats['knowledge']}条")
print(f"  经验: {stats['experience']}条")
print(f"  规则: {stats['rules']}条")

# 测试问题
questions = [
    "什么是人工智能？",
    "机器学习是什么？",
    "Python有什么优点？",
    "如何优化代码性能？",
    "什么是微服务？",
    "如何设计数据库？",
    "什么是API？",
    "如何处理并发？",
    "什么是缓存？",
    "如何保证数据安全？",
]

print(f"\n开始测试 {len(questions)} 个问题...")
print("="*60)

success = 0
for i, q in enumerate(questions, 1):
    print(f"\n[{i}/{len(questions)}] {q}")
    
    start = time.time()
    result = chat(q)
    duration = time.time() - start
    
    if result.get('response'):
        success += 1
        print(f"✅ {duration:.1f}s - {result.get('intent', '?')}")
    else:
        print(f"❌ 无响应")
    
    time.sleep(0.3)

# 最终状态
stats = check_stats()
print("\n" + "="*60)
print("📊 测试完成")
print("="*60)
print(f"成功率: {success}/{len(questions)} ({success/len(questions)*100:.0f}%)")
print(f"\n最终状态:")
print(f"  知识: {stats['knowledge']}条")
print(f"  经验: {stats['experience']}条")
print(f"  规则: {stats['rules']}条")

# 检查是否达到归纳条件
if stats['experience'] >= 20:
    print("\n✅ 经验充足，可以触发归纳")
else:
    print(f"\n⚠️ 还需积累 {20-stats['experience']} 条经验")