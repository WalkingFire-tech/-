#!/usr/bin/env python
"""测试aiohttp - /api/generate"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

import asyncio

async def test_aiohttp_generate():
    try:
        import aiohttp

        print("=== 测试aiohttp - /api/generate ===")
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "gemma-4-12B",
                "prompt": "1+1等于几？",
                "stream": False,
            }
            async with session.post(
                "http://127.0.0.1:11434/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                print(f"状态码: {resp.status}")
                text = await resp.text()
                print(f"响应: {text[:500]}")
    except ImportError:
        print("aiohttp未安装")
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_aiohttp_generate())