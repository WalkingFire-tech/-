#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证ReflectionPipeline改进"""
import sys
sys.path.insert(0, '.')
from infrastructure.reflection_pipeline import ReflectionPipeline
import sqlite3

print("=" * 70)
print("🔍 ReflectionPipeline 改进验证")
print("=" * 70)

pipeline = ReflectionPipeline()

conn = sqlite3.connect('logs/campfire_log.db')
cursor = conn.execute('PRAGMA table_info(reflection_log)')
cols = [r[1] for r in cursor.fetchall()]
conn.close()

print("\n[1] 数据库字段迁移")
print("-" * 50)
required = ['consolidated', 'consolidated_at', 'rule_used', 'is_canary_sample', 'success']
for f in required:
    status = "✓" if f in cols else "✗"
    print(f"  {f}: {status}")

print(f"\n  总字段数: {len(cols)}")

print("\n[2] 配置化参数")
print("-" * 50)
print(f"  成功阈值: {pipeline.success_threshold}")
print(f"  权重配置: {pipeline.weights}")
print(f"  采样策略: {pipeline.jsonl_sample_strategy}")

print("\n[3] 采样策略测试")
print("-" * 50)

test_cases = [
    {"success": False, "confidence": 0.3},
    {"success": True, "confidence": 0.8},
    {"success": False, "confidence": 0.7},
]

for ctx in test_cases:
    result = pipeline._should_sample_jsonl(ctx)
    print(f"  success={ctx['success']}, conf={ctx['confidence']:.1f} → 采样={result}")

print("\n[4] 多维度success计算")
print("-" * 50)

test_contexts = [
    {"confidence": 0.8, "tool_calls": [{"status": "success"}], "plan": {"tasks": [{"status": "success"}]}},
    {"confidence": 0.6, "tool_calls": [{"status": "fail"}], "plan": {}},
    {"confidence": 0.4, "tool_calls": [], "plan": {}},
]

for ctx in test_contexts:
    result = pipeline._calculate_success(ctx)
    print(f"  conf={ctx['confidence']:.1f}, tools={len(ctx['tool_calls'])} → success={result}")

print("\n" + "=" * 70)
print("✅ ReflectionPipeline 改进验证完成")
print("=" * 70)