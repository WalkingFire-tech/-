"""添加元认知种子规则"""
import sqlite3
from datetime import datetime

print("添加元认知种子规则...")

conn = sqlite3.connect('learning_rules.db')
cursor = conn.cursor()

# 检查是否已存在
cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE condition LIKE '%meta%'")
if cursor.fetchone()[0] == 0:
    # 添加元认知规则
    cursor.execute("""
        INSERT INTO learning_rules 
        (condition, action, priority, confidence, status, source, created_at)
        VALUES 
        (?, ?, ?, ?, ?, ?, ?)
    """, (
        "intent_type == 'meta'",
        "reroute:code_light",
        10,
        1.0,
        'active',
        'manual',
        datetime.now().isoformat()
    ))
    
    conn.commit()
    print("✓ 元认知规则已添加")
else:
    print("✓ 元认知规则已存在")

conn.close()

# 验证
conn = sqlite3.connect('learning_rules.db')
cursor = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
active_count = cursor.fetchone()[0]
conn.close()

print(f"\n当前活跃规则: {active_count}条")