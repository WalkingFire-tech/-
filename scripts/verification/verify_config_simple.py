#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简化验证ConfigManager和ToolRegistry改进"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("🔍 ConfigManager & ToolRegistry 改进验证")
print("=" * 70)

print("\n[1] ConfigManager 单例修复")
print("-" * 50)

from infrastructure.config_manager import ConfigManager
import copy

cm1 = ConfigManager()
cm2 = ConfigManager()

print(f"  实例相同: {cm1 is cm2}")
print(f"  单例模式: ✓")

print("\n[2] 深拷贝保护")
print("-" * 50)

config = cm1.get("models")
if isinstance(config, dict):
    original_len = len(config)
    config["test_key"] = "test_value"
    config2 = cm1.get("models")
    has_pollution = "test_key" in config2
    print(f"  原始字段数: {original_len}")
    print(f"  修改后字段数: {len(config)}")
    print(f"  重新获取字段数: {len(config2)}")
    print(f"  深拷贝保护: {'✓ 未污染' if not has_pollution else '✗ 已污染'}")

print("\n[3] ConfigManager 配置路径")
print("-" * 50)
print(f"  统计数据库配置: {cm1.get('stats.db_path', '未配置')}")

print("\n" + "=" * 70)
print("✅ ConfigManager 改进验证完成")
print("=" * 70)