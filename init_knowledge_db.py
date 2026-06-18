import sqlite3

db_path = "data/knowledge_store.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"现有表: {tables}")

if 'knowledge' in tables:
    cursor.execute("PRAGMA table_info(knowledge)")
    columns = cursor.fetchall()
    print(f"\nknowledge表结构:")
    for col in columns:
        print(f"  {col}")
    
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    count = cursor.fetchone()[0]
    print(f"\n现有知识点: {count}条")
else:
    print("\nknowledge表不存在，创建中...")
    cursor.execute('''
        CREATE TABLE knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            source TEXT,
            type TEXT,
            quality REAL,
            created_at TEXT,
            salience REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            metadata TEXT
        )
    ''')
    conn.commit()
    print("✓ knowledge表已创建")

conn.close()