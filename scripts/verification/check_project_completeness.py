#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目完整性检查 - 根据架构规范检查所有文件
"""
from pathlib import Path

print("=" * 80)
print("📁 Alliance-Pioneer 项目完整性检查")
print("=" * 80)

# 定义所有必需的文件和目录
checks = {
    "根目录文件": {
        "files": [
            "README.md",
            "requirements.txt",
            "config.yaml",
            "main.py",
            "api.py",
        ],
        "dirs": []
    },
    
    "核心模块 (core/)": {
        "files": [
            "core/__init__.py",
            "core/orchestrator.py",
            "core/metacognitive_executor.py",
            "core/cognitive_dispatcher.py",
            "core/sleep_consolidator.py",
            "core/canary_evaluator.py",
        ],
        "dirs": [
            "core/layers",
            "core/learning",
            "core/presence",
        ]
    },
    
    "核心层架构 (core/layers/)": {
        "files": [
            "core/layers/__init__.py",
            "core/layers/l1_perception_enhanced.py",
            "core/layers/l2_learning.py",
            "core/layers/l3_integration.py",
            "core/layers/l4_validation.py",
            "core/layers/l5_evolution.py",
            "core/layers/l6_introspection.py",
        ],
        "dirs": []
    },
    
    "学习机制 (core/learning/)": {
        "files": [
            "core/learning/__init__.py",
            "core/learning/incremental_perception.py",
            "core/learning/feedback_loop.py",
            "core/learning/error_alchemy.py",
            "core/learning/tool_builder.py",
            "core/learning/knowledge_weaver.py",
            "core/learning/rhythm_controller.py",
            "core/learning/meta_learning.py",
        ],
        "dirs": []
    },
    
    "存在层 (core/presence/)": {
        "files": [
            "core/presence/__init__.py",
            "core/presence/existence_layer.py",
            "core/presence/self_perception.py",
        ],
        "dirs": []
    },
    
    "基础设施 (infrastructure/)": {
        "files": [
            "infrastructure/__init__.py",
            "infrastructure/config_manager.py",
            "infrastructure/experience_pool.py",
            "infrastructure/reflection_pipeline.py",
            "infrastructure/quick_reflex.py",
        ],
        "dirs": []
    },
    
    "工具模块 (tools/)": {
        "files": [
            "tools/__init__.py",
            "tools/base.py",
            "tools/registry.py",
            "tools/arbiter.py",
            "tools/math_calculator.py",
            "tools/web_search.py",
            "tools/file_operations.py",
            "tools/builtin.py",
            "tools/generator.py",
        ],
        "dirs": []
    },
    
    "元学习 (meta/)": {
        "files": [
            "meta/__init__.py",
            "meta/induction.py",
        ],
        "dirs": []
    },
    
    "适配器 (adapters/)": {
        "files": [
            "adapters/__init__.py",
        ],
        "dirs": [
            "adapters/llm",
        ]
    },
    
    "LLM适配器 (adapters/llm/)": {
        "files": [
            "adapters/llm/remote_adapter.py",
        ],
        "dirs": []
    },
    
    "后端服务 (backend/)": {
        "files": [
            "backend/__init__.py",
            "backend/main.py",
        ],
        "dirs": []
    },
    
    "配置文件 (config/)": {
        "files": [
            "config/reflex_rules.yaml",
        ],
        "dirs": []
    },
    
    "数据存储 (data/)": {
        "files": [
            "data/experience_pool.db",
            "data/learning_rules.db",
        ],
        "dirs": [
            "data/workspace",
        ]
    },
    
    "日志文件 (logs/)": {
        "files": [
            "logs/campfire_log.db",
        ],
        "dirs": []
    },
}

# 统计
total_files = 0
existing_files = 0
total_dirs = 0
existing_dirs = 0
missing_items = []

# 检查每个类别
for category, items in checks.items():
    print(f"\n{'='*80}")
    print(f"📦 {category}")
    print(f"{'='*80}")
    
    # 检查文件
    if items["files"]:
        print("\n文件检查:")
        for file in items["files"]:
            total_files += 1
            path = Path(file)
            if path.exists():
                existing_files += 1
                size = path.stat().st_size if path.is_file() else 0
                print(f"  ✅ {file} ({size} bytes)")
            else:
                missing_items.append(file)
                print(f"  ❌ {file} (缺失)")
    
    # 检查目录
    if items["dirs"]:
        print("\n目录检查:")
        for dir_path in items["dirs"]:
            total_dirs += 1
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                existing_dirs += 1
                file_count = len(list(path.glob("*")))
                print(f"  ✅ {dir_path}/ ({file_count} 项)")
            else:
                missing_items.append(dir_path + "/")
                print(f"  ❌ {dir_path}/ (缺失)")

# 总结
print(f"\n{'='*80}")
print("📊 检查总结")
print(f"{'='*80}")

file_rate = (existing_files / total_files * 100) if total_files > 0 else 0
dir_rate = (existing_dirs / total_dirs * 100) if total_dirs > 0 else 0

print(f"\n文件统计:")
print(f"  总计: {total_files} 个")
print(f"  存在: {existing_files} 个")
print(f"  缺失: {total_files - existing_files} 个")
print(f"  完整率: {file_rate:.1f}%")

print(f"\n目录统计:")
print(f"  总计: {total_dirs} 个")
print(f"  存在: {existing_dirs} 个")
print(f"  缺失: {total_dirs - existing_dirs} 个")
print(f"  完整率: {dir_rate:.1f}%")

if missing_items:
    print(f"\n⚠️  缺失项列表:")
    for item in missing_items:
        print(f"  - {item}")
else:
    print(f"\n✅ 所有文件和目录都存在！")

print(f"\n{'='*80}")

# 返回状态码
import sys
sys.exit(0 if not missing_items else 1)