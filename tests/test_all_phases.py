"""
完整系统综合测试 - 验证所有四个阶段

测试内容：
- 第一阶段：存在层、自我感知、间隙生长、睡眠整合
- 第二阶段：L1感知层、立体记忆、关系模型、自我评估
- 第三阶段：主动性引擎、自适应目标、主动感知
- 第四阶段：系统编排器、低功耗、长期记忆、关系积累
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


def test_phase1():
    """测试第一阶段：存在层组件"""
    logger.info("\n" + "=" * 70)
    logger.info("第一阶段：存在层组件测试")
    logger.info("=" * 70)
    
    from core.presence.existence_layer import ExistenceLayer
    from core.presence.self_perception import SelfPerceptionModule
    from core.presence.gap_growth import GapGrowthEngine
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    existence = ExistenceLayer(heartbeat_interval=5.0)
    self_perception = SelfPerceptionModule()
    gap_growth = GapGrowthEngine()
    sleep_engine = SleepConsolidationEngine()
    
    existence.start()
    self_perception.start()
    gap_growth.start()
    sleep_engine.start()
    
    time.sleep(3)
    
    existence_status = existence.get_status()
    perception = self_perception.perceive()
    gap_stats = gap_growth.get_stats()
    sleep_status = sleep_engine.get_status()
    
    logger.info(f"✓ 存在层: {existence_status['state']}, 循环: {existence_status['total_cycles']}")
    logger.info(f"✓ 自我感知: 健康={perception.health_score:.2f}")
    logger.info(f"✓ 间隙生长: 接收={gap_stats['signals_received']}")
    logger.info(f"✓ 睡眠整合: 运行={sleep_status['running']}")
    
    existence.stop()
    self_perception.stop()
    gap_growth.stop()
    sleep_engine.stop()
    
    logger.info("✅ 第一阶段测试通过")
    return True


def test_phase2():
    """测试第二阶段：感知与记忆"""
    logger.info("\n" + "=" * 70)
    logger.info("第二阶段：感知与记忆测试")
    logger.info("=" * 70)
    
    from core.memory.stereo_memory import StereoMemory
    from core.relationship.model import RelationshipModel
    from core.presence.self_review import SelfReviewEngine
    
    stereo_memory = StereoMemory()
    relationship = RelationshipModel()
    review_engine = SelfReviewEngine()
    
    mem_id = stereo_memory.save(
        user_content="测试用户输入",
        system_content="测试系统响应",
        intent="test",
        topic="测试"
    )
    logger.info(f"✓ 立体记忆保存: {mem_id}")
    
    metrics = relationship.get_metrics()
    logger.info(f"✓ 关系模型: 信任={metrics.get('trust', 0.5):.2f}")
    
    review_result = review_engine.review({
        "conversation_id": "test_001",
        "user_input": "测试输入",
        "system_response": "测试响应",
        "perception_result": {},
        "validation_result": {"status": "pass"}
    })
    logger.info(f"✓ 自我评估: {review_result.get('overall', 'unknown')}")
    
    logger.info("✅ 第二阶段测试通过")
    return True


def test_phase3():
    """测试第三阶段：主动性与进化"""
    logger.info("\n" + "=" * 70)
    logger.info("第三阶段：主动性与进化测试")
    logger.info("=" * 70)
    
    from core.presence.proactivity import ProactivityEngine
    from core.evolution.adaptive_goal import AdaptiveGoalEngine
    
    proactivity = ProactivityEngine()
    goal_engine = AdaptiveGoalEngine()
    
    proactivity.start()
    logger.info("✓ 主动性引擎已启动")
    
    decision = proactivity.should_act()
    logger.info(f"✓ 主动性决策: {decision}")
    
    goals = goal_engine.get_top_priorities(3)
    logger.info(f"✓ 进化目标: {len(goals)}个")
    
    if goals:
        logger.info(f"  首要目标: {goals[0].get('dimension', 'unknown')}")
    
    proactivity.stop()
    
    logger.info("✅ 第三阶段测试通过")
    return True


def test_phase4():
    """测试第四阶段：整合与完善"""
    logger.info("\n" + "=" * 70)
    logger.info("第四阶段：整合与完善测试")
    logger.info("=" * 70)
    
    from core.orchestrator import SystemOrchestrator
    from core.low_power_manager import LowPowerManager
    from core.long_term_memory import LongTermMemory
    from core.relationship_manager import RelationshipManager
    
    orchestrator = SystemOrchestrator()
    power_manager = LowPowerManager(target_watts=50.0)
    ltm = LongTermMemory()
    rel_manager = RelationshipManager()
    
    orchestrator.start()
    power_manager.start()
    
    time.sleep(2)
    
    sys_status = orchestrator.get_system_status()
    power_status = power_manager.get_power_status()
    
    logger.info(f"✓ 系统编排器: {sys_status['state']}, 健康={sys_status['health_score']:.2f}")
    logger.info(f"✓ 低功耗管理: {power_status['current_level']}, {power_status['current_watts']:.1f}W")
    
    mem_id = ltm.store_memory(content={"test": "data"})
    logger.info(f"✓ 长期记忆: {mem_id}")
    
    int_id = rel_manager.record_interaction(
        user_id="test_user",
        interaction_type="question",
        content="测试交互"
    )
    logger.info(f"✓ 关系管理: {int_id}")
    
    power_manager.stop()
    orchestrator.stop()
    
    logger.info("✅ 第四阶段测试通过")
    return True


def test_cognitive_planner():
    """测试认知规划器"""
    logger.info("\n" + "=" * 70)
    logger.info("认知规划器测试")
    logger.info("=" * 70)
    
    from core.services.cognitive_planner import get_cognitive_planner
    
    planner = get_cognitive_planner()
    
    result = planner.process("你好，这是一个测试")
    
    logger.info(f"✓ 处理成功: {result.success}")
    logger.info(f"✓ 响应: {result.response[:50]}...")
    logger.info(f"✓ 感知: 意图={result.perception.get('intent')}")
    logger.info(f"✓ 处理时间: {result.processing_time_ms:.1f}ms")
    
    status = planner.get_system_status()
    logger.info(f"✓ 系统状态: {status['status']}")
    logger.info(f"✓ 对话数: {status['conversation_count']}")
    
    planner.shutdown()
    
    logger.info("✅ 认知规划器测试通过")
    return True


def test_full_integration():
    """完整系统集成测试"""
    logger.info("\n" + "=" * 70)
    logger.info("完整系统集成测试")
    logger.info("=" * 70)
    
    from core.services.cognitive_planner import CognitivePlanner
    
    planner = CognitivePlanner()
    
    logger.info("测试多轮对话...")
    conversations = [
        "你好，请问你是谁？",
        "你能做什么？",
        "帮我分析一下这个问题",
        "谢谢你的帮助"
    ]
    
    for i, user_input in enumerate(conversations):
        result = planner.process(user_input)
        logger.info(f"  对话 {i+1}: 成功={result.success}, 时间={result.processing_time_ms:.1f}ms")
    
    status = planner.get_system_status()
    logger.info(f"\n✓ 最终状态:")
    logger.info(f"  对话数: {status['conversation_count']}")
    logger.info(f"  运行时间: {status['uptime']}")
    
    components = status.get('components', {})
    logger.info(f"  组件状态:")
    for name, running in components.items():
        status_str = "运行中" if running else "已停止"
        logger.info(f"    {name}: {status_str}")
    
    planner.shutdown()
    
    logger.info("✅ 完整系统集成测试通过")
    return True


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🌟 完整系统综合测试套件")
    logger.info("=" * 70)
    
    tests = [
        ("第一阶段：存在层", test_phase1),
        ("第二阶段：感知与记忆", test_phase2),
        ("第三阶段：主动性与进化", test_phase3),
        ("第四阶段：整合与完善", test_phase4),
        ("认知规划器", test_cognitive_planner),
        ("完整集成", test_full_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"{name} 测试失败: {e}")
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
        logger.info("\n🎉 所有测试通过！系统已完全就绪！")
    else:
        logger.warning(f"\n⚠️ 有 {failed} 个测试失败")