#!/usr/bin/env python
"""测试external_learner实例"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from core.external_learner import external_learner, ExternalLearner

print(f"external_learner id: {id(external_learner)}")
print(f"external_learner class: {external_learner.__class__}")
print(f"external_learner.llm_api_key: {external_learner.llm_api_key[:10] if external_learner.llm_api_key else 'None'}...")

# 创建新实例
new_learner = ExternalLearner()
print(f"\nnew_learner id: {id(new_learner)}")
print(f"new_learner class: {new_learner.__class__}")
print(f"new_learner.llm_api_key: {new_learner.llm_api_key[:10] if new_learner.llm_api_key else 'None'}...")

# 测试ask_llm
result = external_learner.ask_llm("1+1等于几？", "你是一个数学助手")
print(f"\nexternal_learner结果: {result}")

result = new_learner.ask_llm("1+1等于几？", "你是一个数学助手")
print(f"new_learner结果: {result}")