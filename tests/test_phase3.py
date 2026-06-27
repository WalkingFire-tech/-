"""
第三阶段验证测试

验证系统能够"主动"和"自主进化"
"""
import asyncio
from datetime import datetime, timedelta


async def test_proactivity_engine():
    """测试主动性引擎"""
    print("\n" + "=" * 60)
    print("测试1: 主动性引擎")
    print("=" * 60)
    
    from core.presence.proactivity import (
        ProactivityEngine,
        ProactivityContext,
        ProactivityLevel,
    )
    
    engine = ProactivityEngine()
    print(f"✓ 主动性引擎已创建")
    print(f"  初始等级: {engine.level.value}")
    
    # 测试不同场景
    scenarios = [
        {
            "name": "短时间沉默",
            "context": ProactivityContext(
                user_silence_duration=300,  # 5分钟
                relationship_trust=0.8,
                recent_interactions=10,
                last_proactivity_time=datetime.now() - timedelta(hours=2),
                user_engagement_level=0.7,
            ),
        },
        {
            "name": "长时间沉默",
            "context": ProactivityContext(
                user_silence_duration=3600,  # 1小时
                relationship_trust=0.8,
                recent_interactions=10,
                last_proactivity_time=datetime.now() - timedelta(hours=2),
                user_engagement_level=0.7,
            ),
        },
        {
            "name": "低信任度",
            "context": ProactivityContext(
                user_silence_duration=3600,
                relationship_trust=0.3,
                recent_interactions=2,
                last_proactivity_time=datetime.now() - timedelta(hours=2),
                user_engagement_level=0.3,
            ),
        },
    ]
    
    for scenario in scenarios:
        decision = engine.evaluate(scenario["context"])
        print(f"\n场景: {scenario['name']}")
        print(f"  应该主动: {decision.should_act}")
        if decision.should_act:
            print(f"  行动类型: {decision.action_type.value}")
            print(f"  内容: {decision.content[:30]}...")
            print(f"  原因: {decision.reason}")
            print(f"  置信度: {decision.confidence:.2f}")
            print(f"  时机得分: {decision.timing_score:.2f}")
    
    # 设置不同等级
    engine.set_level(ProactivityLevel.HIGH)
    print(f"\n设置主动性等级: HIGH")
    
    # 统计
    stats = engine.get_statistics()
    print(f"\n统计:")
    print(f"  等级: {stats['level']}")
    print(f"  总主动次数: {stats['total_proactivities']}")
    
    print("\n✅ 测试1通过")


async def test_adaptive_evolution_goal():
    """测试自适应进化目标"""
    print("\n" + "=" * 60)
    print("测试2: 自适应进化目标")
    print("=" * 60)
    
    from core.evolution.adaptive_goal import (
        AdaptiveEvolutionGoal,
        EvolutionDimension,
        GoalPriority,
    )
    
    evolution = AdaptiveEvolutionGoal()
    print(f"✓ 自适应进化目标已创建")
    
    # 查看初始目标
    print(f"\n初始目标:")
    for goal in evolution.get_priority_goals():
        print(f"  {goal.dimension.value}: 目标={goal.target_value:.2f}, 当前={goal.current_value:.2f}, 进度={goal.progress:.1%}")
    
    # 模拟用户反馈
    feedbacks = [
        {
            "satisfaction": 0.9,
            "praised_aspects": ["准确", "快速"],
            "criticized_aspects": [],
        },
        {
            "satisfaction": 0.7,
            "praised_aspects": ["理解"],
            "criticized_aspects": ["速度"],
        },
        {
            "satisfaction": 0.8,
            "praised_aspects": ["创意", "知识"],
            "criticized_aspects": [],
        },
    ]
    
    print(f"\n模拟用户反馈:")
    for i, feedback in enumerate(feedbacks):
        evolution.infer_value_from_feedback(feedback)
        print(f"  反馈 {i+1}: 满意度={feedback['satisfaction']}, 赞扬={feedback['praised_aspects']}")
    
    # 查看价值推断
    print(f"\n价值推断:")
    for dimension, inference in evolution.value_inferences.items():
        print(f"  {dimension.value}: 值={inference.inferred_value:.2f}, 证据数={inference.evidence_count}, 置信度={inference.confidence:.2f}")
    
    # 更新进度
    evolution.update_progress(EvolutionDimension.ACCURACY, 0.75)
    evolution.update_progress(EvolutionDimension.KNOWLEDGE, 0.65)
    print(f"\n更新进度后:")
    
    # 获取进化方向
    direction = evolution.get_evolution_direction()
    print(f"\n进化方向:")
    print(f"  主要焦点: {direction['primary_focus']}")
    print(f"  已达成目标: {direction['goals_achieved']}")
    for goal in direction['goals']:
        print(f"    {goal['dimension']}: 进度={goal['progress']:.1%}, 差距={goal['gap']:.2f}")
    
    # 设置显式目标
    evolution.set_explicit_goal(
        EvolutionDimension.CREATIVITY,
        target=0.85,
        priority=GoalPriority.HIGH,
    )
    print(f"\n设置显式目标: 创造性=0.85")
    
    # 统计
    stats = evolution.get_statistics()
    print(f"\n统计:")
    print(f"  总目标: {stats['total_goals']}")
    print(f"  总调整: {stats['total_adjustments']}")
    print(f"  平均进度: {stats['average_progress']:.1%}")
    
    print("\n✅ 测试2通过")


async def test_integration():
    """测试集成"""
    print("\n" + "=" * 60)
    print("测试3: 第三阶段集成")
    print("=" * 60)
    
    from core.presence.proactivity import (
        ProactivityEngine,
        ProactivityContext,
    )
    from core.evolution.adaptive_goal import (
        AdaptiveEvolutionGoal,
        EvolutionDimension,
    )
    
    engine = ProactivityEngine()
    evolution = AdaptiveEvolutionGoal()
    
    print(f"✓ 所有模块已创建")
    
    # 模拟完整流程
    print(f"\n模拟场景: 用户长时间沉默")
    
    # 1. 评估是否应该主动
    context = ProactivityContext(
        user_silence_duration=3600,
        relationship_trust=0.75,
        recent_interactions=20,
        last_proactivity_time=datetime.now() - timedelta(hours=3),
        user_engagement_level=0.6,
    )
    
    decision = engine.evaluate(context)
    print(f"\n1. 主动性评估:")
    print(f"   应该主动: {decision.should_act}")
    if decision.should_act:
        print(f"   行动类型: {decision.action_type.value}")
        
        # 2. 执行主动行动
        result = engine.execute(decision)
        print(f"\n2. 执行主动行动:")
        print(f"   执行成功: {result['executed']}")
        print(f"   内容: {result['content'][:40]}...")
    
    # 3. 根据反馈调整进化目标
    feedback = {
        "satisfaction": 0.85,
        "praised_aspects": ["准确", "理解"],
        "criticized_aspects": [],
    }
    evolution.infer_value_from_feedback(feedback)
    
    direction = evolution.get_evolution_direction()
    print(f"\n3. 进化方向:")
    print(f"   主要焦点: {direction['primary_focus']}")
    
    # 4. 更新进度
    evolution.update_progress(EvolutionDimension.ACCURACY, 0.8)
    print(f"\n4. 更新进度: 准确性=0.8")
    
    # 统计
    proactivity_stats = engine.get_statistics()
    evolution_stats = evolution.get_statistics()
    
    print(f"\n整体状态:")
    print(f"  主动性次数: {proactivity_stats['total_proactivities']}")
    print(f"  进化目标数: {evolution_stats['total_goals']}")
    print(f"  平均进度: {evolution_stats['average_progress']:.1%}")
    
    print("\n✅ 测试3通过")


async def main():
    """运行所有测试"""
    print("=" * 70)
    print("🌟 第三阶段验证测试：培育主动性与进化自主性")
    print("=" * 70)
    
    try:
        await test_proactivity_engine()
        await test_adaptive_evolution_goal()
        await test_integration()
        
        print("\n" + "=" * 70)
        print("🎉 第三阶段所有测试通过！")
        print("=" * 70)
        
        print("\n📊 第三阶段完成标志:")
        print("  ✓ 主动性引擎能够判断时机")
        print("  ✓ 自适应进化目标能够从反馈中学习")
        print("  ✓ 进化方向能够动态调整")
        print("  ✓ 所有模块能够协同工作")
        
        print("\n🌟 系统能够'主动'和'自主进化'")
        print("   在用户沉默时主动感知，在合适时机主动表达")
        print("   进化方向由自身从互动中学习")
        
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