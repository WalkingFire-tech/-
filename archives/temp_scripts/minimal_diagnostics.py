"""最简诊断 - 只检查关键问题"""
import sqlite3
from pathlib import Path

print("\n系统诊断\n")

# 1. 检查knowledge表
print("1. 检查knowledge表...")
db_path = Path("data/knowledge_store.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

if "knowledge" not in tables:
    print("  ✗ knowledge表不存在，创建中...")
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
    print("  ✓ knowledge表已创建")
else:
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    count = cursor.fetchone()[0]
    print(f"  ✓ knowledge表存在，{count}条记录")

conn.close()

# 2. 检查数据库完整性
print("\n2. 检查数据库完整性...")
for db_file in Path("data").glob("*.db"):
    try:
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        
        if result == "ok":
            print(f"  ✓ {db_file.name}")
        else:
            print(f"  ✗ {db_file.name}: {result}")
    except Exception as e:
        print(f"  ✗ {db_file.name}: {e}")

# 3. 检查关键文件
print("\n3. 检查关键文件...")
critical_files = [
    "backend/main.py",
    "core/services/planner.py",
    "config/settings.yaml",
]
for file_path in critical_files:
    if Path(file_path).exists():
        print(f"  ✓ {file_path}")
    else:
        print(f"  ✗ {file_path}: 不存在")

print("\n✓ 诊断完成")