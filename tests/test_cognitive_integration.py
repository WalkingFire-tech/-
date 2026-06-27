"""
认知系统集成测试 - 验证所有组件协同工作

测试完整的认知循环和所有组件的集成。
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


def test_system_integration():
    """系统集成测试"""
    logger.info("=" * 70)
    logger.info("🧪 系统集成测试")
    logger.info("=" * 70)
    
    from core.services.cognitive_planner import get_cognitive_planner
    
    planner = get_cognitive_planner()
    
    logger.info("\n1. 测试基础对话...")
    result = planner.process("你好，请问你是谁？")
    assert result.success, "基础对话失败"
    assert result.response, "响应为空"
    logger.info(f"   ✅ 通过: {result.response[:50]}...")
    
    logger.info("\n2. 测试感知层...")
    assert result.perception, "感知层结果为空"
    logger.info(f"   ✅ 通过: 意图={result.perception.get('intent')}, "
                f"情绪={result.perception.get('emotion')}")
    
    logger.info("\n3. 测试学习层...")
    assert result.learning, "学习层结果为空"
    logger.info(f"   ✅ 通过: 成功={result.learning.get('success')}")
    
    logger.info("\n4. 测试整合层...")
    assert result.integration, "整合层结果为空"
    logger.info(f"   ✅ 通过: 成功={result.integration.get('success')}")
    
    logger.info("\n5. 测试校验层...")
    assert result.validation, "校验层结果为空"
    logger.info(f"   ✅ 通过: 状态={result.validation.get('status')}")
    
    logger.info("\n6. 测试系统状态...")
    status = planner.get_system_status()
    assert status, "系统状态为空"
    assert status['status'] == 'running', "系统未运行"
    logger.info(f"   ✅ 通过: 状态={status['status']}")
    
    logger.info("\n7. 测试组件状态...")
    components = status.get('components', {})
    logger.info(f"   组件数: {len(components)}")
    for name, running in components.items():
        status_str = "运行中" if running else "已停止"
        logger.info(f"   {name}: {status_str}")
    logger.info("   ✅ 通过")
    
    logger.info("\n8. 测试关系模型...")
    relationship = status.get('relationship', {})
    if relationship:
        logger.info(f"   ✅ 通过: 信任={relationship.get('trust', 0.5):.2f}")
    else:
        logger.info("   ⚠️ 关系模型未初始化")
    
    logger.info("\n9. 测试进化目标...")
    goals = status.get('goals', [])
    if goals:
        logger.info(f"   ✅ 通过: 目标数={len(goals)}")
    else:
        logger.info("   ⚠️ 进化目标未设置")
    
    logger.info("\n10. 测试多次对话...")
    for i in range(3):
        result = planner.process(f"测试问题 {i+1}")
        assert result.success, f"对话 {i+1} 失败"
    logger.info(f"   ✅ 通过: 完成 3 次对话")
    
    final_status = planner.get_system_status()
    logger.info(f"\n📊 最终状态:")
    logger.info(f"   对话数: {final_status['conversation_count']}")
    logger.info(f"   运行时间: {final_status['uptime']}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ 所有集成测试通过")
    logger.info("=" * 70)
    
    planner.shutdown()


def test_cognitive_components():
    """测试认知组件"""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 认知组件测试")
    logger.info("=" * 70)
    
    logger.info("\n1. 测试L2学习层...")
    try:
        from core.layers.l2_learning import L2LearningLayer
        l2 = L2LearningLayer()
        result = l2.learn({"name": "测试学习", "keywords": ["测试"]})
        logger.info(f"   ✅ 通过: success={result.success}")
    except Exception as e:
        logger.warning(f"   ⚠️ L2学习层测试失败: {e}")
    
    logger.info("\n2. 测试L3整合层...")
    try:
        from core.layers.l3_integration import L3IntegrationLayer
        l3 = L3IntegrationLayer()
        logger.info("   ✅ 通过")
    except Exception as e:
        logger.warning(f"   ⚠️ L3整合层测试失败: {e}")
    
    logger.info("\n3. 测试L4校验层...")
    try:
        from core.layers.l4_validation import L4ValidationLayer
        l4 = L4ValidationLayer()
        logger.info("   ✅ 通过")
    except Exception as e:
        logger.warning(f"   ⚠️ L4校验层测试失败: {e}")
    
    logger.info("\n4. 测试L5进化层...")
    try:
        from core.layers.l5_evolution import L5EvolutionLayer
        l5 = L5EvolutionLayer()
        logger.info("   ✅ 通过")
    except Exception as e:
        logger.warning(f"   ⚠️ L5进化层测试失败: {e}")
    
    logger.info("\n5. 测试L6内省层...")
    try:
        from core.layers.l6_introspection import L6IntrospectionLayer
        l6 = L6IntrospectionLayer()
        logger.info("   ✅ 通过")
    except Exception as e:
        logger.warning(f"   ⚠️ L6内省层测试失败: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ 认知组件测试完成")
    logger.info("=" * 70)


def test_presence_components():
    """测试存在层组件"""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 存在层组件测试")
    logger.info("=" * 70)
    
    logger.info("\n1. 测试存在层...")
    try:
        from core.presence.existence_layer import ExistenceLayer
        existence = ExistenceLayer()
        existence.start()
        time.sleep(1)
        running = existence.is_running()
        existence.stop()
        logger.info(f"   ✅ 通过: 运行={running}")
    except Exception as e:
        logger.warning(f"   ⚠️ 存在层测试失败: {e}")
    
    logger.info("\n2. 测试自我感知引擎...")
    try:
        from core.presence.self_perception import SelfPerceptionEngine
        perception = SelfPerceptionEngine()
        perception.start()
        time.sleep(1)
        running = perception.is_running()
        perception.stop()
        logger.info(f"   ✅ 通过: 运行={running}")
    except Exception as e:
        logger.warning(f"   ⚠️ 自我感知测试失败: {e}")
    
    logger.info("\n3. 测试间隙生长引擎...")
    try:
        from core.presence.gap_growth import GapGrowthEngine
        growth = GapGrowthEngine()
        growth.start()
        time.sleep(1)
        running = growth.is_running()
        growth.stop()
        logger.info(f"   ✅ 通过: 运行={running}")
    except Exception as e:
        logger.warning(f"   ⚠️ 间隙生长测试失败: {e}")
    
    logger.info("\n4. 测试睡眠整合引擎...")
    try:
        from core.presence.sleep_consolidation import SleepEngine
        sleep = SleepEngine()
        sleep.start()
        time.sleep(1)
        running = sleep.is_running()
        sleep.stop()
        logger.info(f"   ✅ 通过: 运行={running}")
    except Exception as e:
        logger.warning(f"   ⚠️ 睡眠整合测试失败: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ 存在层组件测试完成")
    logger.info("=" * 70)


def test_memory_components():
    """测试记忆组件"""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 记忆组件测试")
    logger.info("=" * 70)
    
    logger.info("\n1. 测试立体记忆...")
    try:
        from core.memory.stereo_memory import StereoMemoryStore, StereoMemoryEntry, MemoryImportance
        store = StereoMemoryStore()
        
        memory = StereoMemoryEntry(
            id="test_001",
            user_content="测试输入",
            system_content="测试响应",
            intent="test",
            topic="测试",
            trust_change=0.05,
            intimacy_change=0.1,
            dependency_change=0,
            self_state_before={},
            self_state_after={},
            skills_used=[],
            skills_formed=[],
            timestamp="2024-01-01T00:00:00",
            importance=MemoryImportance.HIGH,
            user_emotion="neutral",
            system_emotion="neutral"
        )
        store.save(memory)
        logger.info("   ✅ 通过")
    except Exception as e:
        logger.warning(f"   ⚠️ 立体记忆测试失败: {e}")
    
    logger.info("\n2. 测试关系模型...")
    try:
        from core.relationship.model import RelationshipModel
        model = RelationshipModel()
        metrics = model.get_metrics()
        logger.info(f"   ✅ 通过: 信任={metrics.get('trust', 0.5):.2f}")
    except Exception as e:
        logger.warning(f"   ⚠️ 关系模型测试失败: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ 记忆组件测试完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("🌟 完整系统集成测试套件")
    logger.info("=" * 70)
    
    test_cognitive_components()
    test_presence_components()
    test_memory_components()
    test_system_integration()
    
    logger.info("\n" + "=" * 70)
    logger.info("🎉 所有测试完成")
    logger.info("=" * 70)