"""检查并添加meta种子规则"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('learning_rules.db')
cursor = conn.cursor()

# 检查是否已存在
cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE condition LIKE '%meta%'")
existing = cursor.fetchone()[0]

if existing == 0:
    cursor.execute("""
        INSERT INTO learning_rules 
        (condition, action, priority, confidence, status, source, created_at)
        VALUES 
        (?, ?, ?, ?, ?, ?, ?)
    """, (
        "intent_type == 'meta'",
        "reroute:code_light",
        1,
        1.0,
        'active',
        'manual',
        datetime.now().isoformat()
    ))
    
    conn.commit()
    print("✓ meta种子规则已添加")
else:
    print(f"✓ meta种子规则已存在: {existing}条")

conn.close()

# 验证
conn = sqlite3.connect('learning_rules.db')
cursor = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
active_count = cursor.fetchone()[0]
conn.close()

print(f"\n当前活跃规则: {active_count}条")