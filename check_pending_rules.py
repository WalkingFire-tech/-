"""查看pending规则详情"""
import sqlite3

conn = sqlite3.connect('learning_rules.db')
cursor = conn.cursor()

# 查看pending规则的置信度分布
cursor.execute("""
    SELECT MIN(confidence), MAX(confidence), AVG(confidence)
    FROM learning_rules
    WHERE status = 'pending'
""")

min_conf, max_conf, avg_conf = cursor.fetchone()
print(f"Pending规则置信度分布:")
print(f"  最小: {min_conf:.2f}")
print(f"  最大: {max_conf:.2f}")
print(f"  平均: {avg_conf:.2f}")

# 查看Top 10
cursor.execute("""
    SELECT id, confidence, source, condition
    FROM learning_rules
    WHERE status = 'pending'
    ORDER BY confidence DESC
    LIMIT 10
""")

print(f"\nTop 10 pending规则:")
for row in cursor.fetchall():
    rule_id, conf, source, condition = row
    print(f"  ID={rule_id}, conf={conf:.2f}, source={source}")
    print(f"    条件: {condition[:60]}")

conn.close()