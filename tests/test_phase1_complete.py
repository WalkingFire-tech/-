"""
第一阶段完整测试 - 存在层、自我感知、间隙生长、睡眠整合

验证所有第一阶段组件的正确性和集成。
"""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def test_existence_layer():
    """测试存在层"""
    logger.info("=" * 70)
    logger.info("测试 1: 存在层")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer, PresenceState
    
    layer = ExistenceLayer(
        heartbeat_interval=2.0,
        growth_interval=1.0,
        rest_interval=5.0,
        sleep_interval=10.0,
    )
    
    logger.info(f"✓ 初始状态: {layer.state.value}")
    assert layer.state == PresenceState.AWAKE
    
    layer.start()
    logger.info("✓ 存在层已启动")
    
    time.sleep(3)
    
    assert layer.is_running(), "存在层应该正在运行"
    logger.info("✓ 正在运行验证通过")
    
    status = layer.get_status()
    logger.info(f"✓ 状态: {status['state']}")
    logger.info(f"✓ 总循环数: {status['total_cycles']}")
    logger.info(f"✓ 运行时间: {status['uptime_seconds']:.1f}秒")
    
    assert status['running'] == True
    assert status['total_cycles'] > 0
    
    layer.receive_signal({"type": "test", "content": "测试信号"})
    logger.info(f"✓ 接收信号后待处理: {len(layer.pending_signals)}")
    
    layer.user_interaction()
    assert layer.state == PresenceState.AWAKE
    logger.info("✓ 用户交互后状态正确")
    
    layer.force_state(PresenceState.GROWING)
    assert layer.state == PresenceState.GROWING
    logger.info("✓ 强制状态切换正确")
    
    layer.stop()
    time.sleep(1)
    
    logger.info("✅ 存在层测试通过")
    return True


def test_self_perception():
    """测试自我感知模块"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 2: 自我感知模块")
    logger.info("=" * 70)
    
    from core.presence.self_perception import (
        SelfPerceptionModule, HealthIndicator
    )
    
    module = SelfPerceptionModule()
    
    logger.info("✓ 模块已初始化")
    
    perception = module.perceive()
    logger.info(f"✓ 感知结果:")
    logger.info(f"  健康分数: {perception.health_score:.2f}")
    logger.info(f"  置信度: {perception.confidence_level:.2f}")
    logger.info(f"  能量水平: {perception.energy_level:.2f}")
    logger.info(f"  知识增长: {perception.knowledge_growth:.2f}")
    logger.info(f"  关系健康: {perception.relationship_health:.2f}")
    
    assert 0 <= perception.health_score <= 1.0
    assert 0 <= perception.confidence_level <= 1.0
    assert 0 <= perception.energy_level <= 1.0
    
    module.update_knowledge_metrics({
        "total_knowledge": 50,
        "recent_additions": 10,
        "validation_rate": 0.8
    })
    logger.info("✓ 知识指标已更新")
    
    module.update_relationship_metrics({
        "trust_level": 0.9,
        "positive_rate": 0.85
    })
    logger.info("✓ 关系指标已更新")
    
    module.report_subsystem_status("test_system", False)
    logger.info("✓ 子系统状态已报告")
    
    health_report = module.get_health_report()
    logger.info(f"✓ 健康报告: {health_report['indicator']}")
    
    module.start()
    time.sleep(2)
    assert module.is_running()
    logger.info("✓ 监控已启动")
    
    module.stop()
    logger.info("✓ 监控已停止")
    
    logger.info("✅ 自我感知模块测试通过")
    return True


def test_gap_growth():
    """测试间隙生长引擎"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 3: 间隙生长引擎")
    logger.info("=" * 70)
    
    from core.presence.gap_growth import (
        GapGrowthEngine, SignalType, SignalPriority
    )
    
    engine = GapGrowthEngine()
    
    logger.info("✓ 引擎已初始化")
    
    engine.start()
    logger.info("✓ 引擎已启动")
    
    signal_id = engine.submit_signal(
        signal_type="knowledge_gap",
        content="测试知识缺口",
        source="test",
        priority="high"
    )
    logger.info(f"✓ 提交信号: {signal_id}")
    
    engine.submit_signal(
        signal_type="emotion_pattern",
        content="积极情绪",
        source="test",
        priority="medium"
    )
    logger.info("✓ 提交第二个信号")
    
    time.sleep(3)
    
    stats = engine.get_stats()
    logger.info(f"✓ 统计:")
    logger.info(f"  接收信号: {stats['signals_received']}")
    logger.info(f"  处理信号: {stats['signals_processed']}")
    logger.info(f"  生长事件: {stats['growth_events']}")
    
    assert stats['signals_received'] >= 2
    
    queue_status = engine.get_queue_status()
    logger.info(f"✓ 队列状态:")
    logger.info(f"  待处理: {queue_status['pending']}")
    logger.info(f"  已处理: {queue_status['processed']}")
    
    engine.stop()
    logger.info("✓ 引擎已停止")
    
    logger.info("✅ 间隙生长引擎测试通过")
    return True


def test_sleep_consolidation():
    """测试睡眠整合引擎"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 4: 睡眠整合引擎")
    logger.info("=" * 70)
    
    from core.presence.sleep_consolidation import (
        SleepConsolidationEngine, SleepStage
    )
    
    engine = SleepConsolidationEngine()
    
    logger.info("✓ 引擎已初始化")
    
    engine.start()
    logger.info("✓ 引擎已启动")
    
    engine.notify_interaction()
    logger.info("✓ 记录用户交互")
    
    time.sleep(2)
    
    status = engine.get_status()
    logger.info(f"✓ 状态:")
    logger.info(f"  运行中: {status['running']}")
    logger.info(f"  睡眠中: {status['is_sleeping']}")
    logger.info(f"  睡眠阶段: {status['sleep_stage']}")
    logger.info(f"  睡眠次数: {status['sleep_cycles']}")
    
    result = engine.force_consolidation(SleepStage.LIGHT)
    logger.info(f"✓ 强制整合:")
    logger.info(f"  整合记忆: {result['consolidated']}")
    logger.info(f"  固化技能: {result['solidified']}")
    logger.info(f"  重组知识: {result['reorganized']}")
    
    stats = engine.get_stats()
    logger.info(f"✓ 统计:")
    logger.info(f"  总整合次数: {stats['total_consolidations']}")
    logger.info(f"  总记忆数: {stats['total_memories_consolidated']}")
    
    engine.stop()
    logger.info("✓ 引擎已停止")
    
    logger.info("✅ 睡眠整合引擎测试通过")
    return True


def test_integration():
    """测试第一阶段集成"""
    logger.info("\n" + "=" * 70)
    logger.info("测试 5: 第一阶段集成")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer, PresenceState
    from core.presence.self_perception import SelfPerceptionModule
    from core.presence.gap_growth import GapGrowthEngine
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    logger.info("初始化所有组件...")
    
    existence = ExistenceLayer(
        heartbeat_interval=3.0,
        growth_interval=2.0,
        rest_interval=10.0,
        sleep_interval=20.0,
    )
    
    self_perception = SelfPerceptionModule()
    gap_growth = GapGrowthEngine()
    sleep_engine = SleepConsolidationEngine()
    
    logger.info("✓ 所有组件已初始化")
    
    logger.info("启动所有组件...")
    existence.start()
    self_perception.start()
    gap_growth.start()
    sleep_engine.start()
    
    logger.info("✓ 所有组件已启动")
    
    time.sleep(5)
    
    logger.info("测试信号流转...")
    existence.receive_signal({
        "type": "test_integration",
        "content": "集成测试信号",
        "source": "test"
    })
    
    gap_growth.submit_signal(
        signal_type="knowledge_gap",
        content="集成测试知识缺口",
        source="existence_layer",
        priority="high"
    )
    
    logger.info("✓ 信号已提交")
    
    time.sleep(3)
    
    logger.info("获取所有状态...")
    existence_status = existence.get_status()
    perception = self_perception.get_current_perception()
    gap_stats = gap_growth.get_stats()
    sleep_status = sleep_engine.get_status()
    
    logger.info(f"✓ 存在层: {existence_status['state']}, 循环: {existence_status['total_cycles']}")
    if perception:
        logger.info(f"✓ 自我感知: 健康={perception.health_score:.2f}, 能量={perception.energy_level:.2f}")
    logger.info(f"✓ 间隙生长: 接收={gap_stats['signals_received']}, 处理={gap_stats['signals_processed']}")
    logger.info(f"✓ 睡眠整合: 运行={sleep_status['running']}, 睡眠={sleep_status['is_sleeping']}")
    
    logger.info("停止所有组件...")
    existence.stop()
    self_perception.stop()
    gap_growth.stop()
    sleep_engine.stop()
    
    logger.info("✓ 所有组件已停止")
    
    logger.info("✅ 第一阶段集成测试通过")
    return True


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🌟 第一阶段完整测试套件")
    logger.info("=" * 70)
    
    results = []
    
    try:
        results.append(("存在层", test_existence_layer()))
    except Exception as e:
        logger.error(f"存在层测试失败: {e}")
        results.append(("存在层", False))
    
    try:
        results.append(("自我感知", test_self_perception()))
    except Exception as e:
        logger.error(f"自我感知测试失败: {e}")
        results.append(("自我感知", False))
    
    try:
        results.append(("间隙生长", test_gap_growth()))
    except Exception as e:
        logger.error(f"间隙生长测试失败: {e}")
        results.append(("间隙生长", False))
    
    try:
        results.append(("睡眠整合", test_sleep_consolidation()))
    except Exception as e:
        logger.error(f"睡眠整合测试失败: {e}")
        results.append(("睡眠整合", False))
    
    try:
        results.append(("集成测试", test_integration()))
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        results.append(("集成测试", False))
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 70)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        logger.info("\n🎉 所有第一阶段测试通过！")
    else:
        logger.warning(f"\n⚠️ 有 {failed} 个测试失败")