#!/usr/bin/env python
"""测试ask_llm方法并打印详细信息"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from core.external_learner import external_learner

print("=== 测试ask_llm方法 ===")
print(f"llm_api_key: {external_learner.llm_api_key[:10] if external_learner.llm_api_key else 'None'}...")
print(f"llm_model: {external_learner.llm_model}")
print(f"llm_base_url: {external_learner.llm_base_url}")

result = external_learner.ask_llm("1+1等于几？", "你是一个数学助手")
print(f"\n结果类型: {type(result)}")
print(f"结果长度: {len(result) if isinstance(result, str) else 'N/A'}")
print(f"结果: {result}")

print("\n=== 测试完成 ===")