"""
简化测试认知循环
"""
import asyncio
from core.cognitive_loop import CognitiveLoop, LoopState


async def main():
    print("=" * 60)
    print("认知循环测试")
    print("=" * 60)
    
    loop = CognitiveLoop()
    
    print("\n=== 测试单个循环 ===")
    result = await loop.run_cycle({"test": "signal"})
    print(f"✓ 循环ID: {result.cycle_id}")
    print(f"✓ 状态: {result.state.value}")
    print(f"✓ 处理信号数: {result.signals_processed}")
    print(f"✓ 置信度: {result.confidence:.2f}")
    print(f"✓ 持续时间: {result.duration_ms:.2f}ms")
    print(f"✓ 洞察: {result.insights}")
    
    print("\n=== 测试多个循环 ===")
    for i in range(5):
        signal = {"success": True, "data": f"test_{i}"}
        result = await loop.run_cycle(signal)
        print(f"  循环{i+1}: 状态={result.state.value}, 置信度={result.confidence:.2f}")
    
    print("\n=== 测试错误处理 ===")
    error_result = await loop.run_cycle(Exception("测试错误"))
    print(f"✓ 错误已处理: {error_result.error is not None}")
    print(f"✓ 洞察: {error_result.insights}")
    
    print("\n=== 状态报告 ===")
    status = loop.get_status()
    print(f"✓ 状态: {status['state']}")
    print(f"✓ 循环数: {status['metrics']['total_cycles']}")
    print(f"✓ 成功率: {status['metrics']['success_rate']:.2f}")
    print(f"✓ 阶段: {status['rhythm']['current_phase']}")
    print(f"✓ 知识节点: {status['knowledge']['total_nodes']}")
    
    print("\n" + "=" * 60)
    print("✅ 认知循环测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())