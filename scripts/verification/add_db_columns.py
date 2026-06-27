#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""添加数据库字段"""
import sqlite3

print('添加consolidated字段到reflection_log表...')

conn = sqlite3.connect('logs/campfire_log.db')

# 检查字段是否存在
cursor = conn.execute('PRAGMA table_info(reflection_log)')
columns = [row[1] for row in cursor.fetchall()]

if 'consolidated' not in columns:
    conn.execute('ALTER TABLE reflection_log ADD COLUMN consolidated INTEGER DEFAULT 0')
    print('  ✅ 添加consolidated字段')

if 'consolidated_at' not in columns:
    conn.execute('ALTER TABLE reflection_log ADD COLUMN consolidated_at TEXT')
    print('  ✅ 添加consolidated_at字段')

if 'rule_used' not in columns:
    conn.execute('ALTER TABLE reflection_log ADD COLUMN rule_used INTEGER')
    print('  ✅ 添加rule_used字段')

if 'is_canary_sample' not in columns:
    conn.execute('ALTER TABLE reflection_log ADD COLUMN is_canary_sample INTEGER DEFAULT 0')
    print('  ✅ 添加is_canary_sample字段')

conn.commit()
conn.close()

print('数据库字段添加完成')