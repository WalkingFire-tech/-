"""激活pending规则"""
import sqlite3

conn = sqlite3.connect('data/learning_rules.db')
cursor = conn.cursor()

# 查看当前状态
cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
pending_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
active_count = cursor.fetchone()[0]

print(f"激活前状态:")
print(f"  Pending规则: {pending_count}条")
print(f"  Active规则: {active_count}条")

# 激活规则
cursor.execute("""
    UPDATE learning_rules 
    SET status = 'active' 
    WHERE status = 'pending' 
      AND confidence >= 0.6
""")

activated = cursor.rowcount
conn.commit()

# 查看激活后状态
cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
new_active_count = cursor.fetchone()[0]

print(f"\n激活结果:")
print(f"  激活规则: {activated}条")
print(f"  Active规则: {new_active_count}条")

# 查看规则分布
cursor.execute("""
    SELECT source, COUNT(*) 
    FROM learning_rules 
    WHERE status='active'
    GROUP BY source
""")

print(f"\n规则来源分布:")
for source, count in cursor.fetchall():
    source_name = source if source else 'unknown'
    print(f"  {source_name}: {count}条")

conn.close()