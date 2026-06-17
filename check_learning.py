import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/knowledge_store.db')

print("\n" + "="*60)
print("知识库学习记录检查")
print("="*60)

# 检查学习来源的知识
cursor = conn.execute("""
    SELECT question, source, created_at 
    FROM knowledge_items 
    WHERE source IN ('search_learned', 'analysis', 'chat_learned', 'duckduckgo', 'bing')
    ORDER BY created_at DESC 
    LIMIT 10
""")
learned = cursor.fetchall()

print(f"\n通过学习获得的知识: {len(learned)}条")
for i, (q, s, t) in enumerate(learned, 1):
    print(f"{i}. {q[:50]}... (来源: {s})")

# 检查总知识量
cursor = conn.execute("SELECT COUNT(*) FROM knowledge_items")
total = cursor.fetchone()[0]

cursor = conn.execute("SELECT COUNT(*) FROM knowledge_items WHERE source = 'search_learned' OR source = 'analysis'")
learned_count = cursor.fetchone()[0]

print(f"\n知识库统计:")
print(f"  总知识: {total}条")
print(f"  学习获得: {learned_count}条")

# 检查经验池
cursor = conn.execute("SELECT COUNT(*) FROM experiences")
exp_count = cursor.fetchone()[0]

print(f"  经验记录: {exp_count}条")

# 检查学习规则
cursor = conn.execute("SELECT COUNT(*) FROM learning_rules")
rules_count = cursor.fetchone()[0]

print(f"  学习规则: {rules_count}条")

conn.close()

print("\n" + "="*60)