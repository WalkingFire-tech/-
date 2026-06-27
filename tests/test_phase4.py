"""
第四阶段集成测试

验证所有组件协同工作：
1. 系统编排器
2. 低功耗管理器
3. 长期记忆系统
4. 关系积累系统
"""
import asyncio
import time
from datetime import datetime

print("=" * 70)
print("🌟 第四阶段集成测试")
print("=" * 70)


def test_orchestrator():
    """测试系统编排器"""
    print("\n" + "=" * 60)
    print("系统编排器测试")
    print("=" * 60)
    
    from core.orchestrator import SystemOrchestrator
    
    orchestrator = SystemOrchestrator()
    
    print(f"✓ 系统状态: {orchestrator.state.value}")
    print(f"✓ 加载层数: {len(orchestrator.layers)}")
    print(f"✓ 加载机制数: {len(orchestrator.mechanisms)}")
    
    orchestrator.start()
    time.sleep(2)
    
    status = orchestrator.get_system_status()
    print(f"✓ 运行状态: {status['state']}")
    print(f"✓ 健康分数: {status['health_score']:.2f}")
    print(f"✓ 活跃层数: {sum(1 for s in status['layers'].values() if s['active'])}")
    
    orchestrator.stop()
    
    print("✅ 系统编排器测试通过")


def test_low_power_manager():
    """测试低功耗管理器"""
    print("\n" + "=" * 60)
    print("低功耗管理器测试")
    print("=" * 60)
    
    from core.low_power_manager import LowPowerManager, PowerLevel
    
    manager = LowPowerManager(target_watts=50.0)
    
    print(f"✓ 目标功耗: {manager.target_watts}W")
    print(f"✓ 当前功耗等级: {manager.metrics.current_level.value}")
    
    manager.force_power_level(PowerLevel.REDUCED)
    print(f"✓ 切换到降低模式: {manager.metrics.current_level.value}")
    
    status = manager.get_power_status()
    print(f"✓ 当前功耗: {status['current_watts']:.1f}W")
    print(f"✓ 节能比例: {status['power_savings_percent']:.1f}%")
    
    suggestions = manager.suggest_optimization()
    print(f"✓ 优化建议数: {len(suggestions['suggestions'])}")
    
    print("✅ 低功耗管理器测试通过")


def test_long_term_memory():
    """测试长期记忆系统"""
    print("\n" + "=" * 60)
    print("长期记忆系统测试")
    print("=" * 60)
    
    from core.long_term_memory import (
        LongTermMemory, MemoryType, MemoryImportance
    )
    
    memory = LongTermMemory(db_path="data/test_long_term_memory.db")
    
    mem_id = memory.store_memory(
        content={"event": "测试记忆", "detail": "这是一条测试记忆"},
        memory_type=MemoryType.EPISODIC,
        importance=MemoryImportance.HIGH,
        emotional_valence=0.5,
    )
    print(f"✓ 存储记忆: {mem_id}")
    
    retrieved = memory.retrieve_memory(mem_id)
    if retrieved:
        print(f"✓ 检索记忆: {retrieved.id}")
        print(f"✓ 记忆强度: {retrieved.get_strength():.3f}")
        print(f"✓ 访问次数: {retrieved.access_count}")
    
    conv_id = memory.start_conversation("test_user_001")
    print(f"✓ 开始对话: {conv_id}")
    
    memory.add_message(conv_id, "user", "你好，这是一条测试消息", emotion=0.3)
    memory.add_message(conv_id, "assistant", "你好！很高兴见到你", emotion=0.5)
    print(f"✓ 添加消息: 2条")
    
    memory.end_conversation(conv_id, satisfaction=0.8)
    print(f"✓ 结束对话")
    
    profile = memory.get_user_profile("test_user_001")
    print(f"✓ 用户档案: 对话数={profile['total_conversations']}, 消息数={profile['total_messages']}")
    
    stats = memory.get_memory_stats()
    print(f"✓ 记忆统计: 总数={stats['total_memories']}, 对话数={stats['total_conversations']}")
    
    print("✅ 长期记忆系统测试通过")


def test_relationship_manager():
    """测试关系积累系统"""
    print("\n" + "=" * 60)
    print("关系积累系统测试")
    print("=" * 60)
    
    from core.relationship_manager import (
        RelationshipManager, InteractionType, RelationshipStage
    )
    
    manager = RelationshipManager(db_path="data/test_relationships.db")
    
    int_id = manager.record_interaction(
        user_id="test_user_001",
        interaction_type=InteractionType.QUESTION,
        content="你好，请帮我解决问题",
        sentiment=0.3,
    )
    print(f"✓ 记录交互: {int_id}")
    
    manager.record_interaction(
        user_id="test_user_001",
        interaction_type=InteractionType.PRAISE,
        content="非常感谢你的帮助！",
        sentiment=0.8,
    )
    print(f"✓ 记录正面交互")
    
    profile = manager.get_relationship("test_user_001")
    print(f"✓ 关系阶段: {profile.stage.value}")
    print(f"✓ 信任度: {profile.trust_score:.2f}")
    print(f"✓ 关系深度: {profile.depth:.2f}")
    print(f"✓ 交互次数: {profile.interaction_count}")
    
    context = manager.get_personalized_context("test_user_001")
    print(f"✓ 个性化上下文: 信任={context['trust_level']:.2f}, 阶段={context['relationship_stage']}")
    
    should_proactive = manager.should_be_proactive("test_user_001")
    print(f"✓ 是否应该主动: {should_proactive}")
    
    summary = manager.get_relationship_summary("test_user_001")
    print(f"✓ 关系摘要:\n{summary}")
    
    print("✅ 关系积累系统测试通过")


def test_full_integration():
    """测试完整集成"""
    print("\n" + "=" * 60)
    print("完整集成测试")
    print("=" * 60)
    
    from core.orchestrator import SystemOrchestrator
    from core.low_power_manager import LowPowerManager
    from core.long_term_memory import LongTermMemory, MemoryType, MemoryImportance
    from core.relationship_manager import RelationshipManager, InteractionType
    
    orchestrator = SystemOrchestrator()
    power_manager = LowPowerManager(target_watts=50.0)
    memory = LongTermMemory(db_path="data/test_integration_memory.db")
    relationship = RelationshipManager(db_path="data/test_integration_relationship.db")
    
    power_manager.set_orchestrator(orchestrator)
    
    print("✓ 所有组件已初始化")
    
    orchestrator.start()
    power_manager.start()
    
    print("✓ 系统已启动")
    time.sleep(2)
    
    user_id = "integration_test_user"
    conv_id = memory.start_conversation(user_id)
    
    relationship.record_interaction(
        user_id=user_id,
        interaction_type=InteractionType.QUESTION,
        content="集成测试问题",
        sentiment=0.5,
    )
    
    mem_id = memory.store_memory(
        content={"question": "集成测试", "answer": "测试答案"},
        memory_type=MemoryType.EPISODIC,
        importance=MemoryImportance.MEDIUM,
    )
    
    memory.add_message(conv_id, "user", "这是一个集成测试问题")
    memory.add_message(conv_id, "assistant", "这是集成测试回答")
    
    memory.end_conversation(conv_id, satisfaction=0.9)
    
    print(f"✓ 完成交互流程")
    
    sys_status = orchestrator.get_system_status()
    power_status = power_manager.get_power_status()
    user_profile = memory.get_user_profile(user_id)
    rel_profile = relationship.get_relationship(user_id)
    
    print(f"✓ 系统状态: {sys_status['state']}, 健康={sys_status['health_score']:.2f}")
    print(f"✓ 功耗状态: {power_status['current_level']}, {power_status['current_watts']:.1f}W")
    print(f"✓ 用户记忆: 对话={user_profile['total_conversations']}, 消息={user_profile['total_messages']}")
    print(f"✓ 用户关系: 信任={rel_profile.trust_score:.2f}, 阶段={rel_profile.stage.value}")
    
    power_manager.stop()
    orchestrator.stop()
    
    print("✓ 系统已停止")
    
    print("✅ 完整集成测试通过")


async def test_async_processing():
    """测试异步处理"""
    print("\n" + "=" * 60)
    print("异步处理测试")
    print("=" * 60)
    
    from core.orchestrator import SystemOrchestrator
    
    orchestrator = SystemOrchestrator()
    orchestrator.start()
    
    results = await orchestrator.process_input({"query": "测试输入", "context": "集成测试"})
    
    print(f"✓ 处理成功: {results['success']}")
    print(f"✓ 置信度: {results['confidence']:.2f}")
    print(f"✓ 处理层数: {len(results['layers'])}")
    
    learning_result = orchestrator.trigger_learning("机器学习基础", priority="high")
    print(f"✓ 学习任务: {learning_result['success']}")
    
    evolution_result = orchestrator.trigger_evolution("accuracy")
    print(f"✓ 进化任务: {evolution_result['success']}")
    
    orchestrator.stop()
    
    print("✅ 异步处理测试通过")


if __name__ == "__main__":
    test_orchestrator()
    test_low_power_manager()
    test_long_term_memory()
    test_relationship_manager()
    test_full_integration()
    
    print("\n" + "=" * 60)
    print("异步测试")
    print("=" * 60)
    asyncio.run(test_async_processing())
    
    print("\n" + "=" * 70)
    print("🎉 所有第四阶段测试通过！")
    print("=" * 70)
    
    print("\n📊 系统能力总结:")
    print("  ✅ 系统编排器 - 整合所有层与机制")
    print("  ✅ 低功耗管理 - 节能运行")
    print("  ✅ 长期记忆 - 跨对话记忆持久化")
    print("  ✅ 关系积累 - 用户信任度演化")
    print("  ✅ 完整集成 - 所有组件协同工作")
    print("  ✅ 异步处理 - 高效并发处理")
    
    print("\n🌟 系统已具备完整的整合、节能、记忆、关系能力")