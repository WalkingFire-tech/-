#!/usr/bin/env python
"""测试aiohttp - 详细响应"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import asyncio
import json

async def test_aiohttp():
    try:
        import aiohttp

        print("=== 测试aiohttp - 详细响应 ===")
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "gemma-4-12B",
                "messages": [
                    {"role": "system", "content": "你是测试助手"},
                    {"role": "user", "content": "1+1等于几？"},
                ],
                "stream": False,
            }
            async with session.post(
                "http://127.0.0.1:11434/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                print(f"状态码: {resp.status}")
                print(f"Content-Type: {resp.headers.get('Content-Type')}")
                text = await resp.text()
                print(f"响应: {text}")
    except ImportError:
        print("aiohttp未安装")
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_aiohttp())