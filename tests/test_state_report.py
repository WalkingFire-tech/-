"""
测试状态报告接口和状态收集器
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_report import (
    LayerStateReport,
    LayerStatus,
    LayerName,
    StateReportable
)
from core.state_collector import (
    StateCollector,
    HealthLevel,
    SystemHealthSummary
)


def test_layer_state_report():
    """测试层状态报告"""
    report = LayerStateReport(
        layer_name="L1_Perception",
        status=LayerStatus.RUNNING,
        timestamp=datetime.now().isoformat(),
        metrics={"confidence": 0.85, "processing_time": 1.2},
        issues=[],
        last_successful_operation="intent_recognition",
        confidence_score=0.85
    )
    
    assert report.layer_name == "L1_Perception"
    assert report.status == LayerStatus.RUNNING
    assert report.is_healthy() is True
    assert report.needs_attention() is False
    
    report_dict = report.to_dict()
    assert "layer" in report_dict
    assert "status" in report_dict
    assert "metrics" in report_dict
    
    print("✅ 层状态报告测试通过")


def test_state_reportable():
    """测试状态报告接口"""
    class MockLayer(StateReportable):
        def __init__(self):
            super().__init__("L2_Learning")
    
    layer = MockLayer()
    
    layer.set_status(LayerStatus.BUSY)
    layer.set_metric("knowledge_count", 150)
    layer.set_metric("learning_rate", 0.08)
    layer.set_confidence(0.75)
    
    report = layer.report_state()
    
    assert report.layer_name == "L2_Learning"
    assert report.status == LayerStatus.BUSY
    assert report.metrics["knowledge_count"] == 150
    assert report.confidence_score == 0.75
    
    print("✅ 状态报告接口测试通过")


def test_state_reportable_feedback():
    """测试状态报告接口的反馈机制"""
    class MockLayer(StateReportable):
        def __init__(self):
            super().__init__("L3_Integration")
    
    layer = MockLayer()
    layer.set_confidence(0.8)
    
    layer.receive_feedback({
        'confidence_adjustment': -0.1,
        'metric_updates': {'conflict_count': 3}
    })
    
    report = layer.report_state()
    
    assert abs(report.confidence_score - 0.7) < 0.01
    assert report.metrics['conflict_count'] == 3
    
    print("✅ 反馈机制测试通过")


def test_state_reportable_success_error():
    """测试成功和错误标记"""
    class MockLayer(StateReportable):
        def __init__(self):
            super().__init__("L4_Verification")
    
    layer = MockLayer()
    layer.set_confidence(0.5)
    
    layer.mark_success("output_verification")
    report = layer.report_state()
    assert report.status == LayerStatus.RUNNING
    assert report.confidence_score > 0.5
    
    layer.mark_error("校验失败：置信度过低")
    report = layer.report_state()
    assert report.status == LayerStatus.ERROR
    assert len(report.issues) > 0
    
    print("✅ 成功和错误标记测试通过")


def test_state_collector():
    """测试状态收集器"""
    db_path = "data/test_state_collector.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    collector = StateCollector(db_path=db_path)
    
    report = LayerStateReport(
        layer_name="L0_Existence",
        status=LayerStatus.RUNNING,
        timestamp=datetime.now().isoformat(),
        metrics={"philosophy_compliance": 1.0},
        issues=[],
        confidence_score=1.0
    )
    
    collector.collect(report)
    
    latest = collector.get_latest("L0_Existence")
    assert latest is not None
    assert latest.layer_name == "L0_Existence"
    
    print("✅ 状态收集器测试通过")


def test_state_collector_multiple_layers():
    """测试多层状态收集"""
    db_path = "data/test_state_collector_multi.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    collector = StateCollector(db_path=db_path)
    
    layers = ["L0_Existence", "L1_Perception", "L2_Learning", "L3_Integration"]
    for layer_name in layers:
        report = LayerStateReport(
            layer_name=layer_name,
            status=LayerStatus.RUNNING,
            timestamp=datetime.now().isoformat(),
            metrics={},
            issues=[],
            confidence_score=0.85
        )
        collector.collect(report)
    
    all_latest = collector.get_all_latest()
    assert len(all_latest) == 4
    
    print("✅ 多层状态收集测试通过")


def test_health_summary():
    """测试健康度摘要"""
    db_path = "data/test_health_summary.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    collector = StateCollector(db_path=db_path)
    
    report_healthy = LayerStateReport(
        layer_name="L0_Existence",
        status=LayerStatus.RUNNING,
        timestamp=datetime.now().isoformat(),
        metrics={},
        issues=[],
        confidence_score=0.95
    )
    collector.collect(report_healthy)
    
    report_degraded = LayerStateReport(
        layer_name="L2_Learning",
        status=LayerStatus.DEGRADED,
        timestamp=datetime.now().isoformat(),
        metrics={},
        issues=["学习效率下降"],
        confidence_score=0.7
    )
    collector.collect(report_degraded)
    
    summary = collector.get_health_summary()
    
    assert summary.level in [HealthLevel.HEALTHY, HealthLevel.WARNING, HealthLevel.DANGER]
    assert summary.overall_score > 0
    assert len(summary.layer_summaries) == 2
    
    print("✅ 健康度摘要测试通过")


def test_listener_notification():
    """测试监听者通知"""
    db_path = "data/test_listener.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    collector = StateCollector(db_path=db_path)
    
    notified_reports = []
    
    def listener(report):
        notified_reports.append(report)
    
    collector.register_listener(listener)
    
    report = LayerStateReport(
        layer_name="L5_Evolution",
        status=LayerStatus.RUNNING,
        timestamp=datetime.now().isoformat(),
        metrics={},
        issues=[],
        confidence_score=0.9
    )
    
    collector.collect(report)
    
    assert len(notified_reports) == 1
    assert notified_reports[0].layer_name == "L5_Evolution"
    
    print("✅ 监听者通知测试通过")


def test_complete_flow():
    """完整流程测试"""
    print("\n测试完整流程...")
    
    db_path = "data/test_state_complete.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    collector = StateCollector(db_path=db_path)
    
    class MockL0(StateReportable):
        def __init__(self):
            super().__init__("L0_Existence")
    
    class MockL1(StateReportable):
        def __init__(self):
            super().__init__("L1_Perception")
    
    l0 = MockL0()
    l1 = MockL1()
    
    l0.set_status(LayerStatus.RUNNING)
    l0.set_metric("philosophy_compliance", 1.0)
    l0.set_confidence(1.0)
    
    l1.set_status(LayerStatus.BUSY)
    l1.set_metric("intent_confidence", 0.85)
    l1.set_confidence(0.85)
    l1.set_processing("用户输入：推荐芯片")
    
    collector.collect(l0.report_state())
    collector.collect(l1.report_state())
    
    summary = collector.get_health_summary()
    
    print(f"   系统健康度: {summary.level.value}")
    print(f"   整体分数: {summary.overall_score:.2f}")
    print(f"   监控层数: {len(summary.layer_summaries)}")
    
    l1.receive_feedback({
        'confidence_adjustment': -0.1,
        'status_suggestion': LayerStatus.DEGRADED
    })
    l1.add_issue("意图理解置信度下降")
    
    collector.collect(l1.report_state())
    
    summary = collector.get_health_summary()
    
    print(f"   反馈后健康度: {summary.level.value}")
    print(f"   反馈后分数: {summary.overall_score:.2f}")
    
    assert summary.overall_score < 0.9
    
    print("✅ 完整流程测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试状态报告接口和状态收集器")
    print("=" * 60)
    
    test_layer_state_report()
    test_state_reportable()
    test_state_reportable_feedback()
    test_state_reportable_success_error()
    test_state_collector()
    test_state_collector_multiple_layers()
    test_health_summary()
    test_listener_notification()
    test_complete_flow()
    
    print("=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)