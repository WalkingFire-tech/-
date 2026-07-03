"""
测试深度认知处理是否修复超时
"""
import sys
import asyncio
import time
sys.path.insert(0, ".")

async def test():
    print("╔════════════════════════════════════════════════════════╗")
    print("║       测试深度认知处理超时修复                          ║")
    print("╚════════════════════════════════════════════════════════╝\n")
    
    from core.metacognitive_executor import MetacognitiveExecutor
    
    executor = MetacognitiveExecutor()
    
    print("测试1：阶段0本体感知（应该在3秒内完成）")
    start = time.time()
    try:
        result = await asyncio.wait_for(
            executor._phase0_capability_introspection(),
            timeout=5.0
        )
        elapsed = time.time() - start
        print(f"  ✅ 阶段0完成: {elapsed:.2f}秒")
        print(f"     工具: {len(result['tools'])}个")
        print(f"     模型: {len(result['models'])}个")
        print(f"     知识库: {len(result['knowledge_bases'])}个")
    except asyncio.TimeoutError:
        print("  ❌ 阶段0超时（>5秒）")
    
    print("\n测试2：完整深度认知处理（应该在18秒内完成）")
    start = time.time()
    try:
        result = await asyncio.wait_for(
            executor.execute_with_full_metacognition("认知的概念是什么", {}),
            timeout=20.0
        )
        elapsed = time.time() - start
        print(f"  ✅ 完整处理完成: {elapsed:.2f}秒")
        print(f"     最终结果长度: {len(result.get('final_result', ''))}字")
        print(f"     置信度: {result.get('confidence', 0):.0%}")
    except asyncio.TimeoutError:
        print("  ❌ 完整处理超时（>20秒）")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

asyncio.run(test())