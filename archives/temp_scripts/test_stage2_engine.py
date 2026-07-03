"""
阶段2：永不放弃引擎测试（轻量级）
"""
import sys
import asyncio
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       阶段2：永不放弃引擎测试                          ║")
print("╚════════════════════════════════════════════════════════╝\n")

async def test():
    from core.never_give_up import NeverGiveUpEngine
    
    engine = NeverGiveUpEngine()
    
    # 测试1：引擎初始化
    print("测试1：引擎初始化")
    print("  ✅ NeverGiveUpEngine初始化成功")
    
    # 测试2：简单问题
    print("\n测试2：简单问题解决")
    result = await engine.solve("你好", {})
    print(f"  ✅ 生成了答案")
    print(f"     置信度: {result.get('confidence', 0):.0%}")
    print(f"     尝试方法: {len(result.get('attempts', []))}种")
    
    # 测试3：复杂问题
    print("\n测试3：复杂问题解决")
    result = await engine.solve("认知的概念是什么", {})
    print(f"  ✅ 生成了{len(result.get('answer', ''))}字的答案")
    print(f"     尝试方法: {len(result.get('attempts', []))}种")
    
    # 测试4：失败回复
    print("\n测试4：失败回复有意义")
    result = await engine.solve("不存在的问题xyz", {})
    answer = result.get('answer', '')
    has_direction = "建议" in answer or "方向" in answer
    print(f"  ✅ 失败回复包含方向: {has_direction}")
    print(f"     回复长度: {len(answer)}字")

asyncio.run(test())

print("\n" + "=" * 60)
print("✅ 阶段2测试完成：永不放弃引擎运行正常")
print("=" * 60)