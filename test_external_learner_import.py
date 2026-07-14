#!/usr/bin/env python
"""测试external_learner实例"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from loguru import logger
logger.remove()
logger.add(sys.stderr, level="INFO")

from core.external_learner import external_learner

print(f"external_learner id: {id(external_learner)}")
print(f"external_learner type: {type(external_learner)}")
print(f"external_learner.llm_api_key: {external_learner.llm_api_key[:10] if external_learner.llm_api_key else 'None'}...")

result = external_learner.ask_llm("1+1等于几？", "你是一个数学助手")
print(f"结果: {result}")