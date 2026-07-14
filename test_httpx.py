#!/usr/bin/env python
"""测试httpx"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

try:
    import httpx

    print("=== 测试httpx ===")
    try:
        payload = {
            "model": "gemma-4-12B",
            "messages": [
                {"role": "system", "content": "你是测试助手"},
                {"role": "user", "content": "1+1等于几？"},
            ],
            "stream": False,
        }
        resp = httpx.post(
            "http://127.0.0.1:11434/api/chat",
            json=payload,
            timeout=60,
        )
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.text[:200]}")
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()
except ImportError:
    print("httpx未安装")