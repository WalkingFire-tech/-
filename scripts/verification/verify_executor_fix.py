#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证MetacognitiveExecutor修复"""
import sys
sys.path.insert(0, '.')
import os

print("=" * 70)
print("🔍 MetacognitiveExecutor 修复验证")
print("=" * 70)

print("\n[1] 导入修复")
print("-" * 50)

try:
    from tools.registry import registry
    print("  tools.registry导入: ✓")
except Exception as e:
    print(f"  tools.registry导入: ✗ ({e})")

try:
    from meta.induction import induction_scheduler
    print("  meta.induction导入: ✓")
except Exception as e:
    print(f"  meta.induction导入: ✗ ({e})")

try:
    from data.knowledge_store import get_knowledge_store
    print("  data.knowledge_store导入: ✓")
except Exception as e:
    print(f"  data.knowledge_store导入: ✗ ({e})")

print("\n[2] 核心层模块")
print("-" * 50)

layers = [
    "core.layers.l2_learning",
    "core.layers.l3_integration",
    "core.layers.l4_validation",
    "core.layers.l5_evolution",
    "core.layers.l6_introspection"
]

for layer in layers:
    try:
        __import__(layer)
        print(f"  {layer}: ✓")
    except Exception as e:
        print(f"  {layer}: ✗")

print("\n[3] 学习机制模块")
print("-" * 50)

mechanisms = [
    "core.learning.incremental_perception",
    "core.learning.feedback_loop",
    "core.learning.error_alchemy",
    "core.learning.tool_builder",
    "core.learning.knowledge_weaver",
    "core.learning.rhythm_controller",
    "core.learning.meta_learning"
]

for mech in mechanisms:
    try:
        __import__(mech)
        print(f"  {mech}: ✓")
    except Exception as e:
        print(f"  {mech}: ✗")

print("\n[4] 存在层模块")
print("-" * 50)

try:
    from core.presence.existence_layer import ExistenceLayer
    print("  ExistenceLayer: ✓")
except Exception as e:
    print(f"  ExistenceLayer: ✗ ({e})")

print("\n[5] MetacognitiveExecutor实例化")
print("-" * 50)

try:
    from core.metacognitive_executor import MetacognitiveExecutor
    executor = MetacognitiveExecutor()
    print("  实例化: ✓")
    print(f"  能力缓存: {executor.capability_cache}")
except Exception as e:
    print(f"  实例化: ✗ ({e})")

print("\n" + "=" * 70)
print("✅ MetacognitiveExecutor 修复验证完成")
print("=" * 70)