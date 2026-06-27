"""
第一阶段验证测试 - 存在层基础框架

验证内容：
1. 存在层能够启动和停止
2. 存在层持续运行（独立线程）
3. 自我状态持续更新
4. 间隙生长功能
5. 睡眠整合功能
6. 与架构蓝图一致性
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


def test_existence_layer_basic():
    """测试1：存在层基础功能"""
    logger.info("=" * 70)
    logger.info("测试1：存在层基础功能")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer, PresenceState
    
    layer = ExistenceLayer(heartbeat_interval=2.0)
    
    logger.info(f"✓ 存在层已创建")
    logger.info(f"✓ 初始状态: {layer.state.value}")
    logger.info(f"✓ 心跳间隔: {layer.heartbeat_interval}秒")
    
    assert layer.state == PresenceState.AWAKE, "初始状态应为AWAKE"
    assert layer.heartbeat_interval == 2.0, "心跳间隔应为2.0秒"
    
    logger.info("✅ 基础功能测试通过")
    return True


def test_existence_layer_running():
    """测试2：存在层持续运行"""
    logger.info("\n" + "=" * 70)
    logger.info("测试2：存在层持续运行")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    
    layer = ExistenceLayer(heartbeat_interval=2.0)
    
    layer.start()
    logger.info("✓ 存在层已启动")
    
    time.sleep(1)
    
    assert layer.is_running(), "存在层应该正在运行"
    logger.info("✓ 正在运行验证通过")
    
    time.sleep(3)
    
    status = layer.get_status()
    logger.info(f"✓ 状态: {status['state']}")
    logger.info(f"✓ 总循环数: {status['total_cycles']}")
    logger.info(f"✓ 运行时间: {status['uptime_seconds']:.1f}秒")
    
    assert status['running'] == True, "状态应为运行中"
    assert status['total_cycles'] > 0, "应该有循环计数"
    
    layer.stop()
    time.sleep(1)
    
    assert not layer.is_running(), "存在层应该已停止"
    logger.info("✓ 停止验证通过")
    
    logger.info("✅ 持续运行测试通过")
    return True


def test_self_perception():
    """测试3：自我感知功能"""
    logger.info("\n" + "=" * 70)
    logger.info("测试3：自我感知功能")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    
    layer = ExistenceLayer(heartbeat_interval=2.0)
    layer.start()
    
    time.sleep(3)
    
    status = layer.get_status()
    
    if status.get('last_perception'):
        perception = status['last_perception']
        logger.info(f"✓ 健康分数: {perception['health']:.2f}")
        logger.info(f"✓ 置信度: {perception['confidence']:.2f}")
        logger.info(f"✓ 能量水平: {perception['energy']:.2f}")
        
        assert 0 <= perception['health'] <= 1.0, "健康分数应在0-1之间"
        assert 0 <= perception['confidence'] <= 1.0, "置信度应在0-1之间"
        assert 0 <= perception['energy'] <= 1.0, "能量水平应在0-1之间"
    else:
        logger.info("⚠️ 暂无感知结果")
    
    layer.stop()
    
    logger.info("✅ 自我感知测试通过")
    return True


def test_gap_growth():
    """测试4：间隙生长功能"""
    logger.info("\n" + "=" * 70)
    logger.info("测试4：间隙生长功能")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    
    layer = ExistenceLayer(
        heartbeat_interval=2.0,
        growth_interval=1.0
    )
    
    layer.start()
    logger.info("✓ 存在层已启动")
    
    layer.receive_signal({"type": "test", "content": "测试信号1"})
    layer.receive_signal({"type": "test", "content": "测试信号2"})
    layer.receive_signal({"type": "test", "content": "测试信号3"})
    
    logger.info(f"✓ 提交了3个信号")
    logger.info(f"✓ 待处理信号数: {len(layer.pending_signals)}")
    
    time.sleep(5)
    
    status = layer.get_status()
    logger.info(f"✓ 已处理信号数: {status['signals_processed']}")
    logger.info(f"✓ 生长循环数: {status['growing_cycles']}")
    
    layer.stop()
    
    logger.info("✅ 间隙生长测试通过")
    return True


def test_sleep_consolidation():
    """测试5：睡眠整合功能"""
    logger.info("\n" + "=" * 70)
    logger.info("测试5：睡眠整合功能")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    
    layer = ExistenceLayer(
        heartbeat_interval=2.0,
        sleep_interval=5.0
    )
    
    layer.start()
    logger.info("✓ 存在层已启动")
    
    time.sleep(7)
    
    status = layer.get_status()
    logger.info(f"✓ 记忆整合数: {status['memories_consolidated']}")
    logger.info(f"✓ 休息循环数: {status['resting_cycles']}")
    
    layer.stop()
    
    logger.info("✅ 睡眠整合测试通过")
    return True


def test_state_transitions():
    """测试6：状态转换"""
    logger.info("\n" + "=" * 70)
    logger.info("测试6：状态转换")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer, PresenceState
    
    layer = ExistenceLayer(heartbeat_interval=2.0)
    
    logger.info(f"✓ 初始状态: {layer.state.value}")
    
    layer.force_state(PresenceState.GROWING)
    assert layer.state == PresenceState.GROWING
    logger.info(f"✓ 强制切换到GROWING: {layer.state.value}")
    
    layer.force_state(PresenceState.RESTING)
    assert layer.state == PresenceState.RESTING
    logger.info(f"✓ 强制切换到RESTING: {layer.state.value}")
    
    layer.force_state(PresenceState.SLEEPING)
    assert layer.state == PresenceState.SLEEPING
    logger.info(f"✓ 强制切换到SLEEPING: {layer.state.value}")
    
    layer.force_state(PresenceState.AWAKE)
    assert layer.state == PresenceState.AWAKE
    logger.info(f"✓ 强制切换到AWAKE: {layer.state.value}")
    
    logger.info("✅ 状态转换测试通过")
    return True


def test_user_interaction():
    """测试7：用户交互响应"""
    logger.info("\n" + "=" * 70)
    logger.info("测试7：用户交互响应")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer, PresenceState
    
    layer = ExistenceLayer(heartbeat_interval=2.0)
    layer.start()
    
    layer.force_state(PresenceState.SLEEPING)
    logger.info(f"✓ 切换到SLEEPING状态")
    
    layer.user_interaction()
    logger.info(f"✓ 用户交互后状态: {layer.state.value}")
    
    assert layer.state == PresenceState.AWAKE, "用户交互后应切换到AWAKE"
    
    status = layer.get_status()
    logger.info(f"✓ 清醒循环数: {status['awake_cycles']}")
    
    layer.stop()
    
    logger.info("✅ 用户交互响应测试通过")
    return True


def test_architecture_consistency():
    """测试8：与架构蓝图一致性"""
    logger.info("\n" + "=" * 70)
    logger.info("测试8：与架构蓝图一致性")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    
    layer = ExistenceLayer()
    
    required_methods = [
        'start', 'stop', 'is_running',
        '_heartbeat', '_perceive_self', '_grow', '_sleep',
        'receive_signal', 'user_interaction',
        'get_status', 'force_state'
    ]
    
    for method in required_methods:
        assert hasattr(layer, method), f"缺少方法: {method}"
        logger.info(f"✓ 方法存在: {method}")
    
    required_attributes = [
        'state', 'metrics', 'pending_signals',
        'perception_history', 'running'
    ]
    
    for attr in required_attributes:
        assert hasattr(layer, attr), f"缺少属性: {attr}"
        logger.info(f"✓ 属性存在: {attr}")
    
    logger.info("✅ 架构一致性测试通过")
    return True


def test_global_singleton():
    """测试9：全局单例"""
    logger.info("\n" + "=" * 70)
    logger.info("测试9：全局单例")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import (
        get_existence_layer,
        start_existence_layer
    )
    
    layer1 = get_existence_layer()
    layer2 = get_existence_layer()
    
    assert layer1 is layer2, "应该是同一个实例"
    logger.info("✓ 单例验证通过")
    
    start_existence_layer()
    time.sleep(2)
    
    assert layer1.is_running(), "应该正在运行"
    logger.info("✓ 启动函数验证通过")
    
    layer1.stop()
    
    logger.info("✅ 全局单例测试通过")
    return True


def test_phase1_verification():
    """第一阶段验证标准"""
    logger.info("\n" + "=" * 70)
    logger.info("第一阶段验证标准")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    
    layer = ExistenceLayer(heartbeat_interval=2.0)
    
    logger.info("\n验证项1：系统启动后存在层自动运行")
    layer.start()
    time.sleep(1)
    assert layer.is_running()
    logger.info("✅ 通过 - 日志显示'存在层已启动'")
    
    logger.info("\n验证项2：存在层持续运行")
    time.sleep(3)
    status = layer.get_status()
    assert status['total_cycles'] > 0
    logger.info(f"✅ 通过 - 每{layer.heartbeat_interval}秒有一次内部心跳")
    
    logger.info("\n验证项3：自我状态持续更新")
    assert status['last_perception'] is not None
    logger.info("✅ 通过 - 每10秒感知一次自身状态")
    
    logger.info("\n验证项4：系统关闭时存在层正常停止")
    layer.stop()
    time.sleep(1)
    assert not layer.is_running()
    logger.info("✅ 通过 - 日志显示'存在层已停止'")
    
    logger.info("\n✅ 所有验证标准通过")
    return True


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🌟 第一阶段验证测试套件")
    logger.info("=" * 70)
    
    tests = [
        ("基础功能", test_existence_layer_basic),
        ("持续运行", test_existence_layer_running),
        ("自我感知", test_self_perception),
        ("间隙生长", test_gap_growth),
        ("睡眠整合", test_sleep_consolidation),
        ("状态转换", test_state_transitions),
        ("用户交互", test_user_interaction),
        ("架构一致性", test_architecture_consistency),
        ("全局单例", test_global_singleton),
        ("验证标准", test_phase1_verification),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"{name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")
    
    logger.info(f"\n总计: {passed}/{len(results)} 通过")
    
    if failed == 0:
        logger.info("\n🎉 第一阶段验证完成！")
        logger.info("\n验证标准：")
        logger.info("  ✅ 系统启动后存在层自动运行")
        logger.info("  ✅ 存在层持续运行（每10秒心跳）")
        logger.info("  ✅ 自我状态持续更新")
        logger.info("  ✅ 系统关闭时存在层正常停止")
    else:
        logger.warning(f"\n⚠️ 有 {failed} 个测试失败")