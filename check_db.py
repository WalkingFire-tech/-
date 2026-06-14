import sqlite3
import os

db_path = 'data/learning_rules.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables in {db_path}: {tables}")
    conn.close()
else:
    print(f"{db_path} not found")