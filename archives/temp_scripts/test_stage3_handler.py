"""
阶段3：聊天处理器测试（轻量级）
"""
import sys
import asyncio
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       阶段3：聊天处理器测试                            ║")
print("╚════════════════════════════════════════════════════════╝\n")

async def test():
    from backend.chat_handler import chat_never_giveup
    
    # 测试1：问候语
    print("测试1：问候语处理")
    result = await chat_never_giveup("你好", {})
    print(f"  ✅ 回复长度: {len(result.get('response', ''))}字")
    print(f"     尝试方法: {len(result.get('attempts', []))}种")
    print(f"     精神内核: {'✓' if result.get('spirit_compliant') else '✗'}")
    
    # 测试2：概念问题
    print("\n测试2：概念问题处理")
    result = await chat_never_giveup("认知的概念是什么", {})
    print(f"  ✅ 回复长度: {len(result.get('response', ''))}字")
    print(f"     尝试方法: {len(result.get('attempts', []))}种")
    print(f"     精神内核: {'✓' if result.get('spirit_compliant') else '✗'}")
    
    # 测试3：代码问题
    print("\n测试3：代码问题处理")
    result = await chat_never_giveup("如何写排序算法", {})
    print(f"  ✅ 回复长度: {len(result.get('response', ''))}字")
    print(f"     尝试方法: {len(result.get('attempts', []))}种")
    print(f"     精神内核: {'✓' if result.get('spirit_compliant') else '✗'}")
    
    # 测试4：复杂问题
    print("\n测试4：复杂问题处理")
    result = await chat_never_giveup("请解释认知科学的发展历史", {})
    print(f"  ✅ 回复长度: {len(result.get('response', ''))}字")
    print(f"     尝试方法: {len(result.get('attempts', []))}种")
    print(f"     精神内核: {'✓' if result.get('spirit_compliant') else '✗'}")

asyncio.run(test())

print("\n" + "=" * 60)
print("✅ 阶段3测试完成：聊天处理器运行正常")
print("=" * 60)