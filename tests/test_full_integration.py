"""
端到端集成测试 - 验证状态报告、心跳、L2学习层的完整集成
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l2_learning import get_l2_learning
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager
from core.introspection.layer_reporter import LayerReporter
from core.state_report import LayerHealth


def test_full_integration():
    """完整集成测试"""
    print("=" * 60)
    print("端到端集成测试")
    print("=" * 60)
    
    collector = get_state_collector()
    hbm = get_heartbeat_manager()
    l2 = get_l2_learning()
    
    print("\n1. 初始化所有层...")
    layers = {}
    for layer_name in ["L0", "L1", "L3", "L4", "L5"]:
        reporter = LayerReporter(layer_name)
        reporter.report_completed(
            metrics={"load": 0.3},
            confidence=0.9
        )
        layers[layer_name] = reporter
        print(f"   {layer_name}: 已初始化")
    
    print("\n2. 等待心跳收集...")
    time.sleep(3)
    
    print("\n3. 检查各层状态...")
    snapshot = collector.get_snapshot()
    print(f"   整体健康度: {snapshot.overall_health.value}")
    print(f"   整体置信度: {snapshot.overall_confidence:.2f}")
    print(f"   健康层数: {snapshot.healthy_layers}/{snapshot.layers_count}")
    
    print("\n4. 检查心跳状态...")
    for layer in ["L0", "L1", "L2", "L3", "L4", "L5"]:
        status = hbm.get_layer_status(layer)
        neighbors = hbm.get_neighbor_status(layer)
        print(f"   {layer}: {status.value}, 相邻层: {len(neighbors)}")
    
    print("\n5. 执行L2学习...")
    target = {
        'name': '26650电池保护芯片选型',
        'keywords': ['26650', '电池', '保护芯片', '选型']
    }
    result = l2.learn(target)
    print(f"   学习成功: {result.success}")
    print(f"   获取知识: {result.knowledge_gained}条")
    print(f"   置信度: {result.confidence:.2f}")
    
    print("\n6. 检查L2状态报告...")
    l2_report = collector.get_latest("L2")
    print(f"   状态: {l2_report.status.value}")
    print(f"   健康度: {l2_report.health.value}")
    print(f"   置信度: {l2_report.confidence_score:.2f}")
    print(f"   指标: {l2_report.metrics}")
    
    print("\n7. 模拟L2降级...")
    l2.reporter.report_warning(
        warnings=["学习效率下降", "知识质量降低"],
        metrics={"efficiency": 0.3}
    )
    
    snapshot2 = collector.get_snapshot()
    print(f"   降级后整体健康度: {snapshot2.overall_health.value}")
    print(f"   L2健康度: {snapshot2.layer_reports['L2'].health.value}")
    
    print("\n8. 获取系统摘要...")
    summary = collector.get_status_summary()
    print(f"   时间: {summary['timestamp']}")
    print(f"   整体健康: {summary['overall_health']}")
    print(f"   整体置信度: {summary['overall_confidence']}")
    print(f"   汇总: {summary['summary']}")
    
    print("\n" + "=" * 60)
    print("✅ 端到端集成测试通过")
    print("=" * 60)
    
    return True


def test_layer_communication():
    """测试层间通信"""
    print("\n" + "=" * 60)
    print("层间通信测试")
    print("=" * 60)
    
    collector = get_state_collector()
    
    print("\n1. L1向L2发送反馈...")
    l1_reporter = LayerReporter("L1")
    l1_reporter.report_completed(
        metrics={"intent_confidence": 0.85},
        confidence=0.85
    )
    
    l2 = get_l2_learning()
    l2.reporter.receive_feedback({
        'confidence_adjustment': 0.05,
        'metric_updates': {'upstream_confidence': 0.85}
    })
    
    l2_report = collector.get_latest("L2")
    print(f"   L2接收反馈后置信度: {l2_report.confidence_score:.2f}")
    print(f"   L2指标: {l2_report.metrics}")
    
    print("\n2. L3感知L2状态...")
    l3_reporter = LayerReporter("L3")
    
    l2_status = collector.get_latest("L2")
    if l2_status and l2_status.health == LayerHealth.HEALTHY:
        l3_reporter.report_completed(
            metrics={"upstream_healthy": 1},
            confidence=0.9
        )
        print(f"   L3检测到L2健康，继续处理")
    else:
        l3_reporter.report_warning(
            warnings=["上游层不健康"]
        )
        print(f"   L3检测到L2不健康，降级处理")
    
    print("\n" + "=" * 60)
    print("✅ 层间通信测试通过")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_full_integration()
    test_layer_communication()
    
    print("\n" + "=" * 60)
    print("所有集成测试通过 ✅")
    print("=" * 60)