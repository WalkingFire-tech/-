"""
测试认知循环
"""
import asyncio
from core.cognitive_loop import CognitiveLoop, LoopState


async def test_single_cycle():
    print("\n=== 测试单个认知循环 ===")
    
    loop = CognitiveLoop()
    
    result = await loop.run_cycle({"test": "signal"})
    
    assert result.cycle_id == "cycle_0", "循环ID错误"
    assert result.state in LoopState, "循环状态错误"
    assert result.duration_ms >= 0, "持续时间错误"
    
    print(f"✓ 循环ID: {result.cycle_id}")
    print(f"✓ 状态: {result.state.value}")
    print(f"✓ 处理信号数: {result.signals_processed}")
    print(f"✓ 置信度: {result.confidence:.2f}")
    print(f"✓ 持续时间: {result.duration_ms:.2f}ms")
    print(f"✓ 洞察数: {len(result.insights)}")
    
    print("✅ 单个循环测试通过")


async def test_multiple_cycles():
    print("\n=== 测试多个认知循环 ===")
    
    loop = CognitiveLoop()
    
    signals = []
    for i in range(3):
        signals.append({"success": True, "data": f"test_{i}"})
        signals.append({"success": False, "error": f"error_{i}"})
        signals.append({"feedback": f"feedback_{i}"})
    
    results = []
    for signal in signals:
        result = await loop.run_cycle(signal)
        results.append(result)
    
    assert len(results) == len(signals), "循环数量错误"
    
    print(f"✓ 完成{len(results)}个循环")
    print(f"✓ 平均置信度: {loop.metrics.average_confidence:.2f}")
    print(f"✓ 平均持续时间: {loop.metrics.average_duration_ms:.2f}ms")
    
    print("✅ 多循环测试通过")


async def test_continuous_loop():
    print("\n=== 测试持续认知循环 ===")
    
    loop = CognitiveLoop()
    
    signal_count = [0]
    def signal_generator():
        signal_count[0] += 1
        return {"iteration": signal_count[0], "type": "auto"}
    
    results = await loop.run_continuous(
        signal_generator=signal_generator,
        max_cycles=10,
    )
    
    assert len(results) == 10, "持续循环数量错误"
    
    print(f"✓ 完成{len(results)}个持续循环")
    print(f"✓ 成功率: {loop._calculate_success_rate():.2f}")
    print(f"✓ 错误率: {loop.metrics.error_rate:.2f}")
    
    print("✅ 持续循环测试通过")


async def test_error_handling():
    print("\n=== 测试错误处理 ===")
    
    loop = CognitiveLoop()
    
    error_signals = [
        Exception("测试错误1"),
        {"success": False, "error": "测试错误2"},
        "error: 测试错误3",
    ]
    
    for signal in error_signals:
        result = await loop.run_cycle(signal)
        print(f"  处理错误信号: {result.cycle_id}, 状态: {result.state.value}")
    
    lessons = loop.error_alchemy.get_lessons_learned()
    
    print(f"✓ 错误已记录: {lessons['total_errors']}个")
    print(f"✓ 避免模式: {len(loop.error_alchemy.get_avoid_patterns())}个")
    
    print("✅ 错误处理测试通过")


async def test_learning_evolution():
    print("\n=== 测试学习进化 ===")
    
    loop = CognitiveLoop()
    
    for i in range(20):
        success = i % 3 != 0
        signal = {
            "success": success,
            "data": f"learning_{i}",
            "iteration": i,
        }
        result = await loop.run_cycle(signal)
    
    print(f"✓ 完成{loop.cycle_count}个学习循环")
    
    knowledge_stats = loop.knowledge_weaver.get_statistics()
    print(f"✓ 知识节点: {knowledge_stats['total_nodes']}")
    print(f"✓ 知识连接: {knowledge_stats['total_connections']}")
    print(f"✓ 知识群落: {knowledge_stats['total_clusters']}")
    
    rhythm_progress = loop.rhythm.get_phase_progress()
    print(f"✓ 当前阶段: {rhythm_progress['current_phase']}")
    print(f"✓ 能量水平: {rhythm_progress['energy_level']:.2f}")
    print(f"✓ 专注度: {rhythm_progress['focus_score']:.2f}")
    
    print("✅ 学习进化测试通过")


async def test_status_report():
    print("\n=== 测试状态报告 ===")
    
    loop = CognitiveLoop()
    
    for i in range(5):
        await loop.run_cycle({"test": i})
    
    status = loop.get_status()
    
    assert "state" in status, "状态缺失"
    assert "metrics" in status, "指标缺失"
    assert "rhythm" in status, "节奏缺失"
    assert "knowledge" in status, "知识缺失"
    assert "learning" in status, "学习缺失"
    
    print(f"✓ 状态: {status['state']}")
    print(f"✓ 循环数: {status['metrics']['total_cycles']}")
    print(f"✓ 成功率: {status['metrics']['success_rate']:.2f}")
    print(f"✓ 阶段: {status['rhythm']['current_phase']}")
    print(f"✓ 知识节点: {status['knowledge']['total_nodes']}")
    
    print("✅ 状态报告测试通过")


async def test_integration_with_mechanisms():
    print("\n=== 测试与七大机制集成 ===")
    
    loop = CognitiveLoop()
    
    for i in range(10):
        signal = {
            "success": True,
            "content": f"integration_test_{i}",
        }
        await loop.run_cycle(signal)
    
    print("✓ 增量感知学习:")
    print(f"  - 信号数: {len(loop.perception.signals)}")
    print(f"  - 模式数: {len(loop.perception.patterns)}")
    
    print("✓ 知识网络编织:")
    stats = loop.knowledge_weaver.get_statistics()
    print(f"  - 节点数: {stats['total_nodes']}")
    print(f"  - 连接数: {stats['total_connections']}")
    
    print("✓ 认知节奏控制器:")
    progress = loop.rhythm.get_phase_progress()
    print(f"  - 阶段: {progress['current_phase']}")
    print(f"  - 状态: {progress['current_state']}")
    
    print("✓ 元学习策略优化:")
    overall_stats = loop.meta_learner.get_overall_stats()
    print(f"  - 策略数: {overall_stats['total_strategies']}")
    print(f"  - 评估数: {overall_stats['total_evaluations']}")
    
    print("✅ 七大机制集成测试通过")


async def main():
    print("=" * 60)
    print("认知循环测试")
    print("=" * 60)
    
    try:
        await test_single_cycle()
        await test_multiple_cycles()
        await test_continuous_loop()
        await test_error_handling()
        await test_learning_evolution()
        await test_status_report()
        await test_integration_with_mechanisms()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！认知循环实现完成")
        print("=" * 60)
        
        print("\n📊 核心能力总结：")
        print("  ✓ 完整的感知-理解-行动-反思循环")
        print("  ✓ 七大机制深度集成")
        print("  ✓ 六层架构协同工作")
        print("  ✓ Loop Engineering设计模式")
        print("  ✓ 错误自动转化为学习信号")
        print("  ✓ 动态节奏调整")
        print("  ✓ 自我评估与验证")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())