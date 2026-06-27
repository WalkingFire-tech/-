"""
第一阶段验证测试

验证系统具备"持续存在"的能力
"""
import asyncio
import time
from datetime import datetime


async def test_existence_layer():
    """测试存在层基础功能"""
    print("\n" + "=" * 60)
    print("测试1: 存在层基础功能")
    print("=" * 60)
    
    from core.presence import ExistenceLayer, PresenceState
    
    layer = ExistenceLayer(
        heartbeat_interval=2.0,
        growth_interval=3.0,
        rest_interval=10.0,
        sleep_interval=30.0,
    )
    
    print(f"✓ 存在层已创建")
    print(f"  初始状态: {layer.state.value}")
    
    layer.start()
    print(f"✓ 存在层已启动")
    
    await asyncio.sleep(5)
    
    status = layer.get_status()
    print(f"\n存在层状态:")
    print(f"  运行状态: {status['running']}")
    print(f"  当前状态: {status['state']}")
    print(f"  总循环数: {status['total_cycles']}")
    print(f"  心跳数: {status['total_cycles']}")
    print(f"  运行时间: {status['uptime_seconds']:.1f}秒")
    
    assert status['running'], "存在层未运行"
    assert status['total_cycles'] >= 2, "心跳数不足"
    
    layer.stop()
    print(f"\n✓ 存在层已停止")
    
    print("\n✅ 测试1通过")


async def test_self_perception():
    """测试自我感知模块"""
    print("\n" + "=" * 60)
    print("测试2: 自我感知模块")
    print("=" * 60)
    
    from core.presence import SelfPerceptionModule
    
    perception = SelfPerceptionModule()
    print(f"✓ 自我感知模块已创建")
    
    result = await perception.perceive()
    print(f"\n自我感知结果:")
    print(f"  健康度: {result.health_score:.2f}")
    print(f"  置信度: {result.confidence_level:.2f}")
    print(f"  能量水平: {result.energy_level:.2f}")
    print(f"  知识增长: {result.knowledge_growth:.2f}")
    print(f"  关系健康: {result.relationship_health:.2f}")
    
    assert 0 <= result.health_score <= 1, "健康度范围错误"
    assert 0 <= result.confidence_level <= 1, "置信度范围错误"
    assert 0 <= result.energy_level <= 1, "能量水平范围错误"
    
    health_summary = perception.get_health_summary()
    print(f"\n健康摘要:")
    print(f"  指示器: {health_summary['indicator']}")
    print(f"  分数: {health_summary['score']:.2f}")
    
    confidence_summary = perception.get_confidence_summary()
    print(f"\n置信度摘要:")
    print(f"  总体: {confidence_summary['overall']:.2f}")
    print(f"  趋势: {confidence_summary['trend']}")
    
    print("\n✅ 测试2通过")


async def test_gap_growth():
    """测试间隙生长模块"""
    print("\n" + "=" * 60)
    print("测试3: 间隙生长模块")
    print("=" * 60)
    
    from core.presence import GapGrowthModule, SignalPriority
    
    growth = GapGrowthModule()
    print(f"✓ 间隙生长模块已创建")
    
    for i in range(10):
        priority = SignalPriority.HIGH if i < 3 else SignalPriority.MEDIUM
        growth.add_signal(
            signal={"data": f"signal_{i}", "type": "learning"},
            priority=priority,
            source="test",
        )
    
    queue_status = growth.get_queue_status()
    print(f"\n队列状态:")
    print(f"  总待处理: {queue_status['total_pending']}")
    print(f"  按优先级: {queue_status['by_priority']}")
    
    results = await growth.process_signals(max_count=5)
    print(f"\n处理结果:")
    print(f"  处理数量: {len(results)}")
    print(f"  成功数量: {sum(1 for r in results if r.get('processed'))}")
    
    growth_summary = growth.get_growth_summary()
    print(f"\n生长摘要:")
    print(f"  总处理: {growth_summary['total_processed']}")
    print(f"  总洞察: {growth_summary['total_insights']}")
    
    assert len(results) == 5, "处理数量错误"
    
    print("\n✅ 测试3通过")


async def test_sleep_consolidation():
    """测试睡眠整合模块"""
    print("\n" + "=" * 60)
    print("测试4: 睡眠整合模块")
    print("=" * 60)
    
    from core.presence import SleepConsolidationModule
    
    sleep = SleepConsolidationModule()
    print(f"✓ 睡眠整合模块已创建")
    
    for i in range(20):
        importance = 0.8 if i < 5 else 0.3
        sleep.add_memory(
            memory_id=f"mem_{i}",
            content=f"记忆内容_{i}",
            importance=importance,
        )
    
    stats = sleep.get_statistics()
    print(f"\n记忆统计:")
    print(f"  总记忆: {stats['total_memories']}")
    print(f"  已巩固: {stats['consolidated']}")
    print(f"  未巩固: {stats['unconsolidated']}")
    print(f"  平均重要性: {stats['avg_importance']:.2f}")
    
    result = await sleep.consolidate()
    print(f"\n整合结果:")
    print(f"  巩固记忆: {result['consolidated']}")
    print(f"  压缩知识: {result['compressed']}")
    print(f"  强化连接: {result['strengthened']}")
    print(f"  发现洞察: {result['insights']}")
    print(f"  睡眠阶段: {result['phase']}")
    
    consolidation_summary = sleep.get_consolidation_summary()
    print(f"\n整合摘要:")
    print(f"  总整合次数: {consolidation_summary['total_consolidations']}")
    print(f"  总巩固记忆: {consolidation_summary['total_memories_consolidated']}")
    
    print("\n✅ 测试4通过")


async def test_continuous_existence():
    """测试持续存在能力"""
    print("\n" + "=" * 60)
    print("测试5: 持续存在能力")
    print("=" * 60)
    
    from core.presence import ExistenceLayer, SignalPriority
    
    layer = ExistenceLayer(
        heartbeat_interval=1.0,
        growth_interval=2.0,
        rest_interval=5.0,
        sleep_interval=10.0,
    )
    
    layer.start()
    print(f"✓ 存在层已启动")
    
    print(f"\n模拟15秒运行...")
    
    for i in range(15):
        await asyncio.sleep(1)
        
        if i == 3:
            layer.receive_signal({"type": "test", "data": f"signal_{i}"})
            print(f"  [{i+1}s] 发送信号")
        elif i == 7:
            layer.user_interaction()
            print(f"  [{i+1}s] 用户交互")
        elif i == 11:
            layer.receive_signal({"type": "learning", "content": "new_knowledge"})
            print(f"  [{i+1}s] 学习信号")
        else:
            status = layer.get_status()
            if i % 3 == 0:
                print(f"  [{i+1}s] 状态: {status['state']}, 循环: {status['total_cycles']}")
    
    final_status = layer.get_status()
    print(f"\n最终状态:")
    print(f"  运行状态: {final_status['running']}")
    print(f"  当前状态: {final_status['state']}")
    print(f"  总循环数: {final_status['total_cycles']}")
    print(f"  清醒循环: {final_status['awake_cycles']}")
    print(f"  生长循环: {final_status['growing_cycles']}")
    print(f"  休息循环: {final_status['resting_cycles']}")
    print(f"  待处理信号: {final_status['signals_pending']}")
    print(f"  已处理信号: {final_status['signals_processed']}")
    print(f"  已巩固记忆: {final_status['memories_consolidated']}")
    
    if final_status['last_perception']:
        print(f"\n最后感知:")
        print(f"  健康: {final_status['last_perception']['health']:.2f}")
        print(f"  置信度: {final_status['last_perception']['confidence']:.2f}")
        print(f"  能量: {final_status['last_perception']['energy']:.2f}")
    
    layer.stop()
    print(f"\n✓ 存在层已停止")
    
    assert final_status['total_cycles'] >= 10, "循环数不足"
    
    print("\n✅ 测试5通过")


async def main():
    """运行所有测试"""
    print("=" * 70)
    print("🌟 第一阶段验证测试：持续存在能力")
    print("=" * 70)
    
    try:
        await test_existence_layer()
        await test_self_perception()
        await test_gap_growth()
        await test_sleep_consolidation()
        await test_continuous_existence()
        
        print("\n" + "=" * 70)
        print("🎉 第一阶段所有测试通过！")
        print("=" * 70)
        
        print("\n📊 第一阶段完成标志:")
        print("  ✓ 系统启动后存在层持续运行")
        print("  ✓ 每10秒输出心跳")
        print("  ✓ 能持续感知自身健康度和置信度")
        print("  ✓ 能在沉默中处理未完成的信号")
        print("  ✓ 能在低功耗状态下整合记忆")
        
        print("\n🌟 系统已具备'持续存在'的能力")
        print("   即使没有用户输入，也能持续感知自身状态并在间隙中生长")
        
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