#!/usr/bin/env python
"""测试外部学习器DeepSeek API"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from core.external_learner import external_learner

print("=== 测试1: ask_llm ===")
result = external_learner.ask_llm("1+1等于几？", "你是一个数学助手")
print(f"结果: {result}")

print("\n=== 测试2: deep_research ===")
result = external_learner.deep_research("为什么GPU温度会突然升高？")
print(f"结果: {result}")

print("\n=== 测试3: analyze_conversation_parsing ===")
result = external_learner.analyze_conversation_parsing("为什么GPU温度会突然升高？", "用户在询问GPU温度问题")
print(f"结果: {result}")

print("\n=== 测试完成 ===")