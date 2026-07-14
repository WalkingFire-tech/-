#!/usr/bin/env python
"""测试外部学习器Ollama调用"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from core.external_learner import external_learner

# 测试1: 深度分析
print("=== 测试1: 深度分析 ===")
query = "为什么GPU温度会突然升高？"
result = external_learner.deep_analysis(query)
print(f"结果: {result[:200] if result else 'None'}...")

# 测试2: 事实核查
print("\n=== 测试2: 事实核查 ===")
claim = "GPU温度升高会导致系统关机"
result = external_learner.fact_check(claim)
print(f"结果: {result[:200] if result else 'None'}...")

# 测试3: 向其他模型请教
print("\n=== 测试3: 向其他模型请教 ===")
question = "如何降低GPU温度？"
result = external_learner.ask_model(question)
print(f"结果: {result[:200] if result else 'None'}...")

print("\n=== 测试完成 ===")