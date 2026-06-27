import sqlite3
import os

db_path = "data/knowledge_store.db"
if not os.path.exists(db_path):
    print(f"数据库不存在: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"表列表: {[t[0] for t in tables]}")
    
    if ('experiences',) in tables:
        cursor.execute("PRAGMA table_info(experiences)")
        columns = cursor.fetchall()
        print(f"\nexperiences表的列:")
        for col in columns:
            print(f"  {col}")
    
    conn.close()