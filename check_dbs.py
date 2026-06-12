import sqlite3

print("检查数据库状态...")

# 检查规则库
print("\n【学习规则库】")
conn = sqlite3.connect('learning_rules.db')
cur = conn.execute("SELECT COUNT(*), status FROM learning_rules GROUP BY status")
for row in cur.fetchall():
    print(f"  {row[1]}: {row[0]}条")
conn.close()

# 检查统计库
print("\n【统计库】")
try:
    conn = sqlite3.connect('model_stats.db')
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"  表: {', '.join(tables)}")
    
    if 'model_calls' in tables:
        cur = conn.execute("SELECT COUNT(*) FROM model_calls")
        print(f"  记录数: {cur.fetchone()[0]}条")
    conn.close()
except Exception as e:
    print(f"  错误: {e}")

# 检查经验池
print("\n【经验池】")
conn = sqlite3.connect('experience_pool.db')
cur = conn.execute("SELECT COUNT(*) FROM experiences")
print(f"  总经验: {cur.fetchone()[0]}条")

cur = conn.execute("SELECT COUNT(*) FROM experiences WHERE quality_score >= 0.7")
print(f"  高质量: {cur.fetchone()[0]}条")
conn.close()