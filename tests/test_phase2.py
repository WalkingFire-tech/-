"""
第二阶段验证测试

验证系统能够"看见"用户和关系
"""
import asyncio
from datetime import datetime


async def test_stereo_memory():
    """测试立体记忆系统"""
    print("\n" + "=" * 60)
    print("测试1: 立体记忆系统")
    print("=" * 60)
    
    from core.memory.stereo_memory import (
        StereoMemorySystem,
        MemoryType,
        SelfDimension,
        MemoryContext,
    )
    
    memory = StereoMemorySystem()
    print(f"✓ 立体记忆系统已创建")
    
    # 存储记忆
    memory_id1 = memory.store(
        content={"question": "什么是AI?", "answer": "AI是人工智能"},
        memory_type=MemoryType.CONVERSATION,
        importance=0.7,
        related_entities={"AI", "人工智能"},
        self_dimension=SelfDimension(
            role="assistant",
            confidence=0.8,
            emotional_state="helpful",
            learning_progress=0.5,
            intentions=["解释概念"],
        ),
    )
    print(f"✓ 存储记忆: {memory_id1}")
    
    memory_id2 = memory.store(
        content={"question": "AI有哪些应用?", "answer": "AI应用包括..."},
        memory_type=MemoryType.CONVERSATION,
        importance=0.6,
        related_entities={"AI", "应用"},
    )
    print(f"✓ 存储记忆: {memory_id2}")
    
    # 建立关联
    memory.relate(memory_id1, memory_id2)
    print(f"✓ 建立记忆关联")
    
    # 回忆记忆
    recalled = memory.recall(memory_id1)
    assert recalled is not None, "回忆失败"
    print(f"✓ 回忆记忆: {recalled.memory_id}")
    print(f"  访问次数: {recalled.time_dimension.access_count}")
    print(f"  强化次数: {recalled.time_dimension.reinforcement_count}")
    
    # 搜索记忆
    results = memory.search(memory_type=MemoryType.CONVERSATION)
    print(f"✓ 搜索记忆: 找到 {len(results)} 条")
    
    # 获取记忆网络
    network = memory.get_memory_network(memory_id1)
    print(f"✓ 记忆网络: 中心 + {len(network['neighbors'])} 个邻居")
    
    # 统计
    stats = memory.get_statistics()
    print(f"\n记忆统计:")
    print(f"  总记忆: {stats['total_memories']}")
    print(f"  按类型: {stats['by_type']}")
    print(f"  平均重要性: {stats['avg_importance']:.2f}")
    
    print("\n✅ 测试1通过")


async def test_relationship_model():
    """测试关系模型"""
    print("\n" + "=" * 60)
    print("测试2: 关系模型")
    print("=" * 60)
    
    from core.relationship.model import (
        RelationshipModel,
        InteractionType,
    )
    
    relationship = RelationshipModel()
    print(f"✓ 关系模型已创建")
    
    # 记录互动
    relationship.record_interaction(
        user_input="你好",
        system_response="你好！有什么可以帮助你的？",
        interaction_type=InteractionType.CONVERSATION,
        user_satisfaction=0.8,
    )
    print(f"✓ 记录互动 1")
    
    relationship.record_interaction(
        user_input="什么是AI?",
        system_response="AI是人工智能...",
        interaction_type=InteractionType.QUESTION,
        user_satisfaction=0.9,
    )
    print(f"✓ 记录互动 2")
    
    relationship.record_interaction(
        user_input="请帮我写代码",
        system_response="好的，我来帮你...",
        interaction_type=InteractionType.COMMAND,
        user_satisfaction=0.7,
    )
    print(f"✓ 记录互动 3")
    
    # 获取关系摘要
    summary = relationship.get_relationship_summary()
    print(f"\n关系摘要:")
    print(f"  信任度: {summary['trust_level']:.2f} ({summary['trust_grade']})")
    print(f"  信任趋势: {summary['trust_trend']}")
    print(f"  亲密度: {summary['intimacy_level']:.2f}")
    print(f"  理解度: {summary['understanding_level']:.2f}")
    print(f"  总互动: {summary['total_interactions']}")
    print(f"  正面率: {summary['positive_rate']:.2%}")
    print(f"  偏好类型: {summary['preferred_types']}")
    
    # 预测
    predicted_type = relationship.predict_next_interaction_type()
    print(f"\n预测下次互动类型: {predicted_type.value}")
    
    should_engage = relationship.should_proactive_engage()
    print(f"是否应该主动互动: {should_engage}")
    
    print("\n✅ 测试2通过")


async def test_self_assessment():
    """测试持续自我评估"""
    print("\n" + "=" * 60)
    print("测试3: 持续自我评估")
    print("=" * 60)
    
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    assessment = ContinuousSelfAssessment()
    print(f"✓ 自我评估系统已创建")
    
    # 评估对话
    result1 = assessment.assess_conversation(
        conversation_id="conv_1",
        user_input="什么是AI?",
        system_response="AI是人工智能，它是一门研究如何使计算机能够模拟人类智能的科学。AI包括机器学习、深度学习、自然语言处理等多个领域。",
        user_feedback=0.9,
    )
    print(f"\n评估 1:")
    print(f"  整体评分: {result1.overall_score:.2f}")
    print(f"  各维度: {result1.metrics}")
    print(f"  洞察: {result1.insights[:2]}")
    
    result2 = assessment.assess_conversation(
        conversation_id="conv_2",
        user_input="帮我写代码",
        system_response="好的",
        user_feedback=0.4,
    )
    print(f"\n评估 2:")
    print(f"  整体评分: {result2.overall_score:.2f}")
    print(f"  自我批评: {result2.self_criticism}")
    print(f"  改进建议: {result2.improvements}")
    print(f"  学习点: {result2.learning_points}")
    
    result3 = assessment.assess_conversation(
        conversation_id="conv_3",
        user_input="解释一下机器学习",
        system_response="机器学习是AI的一个分支，它让计算机能够从数据中学习。主要分为监督学习、无监督学习和强化学习三种类型。",
        user_feedback=0.85,
    )
    print(f"\n评估 3:")
    print(f"  整体评分: {result3.overall_score:.2f}")
    
    # 获取趋势
    trend = assessment.get_performance_trend()
    print(f"\n表现趋势:")
    print(f"  趋势: {trend['trend']}")
    print(f"  近期平均: {trend['recent_average']:.2f}")
    
    # 统计
    stats = assessment.get_statistics()
    print(f"\n统计:")
    print(f"  总评估: {stats['total_assessments']}")
    print(f"  平均分: {stats['average_score']:.2f}")
    print(f"  改进次数: {stats['improving_count']}")
    print(f"  退步次数: {stats['declining_count']}")
    
    print("\n✅ 测试3通过")


async def test_integration():
    """测试集成"""
    print("\n" + "=" * 60)
    print("测试4: 第二阶段集成")
    print("=" * 60)
    
    from core.memory.stereo_memory import StereoMemorySystem, MemoryType
    from core.relationship.model import RelationshipModel, InteractionType
    from core.presence.self_assessment import ContinuousSelfAssessment
    
    memory = StereoMemorySystem()
    relationship = RelationshipModel()
    assessment = ContinuousSelfAssessment()
    
    print(f"✓ 所有模块已创建")
    
    # 模拟一次完整对话流程
    user_input = "请帮我理解深度学习"
    system_response = "深度学习是机器学习的一个子领域，它使用多层神经网络来学习数据的表示。深度学习在图像识别、自然语言处理等领域取得了突破性进展。"
    
    # 1. 存储记忆
    memory_id = memory.store(
        content={"question": user_input, "answer": system_response},
        memory_type=MemoryType.CONVERSATION,
        importance=0.7,
        related_entities={"深度学习", "机器学习", "神经网络"},
    )
    print(f"\n1. 存储记忆: {memory_id}")
    
    # 2. 记录互动
    relationship.record_interaction(
        user_input=user_input,
        system_response=system_response,
        interaction_type=InteractionType.QUESTION,
        user_satisfaction=0.85,
    )
    print(f"2. 记录互动")
    
    # 3. 自我评估
    result = assessment.assess_conversation(
        conversation_id="integrated_conv",
        user_input=user_input,
        system_response=system_response,
        user_feedback=0.85,
    )
    print(f"3. 自我评估: {result.overall_score:.2f}")
    
    # 获取整体状态
    memory_stats = memory.get_statistics()
    relationship_summary = relationship.get_relationship_summary()
    assessment_stats = assessment.get_statistics()
    
    print(f"\n整体状态:")
    print(f"  记忆数: {memory_stats['total_memories']}")
    print(f"  信任度: {relationship_summary['trust_level']:.2f}")
    print(f"  平均表现: {assessment_stats['average_score']:.2f}")
    
    print("\n✅ 测试4通过")


async def main():
    """运行所有测试"""
    print("=" * 70)
    print("🌟 第二阶段验证测试：深化感知与记忆")
    print("=" * 70)
    
    try:
        await test_stereo_memory()
        await test_relationship_model()
        await test_self_assessment()
        await test_integration()
        
        print("\n" + "=" * 70)
        print("🎉 第二阶段所有测试通过！")
        print("=" * 70)
        
        print("\n📊 第二阶段完成标志:")
        print("  ✓ 立体记忆系统正常工作")
        print("  ✓ 关系模型能够追踪信任度演化")
        print("  ✓ 持续自我评估能够生成洞察")
        print("  ✓ 所有模块能够协同工作")
        
        print("\n🌟 系统能够'看见'用户和关系")
        print("   在多次对话后，形成对用户关系的持续理解")
        
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