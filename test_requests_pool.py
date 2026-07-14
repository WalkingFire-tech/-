#!/usr/bin/env python
"""测试requests - 禁用连接池"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

print("=== 测试requests - 禁用连接池 ===")
try:
    session = requests.Session()
    adapter = HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=1),
        pool_connections=1,
        pool_maxsize=1
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    resp = session.post(
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

print("\n=== 测试requests - 使用HTTPAdapter without pool ===")
try:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=0, pool_maxsize=0)
    session.mount('http://', adapter)

    resp = session.post(
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