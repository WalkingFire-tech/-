#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""强制重新测试意图识别"""
import sys
import importlib
from pathlib import Path

# 清除所有缓存
for module_name in list(sys.modules.keys()):
    if 'intent_parser' in module_name or 'core.services' in module_name:
        del sys.modules[module_name]

sys.path.insert(0, str(Path(__file__).parent))

# 重新导入
from core.services.intent_parser import IntentParser

print("=" * 60)
print("强制重新测试意图识别")
print("=" * 60)

p = IntentParser()

print(f"\nMemory pattern:\n{p.rules['memory'].pattern}\n")

test_cases = [
    "回顾历史对话",
    "历史对话",
    "回顾对话",
    "历史问题",
    "之前我们聊过什么",
    "记住这个",
    "回顾历史问题"
]

print("测试结果:")
for text in test_cases:
    intent = p.parse(text)
    match = p.rules['memory'].search(text)
    print(f"  {text:20s} -> {intent.type:10s} (正则匹配: {bool(match)})")

print("\n" + "=" * 60)