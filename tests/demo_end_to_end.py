"""
端到端演示 - 完整的学习进化流程

展示六层架构 + 七大机制 + 认知循环的完整协作
"""
import asyncio
from datetime import datetime
from core.cognitive_loop import CognitiveLoop


async def demo_learning_evolution():
    """演示完整的学习进化流程"""
    
    print("=" * 70)
    print("🧠 六层认知进化架构 - 端到端演示")
    print("=" * 70)
    
    loop = CognitiveLoop()
    
    print("\n📊 初始状态:")
    initial_status = loop.get_status()
    print(f"  - 认知阶段: {initial_status['rhythm']['current_phase']}")
    print(f"  - 能量水平: {initial_status['rhythm']['energy_level']:.2f}")
    print(f"  - 知识节点: {initial_status['knowledge']['total_nodes']}")
    
    print("\n" + "=" * 70)
    print("第一阶段：探索学习 (10个循环)")
    print("=" * 70)
    
    for i in range(10):
        signal = {
            "success": True,
            "content": f"探索知识_{i}",
            "type": "exploration",
        }
        result = await loop.run_cycle(signal)
        
        if i % 3 == 0:
            print(f"\n循环 {i+1}:")
            print(f"  - 状态: {result.state.value}")
            print(f"  - 置信度: {result.confidence:.2f}")
            print(f"  - 行动: {result.actions_taken[:2]}")
    
    status = loop.get_status()
    print(f"\n探索阶段完成:")
    print(f"  - 知识节点: {status['knowledge']['total_nodes']}")
    print(f"  - 知识连接: {status['knowledge']['total_connections']}")
    print(f"  - 当前阶段: {status['rhythm']['current_phase']}")
    
    print("\n" + "=" * 70)
    print("第二阶段：错误学习 (5个错误)")
    print("=" * 70)
    
    errors = [
        ValueError("数据格式错误"),
        TypeError("类型不匹配"),
        RuntimeError("运行时错误"),
        KeyError("键不存在"),
        AttributeError("属性缺失"),
    ]
    
    for i, error in enumerate(errors):
        result = await loop.run_cycle(error)
        print(f"\n错误 {i+1}: {type(error).__name__}")
        print(f"  - 已转化为学习信号")
        print(f"  - 洞察: {result.insights[-1] if result.insights else '无'}")
    
    lessons = loop.error_alchemy.get_lessons_learned()
    print(f"\n错误学习完成:")
    print(f"  - 总错误数: {lessons['total_errors']}")
    print(f"  - 避免模式: {len(loop.error_alchemy.get_avoid_patterns())}")
    print(f"  - 错误分类: {lessons['error_categories']}")
    
    print("\n" + "=" * 70)
    print("第三阶段：知识整合 (10个循环)")
    print("=" * 70)
    
    for i in range(10):
        signal = {
            "success": True,
            "content": {
                "concept": f"概念_{i}",
                "relation": f"关联_{i % 3}",
                "category": f"类别_{i % 2}",
            },
            "type": "integration",
        }
        result = await loop.run_cycle(signal)
        
        if i % 3 == 0:
            print(f"\n循环 {i+1}:")
            print(f"  - 知识节点: {loop.knowledge_weaver.get_statistics()['total_nodes']}")
            print(f"  - 知识群落: {loop.knowledge_weaver.get_statistics()['total_clusters']}")
    
    status = loop.get_status()
    print(f"\n知识整合完成:")
    print(f"  - 总节点: {status['knowledge']['total_nodes']}")
    print(f"  - 总连接: {status['knowledge']['total_connections']}")
    print(f"  - 知识群落: {status['knowledge']['total_clusters']}")
    
    print("\n" + "=" * 70)
    print("第四阶段：策略优化")
    print("=" * 70)
    
    for i in range(5):
        accuracy = 0.6 + i * 0.08
        from core.learning import EvaluationMetric
        loop.meta_learner.evaluate_strategy(
            "spaced_repetition",
            EvaluationMetric.ACCURACY,
            accuracy,
        )
        print(f"  评估 {i+1}: 准确率={accuracy:.2f}")
    
    recommendations = loop.meta_learner.recommend_strategy({
        "task_type": "记忆",
        "recent_accuracy": 0.8,
    })
    
    print(f"\n策略推荐:")
    for i, rec in enumerate(recommendations[:3]):
        print(f"  {i+1}. {rec.strategy.name}")
        print(f"     - 置信度: {rec.confidence:.2f}")
        print(f"     - 原因: {rec.reason}")
    
    print("\n" + "=" * 70)
    print("第五阶段：持续进化 (20个循环)")
    print("=" * 70)
    
    def signal_generator():
        import random
        return {
            "success": random.random() > 0.2,
            "content": f"进化信号_{random.randint(1, 100)}",
            "iteration": loop.cycle_count,
        }
    
    results = await loop.run_continuous(
        signal_generator=signal_generator,
        max_cycles=20,
    )
    
    print(f"\n持续进化完成:")
    print(f"  - 总循环数: {len(results)}")
    print(f"  - 成功循环: {sum(1 for r in results if r.error is None)}")
    print(f"  - 平均置信度: {sum(r.confidence for r in results) / len(results):.2f}")
    
    print("\n" + "=" * 70)
    print("📈 最终状态报告")
    print("=" * 70)
    
    final_status = loop.get_status()
    
    print("\n🔄 认知循环:")
    print(f"  - 总循环数: {final_status['metrics']['total_cycles']}")
    print(f"  - 成功率: {final_status['metrics']['success_rate']:.2%}")
    print(f"  - 平均置信度: {final_status['metrics']['average_confidence']:.2f}")
    print(f"  - 错误率: {final_status['metrics']['error_rate']:.2%}")
    
    print("\n🧠 认知节奏:")
    print(f"  - 当前阶段: {final_status['rhythm']['current_phase']}")
    print(f"  - 当前状态: {final_status['rhythm']['current_state']}")
    print(f"  - 能量水平: {final_status['rhythm']['energy_level']:.2f}")
    print(f"  - 专注度: {final_status['rhythm']['focus_score']:.2f}")
    
    print("\n📚 知识网络:")
    print(f"  - 总节点: {final_status['knowledge']['total_nodes']}")
    print(f"  - 总连接: {final_status['knowledge']['total_connections']}")
    print(f"  - 知识群落: {final_status['knowledge']['total_clusters']}")
    print(f"  - 平均连接数: {final_status['knowledge']['average_connections']:.2f}")
    
    print("\n🎯 学习系统:")
    print(f"  - 信号数: {final_status['learning']['signals']}")
    print(f"  - 模式数: {final_status['learning']['patterns']}")
    print(f"  - 策略数: {final_status['learning']['strategies']}")
    
    print("\n💡 错误炼金:")
    lessons = loop.error_alchemy.get_lessons_learned()
    print(f"  - 总错误: {lessons['total_errors']}")
    print(f"  - 已解决: {lessons['resolved_errors']}")
    print(f"  - 避免模式: {lessons['avoid_patterns']}")
    
    print("\n" + "=" * 70)
    print("✅ 端到端演示完成")
    print("=" * 70)
    
    print("\n🎓 核心能力展示:")
    print("  ✓ 完整的感知-理解-行动-反思循环")
    print("  ✓ 错误自动转化为学习信号")
    print("  ✓ 知识网络自动编织")
    print("  ✓ 认知节奏动态调整")
    print("  ✓ 元学习策略优化")
    print("  ✓ 六层架构协同工作")
    print("  ✓ 七大机制深度集成")
    
    return final_status


if __name__ == "__main__":
    asyncio.run(demo_learning_evolution())