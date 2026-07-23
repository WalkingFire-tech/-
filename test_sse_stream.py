#!/usr/bin/env python
"""测试SSE stream对话"""
import httpx
import json

print("=== 测试SSE stream对话 ===")
try:
    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            'POST',
            'http://127.0.0.1:8000/api/chat/stream',
            json={'message': '你好', 'conversation_id': 'test-sse-001'}
        ) as response:
            print(f'Status: {response.status_code}')

            count = 0
            for chunk in response.iter_text():
                count += 1
                print(f'Chunk {count}: {chunk[:100]}...' if count <= 5 else '...')
                if count >= 10:
                    break

            print(f'\nTotal chunks: {count}')
            print("✅ SSE stream测试成功")
except Exception as e:
    print(f"❌ SSE stream测试失败: {e}")
    import traceback
    traceback.print_exc()