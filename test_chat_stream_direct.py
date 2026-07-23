#!/usr/bin/env python
"""直接测试chat_stream函数"""
import sys
import asyncio
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from backend.chat_stream import chat_stream

async def test_chat_stream():
    print("=== 直接测试chat_stream函数 ===")
    try:
        count = 0
        async for event_type, data in chat_stream("你好", {"history": [], "session_id": "test-direct"}):
            count += 1
            if count <= 5:
                print(f'Event {count}: type={event_type}, keys={list(data.keys())[:5]}')
            if count >= 10:
                break

        print(f'\nTotal events: {count}')
        print("✅ chat_stream函数测试成功")
    except Exception as e:
        print(f"❌ chat_stream函数测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat_stream())