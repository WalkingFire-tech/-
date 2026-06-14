#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试格式化错误修复"""
import sqlite3

print("=" * 60)
print("测试格式化错误修复")
print("=" * 60)

# 测试1: 检查experience_pool.db中的数据
print("\n[测试1] 检查experience_pool.db数据")
try:
    conn = sqlite3.connect('experience_pool.db')
    cur = conn.execute('''
        SELECT intent_type, raw_input, quality_score, success, model_name
        FROM experiences
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    recent = cur.fetchall()
    conn.close()
    
    print(f"  找到 {len(recent)} 条记录")
    
    for i, (intent_type, raw_input, quality, success, model) in enumerate(recent, 1):
        quality_val = quality if quality is not None else 0.0
        model_val = model if model is not None else "未知"
        print(f"  {i}. [{intent_type}] {raw_input[:20]}... | 质量: {quality_val:.1f} | 模型: {model_val}")
    
    qualities = [r[2] for r in recent if r[2] is not None]
    avg_quality = sum(qualities) / len(qualities) if qualities else 0.0
    success_rate = sum(1 for r in recent if r[3]) / len(recent) * 100
    
    print(f"\n  平均质量: {avg_quality:.1f}分")
    print(f"  成功率: {success_rate:.1f}%")
    print("  ✓ 格式化成功，无NoneType错误")
    
except Exception as e:
    print(f"  ✗ 错误: {e}")

# 测试2: 检查learning_rules.db中的数据
print("\n[测试2] 检查learning_rules.db数据")
try:
    conn = sqlite3.connect('learning_rules.db')
    cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
    active_rules = cur.fetchone()[0]
    conn.close()
    
    print(f"  活跃规则: {active_rules}条")
    print("  ✓ 查询成功")
    
except Exception as e:
    print(f"  ✗ 错误: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)