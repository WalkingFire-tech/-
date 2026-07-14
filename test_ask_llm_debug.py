#!/usr/bin/env python
"""测试ask_llm方法并打印日志"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import logging
logging.basicConfig(level=logging.DEBUG)

from core.external_learner import external_learner

print("=== 测试ask_llm方法 ===")
result = external_learner.ask_llm("1+1等于几？", "你是一个数学助手")
print(f"结果: {result}")
print("\n=== 测试完成 ===")