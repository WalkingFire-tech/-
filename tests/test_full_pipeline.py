"""
L2-L3-L4-L5完整流程测试

验证：
1. L2学习 → L3整合 → L4校验 → L5进化
2. 层间通信（心跳检测）
3. 回退机制（L4→L2）
4. 状态报告完整性
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l2_learning import get_l2_learning
from core.layers.l3_integration import get_l3_integration
from core.layers.l4_validation import get_l4_validation
from core.layers.l5_evolution import get_l5_evolution
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager


def test_layer_initialization():
    """测试所有层初始化"""
    print("=" * 60)
    print("所有层初始化测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    l3 = get_l3_integration()
    l4 = get_l4_validation()
    l5 = get_l5_evolution()
    
    assert l2 is not None
    assert l3 is not None
    assert l4 is not None
    assert l5 is not None
    
    print("✅ 所有层初始化成功")


def test_heartbeat_between_layers():
    """测试层间心跳"""
    print("\n" + "=" * 60)
    print("层间心跳测试")
    print("=" * 60)
    
    heartbeat = get_heartbeat_manager()
    
    layers = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6']
    
    print("\n各层存活状态:")
    for layer in layers:
        is_alive = heartbeat.is_layer_alive(layer)
        status = heartbeat.get_layer_status(layer)
        print(f"  {layer}: {'✅ 存活' if is_alive else '❌ 死亡'} ({status.value})")
    
    for layer in layers:
        assert heartbeat.is_layer_alive(layer), f"{layer} 应该存活"
    
    print("\n✅ 所有层心跳正常")


def test_full_pipeline():
    """测试完整流程"""
    print("\n" + "=" * 60)
    print("完整流程测试: L2→L3→L4→L5")
    print("=" * 60)
    
    l2 = get_l2_learning()
    l3 = get_l3_integration()
    l4 = get_l4_validation()
    l5 = get_l5_evolution()
    
    print("\n[步骤1] L2学习")
    learning_target = {
        'name': 'Python异步编程最佳实践',
        'keywords': ['python', 'async', 'asyncio', 'concurrency', 'best-practices']
    }
    
    l2_result = l2.learn(learning_target)
    
    print(f"  学习结果: {'成功' if l2_result.success else '失败'}")
    print(f"  获取知识: {l2_result.knowledge_gained}条")
    print(f"  置信度: {l2_result.confidence:.2f}")
    
    knowledge_items = [
        {
            'id': f'learned_{i}',
            'answer': f'关于{learning_target["name"]}的知识点{i+1}',
            'source': 'external_search',
            'confidence': 0.8,
            'quality_score': 75,
            'keywords': learning_target['keywords']
        }
        for i in range(3)
    ]
    
    print("\n[步骤2] L3整合")
    l3_result = l3.integrate(knowledge_items)
    
    print(f"  整合结果: {'成功' if l3_result.success else '失败'}")
    print(f"  知识节点: {l3_result.total_nodes}个")
    print(f"  核心知识: {len(l3_result.core_knowledge)}条")
    print(f"  冲突解决: {l3_result.resolved_conflicts}个")
    print(f"  置信度: {l3_result.confidence:.2f}")
    
    print("\n[步骤3] L4校验")
    integrated_knowledge = {
        'knowledge_graph': l3_result.knowledge_graph,
        'core_knowledge': l3_result.core_knowledge
    }
    
    l4_result = l4.validate(integrated_knowledge)
    
    print(f"  校验结果: {'成功' if l4_result.success else '失败'}")
    print(f"  校验等级: {l4_result.validation_level.value}")
    print(f"  确定性: {l4_result.certainty_score:.2f}")
    print(f"  一致性: {l4_result.consistency_score:.2f}")
    print(f"  信任等级: {l4_result.trust_chain.overall_trust.value if l4_result.trust_chain else 'N/A'}")
    print(f"  触发回退: {'是' if l4_result.should_fallback else '否'}")
    
    print("\n[步骤4] L5进化")
    validated_knowledge = {
        'knowledge_graph': l3_result.knowledge_graph,
        'validation_level': l4_result.validation_level.value
    }
    
    l5_result = l5.evolve(validated_knowledge)
    
    print(f"  进化结果: {'成功' if l5_result.success else '失败'}")
    print(f"  进化方向: {l5_result.direction.value}")
    print(f"  基因演化: {l5_result.genes_evolved}个")
    print(f"  新能力: {len(l5_result.new_capabilities)}个")
    print(f"  适应度提升: {l5_result.fitness_improvement:+.2f}")
    
    assert l2_result.success
    assert l3_result.success
    assert l4_result.success
    assert l5_result.success
    
    print("\n✅ 完整流程测试通过")


def test_fallback_mechanism():
    """测试回退机制"""
    print("\n" + "=" * 60)
    print("回退机制测试: L4→L2")
    print("=" * 60)
    
    l3 = get_l3_integration()
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    print("\n[场景] 低质量知识触发回退")
    
    poor_knowledge = {
        'poor': KnowledgeNode(
            id='poor',
            content='Very low quality and uncertain information.',
            source='unknown',
            confidence=0.2,
            quality_score=20,
            timestamp=datetime.now().isoformat(),
            keywords=[]
        )
    }
    
    l3_result = l3.integrate([{
        'id': 'poor',
        'answer': 'Very low quality and uncertain information.',
        'source': 'unknown',
        'confidence': 0.2,
        'quality_score': 20
    }])
    
    integrated = {
        'knowledge_graph': l3_result.knowledge_graph,
        'core_knowledge': l3_result.core_knowledge
    }
    
    l4_result = l4.validate(integrated)
    
    print(f"  校验等级: {l4_result.validation_level.value}")
    print(f"  触发回退: {'是' if l4_result.should_fallback else '否'}")
    print(f"  回退原因: {l4_result.fallback_reason}")
    
    if l4_result.should_fallback:
        print("\n[回退动作] 触发L4→L2回退")
        fallback_event = l4.trigger_fallback_to_l2(l4_result.fallback_reason)
        print(f"  回退状态: {fallback_event['status']}")
        print(f"  回退原因: {fallback_event['reason']}")
    
    assert l4_result.should_fallback
    
    print("\n✅ 回退机制测试通过")


def test_state_reporting():
    """测试状态报告"""
    print("\n" + "=" * 60)
    print("状态报告测试")
    print("=" * 60)
    
    collector = get_state_collector()
    
    print("\n收集所有层状态...")
    all_states = collector.get_all_latest()
    
    print(f"\n状态收集结果:")
    print(f"  总层数: {len(all_states)}")
    
    for layer_name, state in all_states.items():
        print(f"\n  {layer_name}:")
        print(f"    状态: {state.status.value}")
        print(f"    健康: {state.health.value}")
        print(f"    置信度: {state.confidence_score:.2f}")
        print(f"    最后操作: {state.last_operation}")
    
    assert len(all_states) >= 4
    
    print("\n✅ 状态报告测试通过")


def test_layer_status_methods():
    """测试各层状态方法"""
    print("\n" + "=" * 60)
    print("各层状态方法测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    l3 = get_l3_integration()
    l4 = get_l4_validation()
    l5 = get_l5_evolution()
    
    l2_status = l2.get_learning_status()
    print(f"\nL2状态:")
    print(f"  层: {l2_status['layer']}")
    print(f"  总学习次数: {l2_status['stats']['total_learning_attempts']}")
    print(f"  相邻层: {l2_status['neighbor_status']}")
    
    l3_status = l3.get_integration_status()
    print(f"\nL3状态:")
    print(f"  层: {l3_status['layer']}")
    print(f"  总整合次数: {l3_status['stats']['total_integrations']}")
    print(f"  相邻层: {l3_status['neighbor_status']}")
    
    l4_status = l4.get_validation_status()
    print(f"\nL4状态:")
    print(f"  层: {l4_status['layer']}")
    print(f"  总校验次数: {l4_status['stats']['total_validations']}")
    print(f"  回退率: {l4_status['fallback_rate']:.2f}")
    print(f"  相邻层: {l4_status['neighbor_status']}")
    
    l5_status = l5.get_evolution_status()
    print(f"\nL5状态:")
    print(f"  层: {l5_status['layer']}")
    print(f"  总进化次数: {l5_status['stats']['total_evolutions']}")
    print(f"  平均适应度: {l5_status['stats']['avg_fitness']:.2f}")
    print(f"  相邻层: {l5_status['neighbor_status']}")
    
    print("\n✅ 各层状态方法测试通过")


def test_neighbor_awareness():
    """测试相邻层感知"""
    print("\n" + "=" * 60)
    print("相邻层感知测试")
    print("=" * 60)
    
    heartbeat = get_heartbeat_manager()
    
    layer_pairs = [
        ('L2', ['L1', 'L3']),
        ('L3', ['L2', 'L4']),
        ('L4', ['L3', 'L5']),
        ('L5', ['L4', 'L6'])
    ]
    
    print("\n各层相邻层状态:")
    for layer, neighbors in layer_pairs:
        neighbor_status = heartbeat.get_neighbor_status(layer)
        print(f"\n  {layer} 的相邻层:")
        for neighbor, status in neighbor_status.items():
            print(f"    {neighbor}: {status.value}")
    
    print("\n✅ 相邻层感知测试通过")


def test_system_health():
    """测试系统整体健康度"""
    print("\n" + "=" * 60)
    print("系统整体健康度测试")
    print("=" * 60)
    
    collector = get_state_collector()
    
    health_summary = collector.get_health_summary()
    
    print(f"\n系统健康度:")
    print(f"  总层数: {health_summary['total_layers']}")
    print(f"  健康层数: {health_summary['healthy_layers']}")
    print(f"  警告层数: {health_summary['warning_layers']}")
    print(f"  严重层数: {health_summary['critical_layers']}")
    print(f"  整体健康度: {health_summary['overall_health']}")
    
    assert health_summary['total_layers'] >= 4
    
    print("\n✅ 系统整体健康度测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("L2-L3-L4-L5完整流程测试")
    print("=" * 60)
    
    try:
        test_layer_initialization()
        test_heartbeat_between_layers()
        test_full_pipeline()
        test_fallback_mechanism()
        test_state_reporting()
        test_layer_status_methods()
        test_neighbor_awareness()
        test_system_health()
        
        print("\n" + "=" * 60)
        print("✅ 所有完整流程测试通过!")
        print("=" * 60)
        
        print("\n系统架构验证:")
        print("  ✅ L2学习层 - 知识获取")
        print("  ✅ L3整合层 - 知识整合")
        print("  ✅ L4校验层 - 输出校验")
        print("  ✅ L5进化层 - 基因演化")
        print("  ✅ 层间心跳 - 双向感知")
        print("  ✅ 回退机制 - L4→L2")
        print("  ✅ 状态报告 - 完整追踪")
        
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)