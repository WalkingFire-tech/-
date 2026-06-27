#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目完整性验证报告

检查所有关键模块和文件是否存在
"""
import sys
from pathlib import Path

print("=" * 70)
print("📊 Alliance-Pioneer 项目完整性验证")
print("=" * 70)

checks = {
    "核心模块": [
        "core/__init__.py",
        "core/orchestrator.py",
        "core/metacognitive_executor.py",
        "core/cognitive_dispatcher.py",
        "core/sleep_consolidator.py",
        "core/canary_evaluator.py",
    ],
    "核心层架构": [
        "core/layers/__init__.py",
        "core/layers/l1_perception_enhanced.py",
        "core/layers/l2_learning.py",
        "core/layers/l3_integration.py",
        "core/layers/l4_validation.py",
        "core/layers/l5_evolution.py",
        "core/layers/l6_introspection.py",
    ],
    "学习机制": [
        "core/learning/__init__.py",
        "core/learning/incremental_perception.py",
        "core/learning/feedback_loop.py",
        "core/learning/error_alchemy.py",
        "core/learning/tool_builder.py",
        "core/learning/knowledge_weaver.py",
        "core/learning/rhythm_controller.py",
        "core/learning/meta_learning.py",
    ],
    "存在层": [
        "core/presence/__init__.py",
        "core/presence/existence_layer.py",
        "core/presence/self_perception.py",
    ],
    "基础设施": [
        "infrastructure/__init__.py",
        "infrastructure/config_manager.py",
        "infrastructure/experience_pool.py",
        "infrastructure/reflection_pipeline.py",
        "infrastructure/quick_reflex.py",
    ],
    "工具模块": [
        "tools/__init__.py",
        "tools/base.py",
        "tools/registry.py",
        "tools/arbiter.py",
        "tools/math_calculator.py",
        "tools/web_search.py",
        "tools/file_operations.py",
    ],
    "元学习": [
        "meta/__init__.py",
        "meta/induction.py",
    ],
    "适配器": [
        "adapters/__init__.py",
        "adapters/llm/remote_adapter.py",
    ],
    "数据存储": [
        "data/experience_pool.db",
        "data/learning_rules.db",
        "logs/campfire_log.db",
    ],
}

total = 0
passed = 0

for category, files in checks.items():
    print(f"\n[{category}]")
    print("-" * 50)
    
    for file in files:
        total += 1
        exists = Path(file).exists()
        if exists:
            passed += 1
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (缺失)")

print("\n" + "=" * 70)
print(f"验证结果: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
print("=" * 70)

if passed == total:
    print("✅ 项目完整性验证通过")
    sys.exit(0)
else:
    print("⚠️ 存在缺失文件，请检查")
    sys.exit(1)