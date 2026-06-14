"""激活pending规则（降低阈值）"""
import sqlite3

with sqlite3.connect('data/learning_rules.db') as conn:
    cursor = conn.cursor()
    
    print("激活pending规则（阈值0.5）")
    print("=" * 60)
    
    cursor.execute("""
        UPDATE learning_rules 
        SET status = 'active' 
        WHERE status = 'pending' 
          AND confidence >= 0.5
    """)
    
    activated = cursor.rowcount
    conn.commit()
    
    print(f"激活规则: {activated}条")
    
    cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
    active_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
    pending_count = cursor.fetchone()[0]
    
    print(f"\n当前状态:")
    print(f"  Active规则: {active_count}条")
    print(f"  Pending规则: {pending_count}条")
    
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

print("\n" + "=" * 60)
print("激活完成")