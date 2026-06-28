"""
最小化端到端测试：只测试核心流程
"""
import sys
import asyncio
import time
sys.path.insert(0, ".")

async def test_minimal():
    print("测试1：精神内核加载")
    from core.spirit_core import spirit_core
    print(f"  ✅ 精神内核加载成功")
    
    print("\n测试2：问候语处理")
    from backend.chat_handler import chat_never_giveup
    start = time.time()
    result = await asyncio.wait_for(
        chat_never_giveup("你好", {}),
        timeout=10.0
    )
    elapsed = time.time() - start
    print(f"  ✅ 问候语: {elapsed:.1f}秒, {len(result.get('response', ''))}字")
    
    print("\n测试3：概念问题处理")
    start = time.time()
    result = await asyncio.wait_for(
        chat_never_giveup("认知是什么", {}),
        timeout=25.0
    )
    elapsed = time.time() - start
    print(f"  ✅ 概念问题: {elapsed:.1f}秒, {len(result.get('response', ''))}字")
    print(f"  回复预览: {result.get('response', '')[:100]}...")
    
    print("\n✅ 最小化测试完成")

asyncio.run(test_minimal())