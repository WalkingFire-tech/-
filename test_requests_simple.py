#!/usr/bin/env python
"""测试requests.post - 简化版本"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import requests
import urllib3

# 禁用SSL警告（虽然我们用的是HTTP）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("=== 测试requests.post - 简化版本 ===")
try:
    # 尝试最简单的POST请求
    resp = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "gemma-4-12B", "prompt": "1+1", "stream": False},
        timeout=60,
    )
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.text[:200]}")
except Exception as e:
    print(f"失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试requests.post - 带headers ===")
try:
    resp = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "gemma-4-12B", "prompt": "1+1", "stream": False},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.text[:200]}")
except Exception as e:
    print(f"失败: {e}")
    import traceback
    traceback.print_exc()