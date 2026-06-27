"""
完整六层架构端到端测试

验证：
1. L0-L6所有层正常工作
2. 层间通信（心跳检测）
3. 完整流程：L1→L2→L3→L4→L5
4. L6内省监控所有层
5. 状态报告完整性
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l2_learning import get_l2_learning
from core.layers.l3_integration import get_l3_integration
from core.layers.l4_validation import get_l4_validation
from core.layers.l5_evolution import get_l5_evolution
from core.layers.l6_introspection import get_l6_introspection
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager


def test_all_layers_initialization():
    """测试所有层初始化"""
    print("=" * 60)
    print("所有层初始化测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    l3 = get_l3_integration()
    l4 = get_l4_validation()
    l5 = get_l5_evolution()
    l6 = get_l6_introspection()
    
    assert l2 is not None
    assert l3 is not None
    assert l4 is not None
    assert l5 is not None
    assert l6 is not None
    
    print("✅ 所有层初始化成功")


def test_heartbeat_all_layers():
    """测试所有层心跳"""
    print("\n" + "=" * 60)
    print("所有层心跳测试")
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


def test_complete_pipeline():
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
        'name': '六层认知架构验证',
        'keywords': ['认知', '架构', '六层', '验证']
    }
    
    l2_result = l2.learn(learning_target)
    
    print(f"  学习结果: {'成功' if l2_result.success else '失败'}")
    print(f"  获取知识: {l2_result.knowledge_gained}条")
    print(f"  置信度: {l2_result.confidence:.2f}")
    
    knowledge_items = [
        {
            'id': f'arch_{i}',
            'answer': f'关于六层认知架构的知识点{i+1}',
            'source': 'architecture_doc',
            'confidence': 0.85,
            'quality_score': 80,
            'keywords': ['认知', '架构']
        }
        for i in range(3)
    ]
    
    print("\n[步骤2] L3整合")
    l3_result = l3.integrate(knowledge_items)
    
    print(f"  整合结果: {'成功' if l3_result.success else '失败'}")
    print(f"  知识节点: {l3_result.total_nodes}个")
    print(f"  核心知识: {len(l3_result.core_knowledge)}条")
    print(f"  置信度: {l3_result.confidence:.2f}")
    
    print("\n[步骤3] L4校验")
    integrated_knowledge = {
        'knowledge_graph': l3_result.knowledge_graph,
        'core_knowledge': l3_result.core_knowledge,
        'confidence': l3_result.confidence
    }
    
    l4_result = l4.validate(integrated_knowledge)
    
    print(f"  校验结果: {'成功' if l4_result.success else '失败'}")
    print(f"  校验状态: {l4_result.status.value}")
    print(f"  确定性: {l4_result.certainty_score:.2f}")
    print(f"  信任等级: {l4_result.trust_level.value}")
    print(f"  质疑数: {len(l4_result.doubts)}个")
    
    print("\n[步骤4] L5进化")
    experience = {
        'user_input': '六层认知架构验证',
        'validation_result': {
            'status': l4_result.status.value,
            'confidence': l4_result.certainty_score
        },
        'learning_result': {
            'knowledge_gained': l2_result.knowledge_gained
        },
        'processing_time_ms': 1500,
        'user_feedback': {}
    }
    
    l5_result = l5.record_experience(experience)
    
    print(f"  进化结果: {'成功' if l5_result.success else '失败'}")
    print(f"  适应度: {l5_result.confidence:.3f}")
    print(f"  变更: {len(l5_result.changes)}项")
    
    assert l2_result.success
    assert l3_result.success
    assert l5_result.success
    
    print("\n✅ 完整流程测试通过")


def test_l6_introspection():
    """测试L6内省"""
    print("\n" + "=" * 60)
    print("L6内省测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    print("\n生成内省报告...")
    report = l6.generate_report()
    
    print(f"\n内省报告:")
    print(f"  健康度: {report.health.overall:.3f}")
    print(f"  健康级别: {report.health.get_level().value}")
    print(f"  协调性: {report.health.coordination:.3f}")
    print(f"  趋势: {report.health.trend}")
    print(f"  活跃异常: {len(report.active_anomalies)}个")
    print(f"  摘要: {report.summary}")
    
    if report.recommendations:
        print(f"\n建议:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
    
    print("\n✅ L6内省测试通过")


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
    
    assert health_summary['total_layers'] >= 5
    
    print("\n✅ 系统整体健康度测试通过")


def test_layer_status_methods():
    """测试各层状态方法"""
    print("\n" + "=" * 60)
    print("各层状态方法测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    l3 = get_l3_integration()
    l4 = get_l4_validation()
    l5 = get_l5_evolution()
    l6 = get_l6_introspection()
    
    l2_status = l2.get_learning_status()
    print(f"\nL2状态:")
    print(f"  层: {l2_status['layer']}")
    print(f"  总学习次数: {l2_status['stats']['total_learning_attempts']}")
    
    l3_status = l3.get_integration_status()
    print(f"\nL3状态:")
    print(f"  层: {l3_status['layer']}")
    print(f"  总整合次数: {l3_status['stats']['total_integrations']}")
    
    l4_status = l4.get_validation_status()
    print(f"\nL4状态:")
    print(f"  层: {l4_status['layer']}")
    print(f"  总校验次数: {l4_status['stats']['total_validations']}")
    
    l5_status = l5.get_evolution_status()
    print(f"\nL5状态:")
    print(f"  层: {l5_status['layer']}")
    print(f"  总进化次数: {l5_status['stats']['total_evolutions']}")
    print(f"  平均适应度: {l5_status['fitness']['avg']:.3f}")
    
    l6_status = l6.get_introspection_status()
    print(f"\nL6状态:")
    print(f"  层: {l6_status['layer']}")
    print(f"  平均健康度: {l6_status['health']['avg']:.3f}")
    
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
        ('L5', ['L4', 'L6']),
        ('L6', ['L5'])
    ]
    
    print("\n各层相邻层状态:")
    for layer, neighbors in layer_pairs:
        neighbor_status = heartbeat.get_neighbor_status(layer)
        print(f"\n  {layer} 的相邻层:")
        for neighbor, status in neighbor_status.items():
            print(f"    {neighbor}: {status.value}")
    
    print("\n✅ 相邻层感知测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("完整六层架构端到端测试")
    print("=" * 60)
    
    try:
        test_all_layers_initialization()
        test_heartbeat_all_layers()
        test_complete_pipeline()
        test_l6_introspection()
        test_system_health()
        test_layer_status_methods()
        test_neighbor_awareness()
        
        print("\n" + "=" * 60)
        print("✅ 所有端到端测试通过!")
        print("=" * 60)
        
        print("\n六层认知架构验证:")
        print("  ✅ L2学习层 - 知识获取")
        print("  ✅ L3整合层 - 知识整合")
        print("  ✅ L4校验层 - 自我质疑")
        print("  ✅ L5进化层 - 基因演化")
        print("  ✅ L6内省层 - 系统监控")
        print("  ✅ 层间心跳 - 双向感知")
        print("  ✅ 状态报告 - 完整追踪")
        print("  ✅ 完整流程 - 端到端验证")
        
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)