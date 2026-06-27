#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化金丝雀验证器所需的数据库表

解决：
1. learning_rules 表缺少必要字段
2. reflection_log 表缺少金丝雀标记字段
"""
import sqlite3
from pathlib import Path

print("=" * 70)
print("🔧 初始化金丝雀验证器数据库表")
print("=" * 70)

# ========== 1. learning_rules 表 ==========
print("\n[1] learning_rules 表")
print("-" * 50)

rules_db = Path("data/learning_rules.db")
rules_db.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(rules_db))

# 检查表是否存在
cursor = conn.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='learning_rules'
""")
table_exists = cursor.fetchone() is not None

if not table_exists:
    # 创建表
    conn.execute('''
        CREATE TABLE learning_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condition TEXT NOT NULL,
            action TEXT NOT NULL,
            priority INTEGER DEFAULT 3,
            confidence REAL DEFAULT 0.5,
            source TEXT DEFAULT 'unknown',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            updated_at TEXT,
            promoted_at TEXT,
            promotion_reason TEXT,
            rejected_at TEXT,
            rejection_reason TEXT,
            metadata TEXT
        )
    ''')
    conn.commit()
    print("  ✅ 创建 learning_rules 表")
else:
    print("  ℹ️ learning_rules 表已存在")

# 检查并添加缺失字段
cursor = conn.execute("PRAGMA table_info(learning_rules)")
columns = [row[1] for row in cursor.fetchall()]

required_columns = {
    "promoted_at": "TEXT",
    "promotion_reason": "TEXT",
    "rejected_at": "TEXT",
    "rejection_reason": "TEXT",
    "updated_at": "TEXT",
}

for col, col_type in required_columns.items():
    if col not in columns:
        try:
            conn.execute(f"ALTER TABLE learning_rules ADD COLUMN {col} {col_type}")
            print(f"  ✅ 添加字段: {col}")
        except Exception as e:
            print(f"  ⚠️ 添加字段 {col} 失败: {e}")

conn.commit()
conn.close()

# ========== 2. reflection_log 表 ==========
print("\n[2] reflection_log 表")
print("-" * 50)

reflection_db = Path("logs/campfire_log.db")
reflection_db.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(reflection_db))

# 检查表是否存在
cursor = conn.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='reflection_log'
""")
table_exists = cursor.fetchone() is not None

if not table_exists:
    # 创建表
    conn.execute('''
        CREATE TABLE reflection_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            query TEXT,
            plan TEXT,
            tool_calls TEXT,
            final_answer TEXT,
            confidence REAL,
            model_used TEXT,
            user_id TEXT,
            session_id TEXT,
            duration_ms INTEGER,
            extra_metadata TEXT,
            consolidated INTEGER DEFAULT 0,
            consolidated_at TEXT,
            rule_used INTEGER,
            is_canary_sample INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    print("  ✅ 创建 reflection_log 表")
else:
    print("  ℹ️ reflection_log 表已存在")

# 检查并添加缺失字段
cursor = conn.execute("PRAGMA table_info(reflection_log)")
columns = [row[1] for row in cursor.fetchall()]

required_columns = {
    "rule_used": "INTEGER",
    "is_canary_sample": "INTEGER DEFAULT 0",
    "consolidated": "INTEGER DEFAULT 0",
    "consolidated_at": "TEXT",
}

for col, col_type in required_columns.items():
    if col not in columns:
        try:
            conn.execute(f"ALTER TABLE reflection_log ADD COLUMN {col} {col_type}")
            print(f"  ✅ 添加字段: {col}")
        except Exception as e:
            print(f"  ⚠️ 添加字段 {col} 失败: {e}")

conn.commit()
conn.close()

# ========== 验证 ==========
print("\n[验证] 表结构检查")
print("-" * 50)

# 验证 learning_rules
conn = sqlite3.connect(str(rules_db))
cursor = conn.execute("PRAGMA table_info(learning_rules)")
columns = [row[1] for row in cursor.fetchall()]
conn.close()

print(f"  learning_rules 字段: {len(columns)}个")
required = ["condition", "action", "status", "promoted_at", "rejected_at"]
missing = [r for r in required if r not in columns]
if missing:
    print(f"  ❌ 缺失字段: {missing}")
else:
    print(f"  ✅ 必要字段完整")

# 验证 reflection_log
conn = sqlite3.connect(str(reflection_db))
cursor = conn.execute("PRAGMA table_info(reflection_log)")
columns = [row[1] for row in cursor.fetchall()]
conn.close()

print(f"  reflection_log 字段: {len(columns)}个")
required = ["rule_used", "is_canary_sample", "consolidated"]
missing = [r for r in required if r not in columns]
if missing:
    print(f"  ❌ 缺失字段: {missing}")
else:
    print(f"  ✅ 必要字段完整")

print("\n" + "=" * 70)
print("✅ 数据库表初始化完成")
print("=" * 70)