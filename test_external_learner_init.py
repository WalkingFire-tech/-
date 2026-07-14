#!/usr/bin/env python
"""检查external_learner初始化"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from core.external_learner import external_learner

print(f"llm_api_key: {external_learner.llm_api_key[:10] if external_learner.llm_api_key else 'None'}...")
print(f"llm_model: {external_learner.llm_model}")
print(f"llm_base_url: {external_learner.llm_base_url}")