#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试simpleeval支持的语法"""
from simpleeval import simple_eval

print("=" * 60)
print("测试 simpleeval 支持的语法")
print("=" * 60)

# 测试1: 基本比较
print("\n[测试1] 基本比较")
test_cases = [
    ("intent_type == 'code'", {"intent_type": "code"}, True),
    ("intent_type == 'chat'", {"intent_type": "code"}, False),
    ("quality < 30", {"quality": 25}, True),
    ("quality > 50", {"quality": 25}, False),
]

for expr, names, expected in test_cases:
    try:
        result = simple_eval(expr, names=names)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {expr} -> {result} (期望: {expected})")
    except Exception as e:
        print(f"  ✗ {expr} -> 错误: {e}")

# 测试2: 逻辑运算
print("\n[测试2] 逻辑运算")
test_cases = [
    ("intent_type == 'code' and quality < 30", {"intent_type": "code", "quality": 25}, True),
    ("intent_type == 'chat' or quality < 30", {"intent_type": "code", "quality": 25}, True),
]

for expr, names, expected in test_cases:
    try:
        result = simple_eval(expr, names=names)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {expr} -> {result} (期望: {expected})")
    except Exception as e:
        print(f"  ✗ {expr} -> 错误: {e}")

# 测试3: in操作符
print("\n[测试3] in操作符")
test_cases = [
    ("'test' in raw_input", {"raw_input": "this is a test"}, True),
    ("'Python' in raw_input", {"raw_input": "I love Java"}, False),
]

for expr, names, expected in test_cases:
    try:
        result = simple_eval(expr, names=names)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {expr} -> {result} (期望: {expected})")
    except Exception as e:
        print(f"  ✗ {expr} -> 错误: {e}")

# 测试4: LIKE语法（不支持）
print("\n[测试4] LIKE语法（应该不支持）")
test_cases = [
    ("raw_input LIKE '%test%'", {"raw_input": "this is a test"}, None),
    ("text contains 'Python'", {"text": "I love Python"}, None),
]

for expr, names, expected in test_cases:
    try:
        result = simple_eval(expr, names=names)
        print(f"  ! {expr} -> {result} (意外成功)")
    except Exception as e:
        print(f"  ✓ {expr} -> 预期错误: {type(e).__name__}")

print("\n" + "=" * 60)
print("结论:")
print("1. simpleeval 支持基本比较和逻辑运算")
print("2. simpleeval 支持 in 操作符")
print("3. simpleeval 不支持 SQL LIKE 语法")
print("4. 需要将 LIKE 转换为 in 操作符")
print("=" * 60)