#!/usr/bin/env python
"""测试Ollama适配器 - 使用gemma-4-12B模型"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import requests

print("=== 测试requests.post (gemma-4-12B) ===")
try:
    payload = {
        "model": "gemma-4-12B",
        "messages": [
            {"role": "system", "content": "你是测试助手"},
            {"role": "user", "content": "1+1等于几？"},
        ],
        "stream": False,
    }
    resp = requests.post(
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