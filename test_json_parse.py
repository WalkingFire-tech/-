#!/usr/bin/env python
"""测试JSON解析"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import requests
import json
import urllib3
urllib3.disable_warnings()

response = requests.post(
    'https://api.deepseek.com/v1/chat/completions',
    headers={
        'Authorization': 'Bearer sk-c7d567e16e054f3597893cc20f2a5659',
        'Content-Type': 'application/json'
    },
    json={
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'user', 'content': '1+1'}
        ],
        'temperature': 0.7,
        'max_tokens': 2000
    },
    timeout=30,
    verify=False
)

print(f"状态码: {response.status_code}")
print(f"响应文本: {response.text[:500]}")

try:
    data = response.json()
    print(f"JSON解析成功")
    print(f"choices数量: {len(data.get('choices', []))}")
    if data.get('choices'):
        print(f"第一个choice: {data['choices'][0]}")
        content = data['choices'][0]['message']['content']
        print(f"内容: {content}")
except Exception as e:
    print(f"JSON解析失败: {e}")
    import traceback
    traceback.print_exc()