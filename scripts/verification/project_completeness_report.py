#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成项目完整性报告
"""
from pathlib import Path
from collections import defaultdict

print("=" * 80)
print("📊 Alliance-Pioneer 项目完整性报告")
print("=" * 80)

# 统计各目录的文件数
directories = {
    "核心模块 (core/)": "core",
    "基础设施 (infrastructure/)": "infrastructure",
    "工具模块 (tools/)": "tools",
    "元学习 (meta/)": "meta",
    "适配器 (adapters/)": "adapters",
    "后端服务 (backend/)": "backend",
    "配置文件 (config/)": "config",
    "数据存储 (data/)": "data",
    "日志文件 (logs/)": "logs",
    "脚本 (scripts/)": "scripts",
    "测试 (tests/)": "tests",
    "文档 (docs/)": "docs",
}

stats = {}

for name, path in directories.items():
    p = Path(path)
    if p.exists():
        py_files = list(p.rglob("*.py"))
        db_files = list(p.rglob("*.db"))
        yaml_files = list(p.rglob("*.yaml"))
        other_files = [f for f in p.rglob("*") if f.is_file() and f.suffix not in [".py", ".db", ".yaml", ".pyc"]]
        
        stats[name] = {
            "py": len(py_files),
            "db": len(db_files),
            "yaml": len(yaml_files),
            "other": len(other_files),
            "total": len(py_files) + len(db_files) + len(yaml_files) + len(other_files)
        }
    else:
        stats[name] = {"py": 0, "db": 0, "yaml": 0, "other": 0, "total": 0}

# 打印统计
print("\n目录统计:")
print("-" * 80)
print(f"{'目录':<30} {'Python':<10} {'数据库':<10} {'配置':<10} {'其他':<10} {'总计':<10}")
print("-" * 80)

total_py = 0
total_db = 0
total_yaml = 0
total_other = 0

for name, s in stats.items():
    print(f"{name:<30} {s['py']:<10} {s['db']:<10} {s['yaml']:<10} {s['other']:<10} {s['total']:<10}")
    total_py += s['py']
    total_db += s['db']
    total_yaml += s['yaml']
    total_other += s['other']

print("-" * 80)
print(f"{'总计':<30} {total_py:<10} {total_db:<10} {total_yaml:<10} {total_other:<10} {total_py + total_db + total_yaml + total_other:<10}")

# 检查关键文件
print("\n\n关键文件检查:")
print("-" * 80)

key_files = {
    "核心组件": [
        "core/orchestrator.py",
        "core/metacognitive_executor.py",
        "core/cognitive_dispatcher.py",
        "core/sleep_consolidator.py",
        "core/canary_evaluator.py",
    ],
    "基础设施": [
        "infrastructure/config_manager.py",
        "infrastructure/experience_pool.py",
        "infrastructure/reflection_pipeline.py",
        "infrastructure/quick_reflex.py",
    ],
    "工具系统": [
        "tools/__init__.py",
        "tools/base.py",
        "tools/registry.py",
        "tools/arbiter.py",
        "tools/math_calculator.py",
        "tools/web_search.py",
    ],
    "元学习": [
        "meta/induction.py",
    ],
    "数据文件": [
        "data/experience_pool.db",
        "data/learning_rules.db",
        "logs/campfire_log.db",
    ],
    "配置": [
        "config/reflex_rules.yaml",
    ],
}

for category, files in key_files.items():
    print(f"\n{category}:")
    for f in files:
        exists = Path(f).exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {f}")

# 检查__init__.py
print("\n\n__init__.py 检查:")
print("-" * 80)

init_dirs = [
    "core",
    "core/layers",
    "core/learning",
    "core/presence",
    "infrastructure",
    "tools",
    "meta",
    "adapters",
    "backend",
]

for d in init_dirs:
    init_file = Path(d) / "__init__.py"
    exists = init_file.exists()
    status = "✅" if exists else "❌"
    print(f"  {status} {d}/__init__.py")

print("\n" + "=" * 80)
print("✅ 项目完整性检查完成")
print("=" * 80)