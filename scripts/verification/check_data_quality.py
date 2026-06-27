#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查数据质量"""

import sqlite3

print("=" * 70)
print("🔍 数据质量深度检查")
print("=" * 70)

# 1. 经验池success字段
print("\n[1] 经验池success字段检查")
conn = sqlite3.connect('data/experience_pool.db')

sample = conn.execute('SELECT id, intent_type, quality_score, success, raw_input FROM experiences LIMIT 5').fetchall()
print("  样本数据:")
for row in sample:
    input_str = row[4][:30] if row[4] else "None"
    print(f"    ID={row[0]}, intent={row[1]}, quality={row[2]}, success={row[3]}, input={input_str}...")

non_zero = conn.execute('SELECT COUNT(*) FROM experiences WHERE success != 0').fetchone()[0]
print(f"\n  非零success记录: {non_zero}条")

# 检查quality_score分布
quality_dist = conn.execute('''
    SELECT 
        CASE 
            WHEN quality_score >= 80 THEN 'high(>=80)'
            WHEN quality_score >= 50 THEN 'medium(50-79)'
            ELSE 'low(<50)'
        END as level,
        COUNT(*) as cnt
    FROM experiences
    GROUP BY level
''').fetchall()
print(f"  质量分布: {dict(quality_dist)}")

conn.close()

# 2. 学习规则内容
print("\n[2] 学习规则内容检查")
conn = sqlite3.connect('data/learning_rules.db')

rules = conn.execute('SELECT id, condition, action, confidence, source, status FROM learning_rules WHERE source="induction" LIMIT 3').fetchall()
print("  归纳规则样本:")
for rule in rules:
    cond = rule[1][:40] if rule[1] else "None"
    act = rule[2][:40] if rule[2] else "None"
    print(f"    条件: {cond}...")
    print(f"    动作: {act}...")
    print(f"    置信度: {rule[3]}, 状态: {rule[5]}")
    print()

# 按来源统计
sources = conn.execute('SELECT source, COUNT(*) as cnt FROM learning_rules GROUP BY source').fetchall()
print(f"  来源分布: {dict(sources)}")

conn.close()

# 3. 反思日志的工具调用
print("\n[3] 反思日志工具调用检查")
conn = sqlite3.connect('logs/campfire_log.db')

logs = conn.execute('SELECT id, query, tool_calls, confidence FROM reflection_log LIMIT 5').fetchall()
print("  反思日志样本:")
for log in logs:
    query = log[1][:30] if log[1] else "None"
    tools = log[2][:50] if log[2] else "None"
    print(f"    查询: {query}...")
    print(f"    工具: {tools}...")
    print(f"    置信度: {log[3]}")
    print()

conn.close()