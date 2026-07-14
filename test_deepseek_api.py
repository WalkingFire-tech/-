#!/usr/bin/env python
"""直接测试DeepSeek API"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import requests
import json

print("=== 直接测试DeepSeek API ===")
try:
    with open("config/external_api.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        api_key = config.get("deepseek_api_key", "")
        print(f"API密钥: {api_key[:10]}..." if api_key else "API密钥未配置")

    if not api_key:
        print("错误: API密钥未配置")
        sys.exit(1)

    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个测试助手"},
                {"role": "user", "content": "1+1等于几？"}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        },
        timeout=30
    )

    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(f"响应: {content}")
    else:
        print(f"错误: {response.text}")
except Exception as e:
    print(f"异常: {e}")
    import traceback
    traceback.print_exc()