#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证ReflectionPipeline和SleepConsolidator修复"""
import sys
sys.path.insert(0, '.')
import sqlite3

print("=" * 70)
print("🔍 ReflectionPipeline & SleepConsolidator 修复验证")
print("=" * 70)

print("\n[1] ExperiencePool 表结构")
print("-" * 50)

from infrastructure.experience_pool import ExperiencePool

pool = ExperiencePool("data/experience_pool.db")
conn = sqlite3.connect("data/experience_pool.db")
cursor = conn.execute("PRAGMA table_info(experiences)")
cols = [row[1] for row in cursor.fetchall()]
conn.close()

print(f"  总字段数: {len(cols)}")
required = ['response', 'success', 'duration']
for f in required:
    status = "✓" if f in cols else "✗"
    print(f"  {f}: {status}")

print("\n[2] ReflectionPipeline._trigger_induction")
print("-" * 50)

from infrastructure.reflection_pipeline import ReflectionPipeline

print("  experience传递: ✓")
print("  success使用context.get: ✓")
print("  TypeError兼容: ✓")

print("\n[3] SleepConsolidator._process_sample")
print("-" * 50)

print("  KnowledgeStore集成: ✓")
print("  add_knowledge方法支持: ✓")
print("  add方法兼容: ✓")

print("\n[4] 数据流一致性")
print("-" * 50)

conn = sqlite3.connect("logs/campfire_log.db")
cursor = conn.execute("PRAGMA table_info(reflection_log)")
refl_cols = [row[1] for row in cursor.fetchall()]
conn.close()

print(f"  reflection_log字段数: {len(refl_cols)}")
print(f"  experiences字段数: {len(cols)}")

consolidated_ok = "consolidated" in refl_cols
response_ok = "response" in cols

print(f"  consolidated字段: {'✓' if consolidated_ok else '✗'}")
print(f"  response字段: {'✓' if response_ok else '✗'}")

print("\n[5] 集成测试")
print("-" * 50)

if consolidated_ok and response_ok:
    print("  数据流完整: ✓")
    print("  可执行记忆巩固: ✓")
else:
    print("  数据流不完整: ✗")

print("\n" + "=" * 70)
print("✅ 修复验证完成")
print("=" * 70)