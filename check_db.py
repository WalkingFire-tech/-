import sqlite3
import os

db_path = "data/learning_progress.db"
if not os.path.exists(db_path):
    print(f"数据库不存在: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"表列表: {tables}")
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n表 {table_name} 的列:")
        for col in columns:
            print(f"  {col}")
    
    conn.close()