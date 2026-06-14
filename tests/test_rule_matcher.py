#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试规则匹配引擎修复"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from infrastructure.rule_matcher import RuleMatcher

print("=" * 60)
print("测试规则匹配引擎修复")
print("=" * 60)

matcher = RuleMatcher()

# 测试1: 基本条件
print("\n[测试1] 基本条件")
test_cases = [
    ("intent_type == 'code'", {"intent_type": "code"}, True),
    ("intent_type == 'chat'", {"intent_type": "code"}, False),
    ("quality < 30", {"quality": 25}, True),
]

for condition, context, expected in test_cases:
    result = matcher.evaluate_condition(condition, context)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {condition} -> {result} (期望: {expected})")

# 测试2: LIKE语法转换
print("\n[测试2] LIKE语法转换")
test_cases = [
    ("raw_input LIKE '%test%'", {"raw_input": "this is a test"}, True),
    ("raw_input LIKE '%Python%'", {"raw_input": "I love Java"}, False),
]

for condition, context, expected in test_cases:
    result = matcher.evaluate_condition(condition, context)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {condition} -> {result} (期望: {expected})")

# 测试3: contains语法转换
print("\n[测试3] contains语法转换")
test_cases = [
    ("text contains 'Python'", {"text": "I love Python"}, True),
    ("text contains 'Java'", {"text": "I love Python"}, False),
]

for condition, context, expected in test_cases:
    result = matcher.evaluate_condition(condition, context)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {condition} -> {result} (期望: {expected})")

# 测试4: 复杂条件
print("\n[测试4] 复杂条件")
test_cases = [
    ("intent_type == 'chat' and '是否应该' in raw_input", 
     {"intent_type": "chat", "raw_input": "我是否应该学习Python？"}, True),
    ("model == 'mindchat' and intent_type == 'code'", 
     {"model": "mindchat", "intent_type": "code"}, True),
]

for condition, context, expected in test_cases:
    result = matcher.evaluate_condition(condition, context)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {condition[:40]}... -> {result} (期望: {expected})")

print("\n" + "=" * 60)
print("规则匹配引擎修复验证完成")
print("=" * 60)