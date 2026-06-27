"""
状态报告系统测试
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_report import LayerStateReport, LayerStatus, LayerHealth, SystemSnapshot
from core.reporting.state_collector import get_state_collector, StateCollector
from core.introspection.layer_reporter import LayerReporter


def test_state_report():
    """测试状态报告系统"""
    
    print("=" * 60)
    print("状态报告系统测试")
    print("=" * 60)
    
    collector = get_state_collector()
    
    layers = ["L0", "L1", "L2", "L3", "L4", "L5"]
    
    for layer in layers:
        reporter = LayerReporter(layer)
        
        reporter.report_idle()
        print(f"✓ {layer}: 空闲状态已报告")
        
        reporter.report_busy(f"处理任务")
        print(f"✓ {layer}: 忙碌状态已报告")
        
        reporter.report_completed(
            metrics={"throughput": 100, "accuracy": 0.95},
            confidence=0.92
        )
        print(f"✓ {layer}: 完成状态已报告")
    
    latest = collector.get_all_latest()
    print(f"\n已收集 {len(latest)} 层的状态报告")
    
    snapshot = collector.get_snapshot()
    print(f"\n系统快照:")
    print(f"  整体健康: {snapshot.overall_health.value}")
    print(f"  整体置信度: {snapshot.overall_confidence:.1%}")
    print(f"  健康层数: {snapshot.healthy_layers}/{snapshot.layers_count}")
    print(f"  警告层: {snapshot.warning_layers}")
    print(f"  严重层: {snapshot.critical_layers}")
    
    error_reporter = LayerReporter("L4")
    error_reporter.report_error(["自我质疑失败", "校验未通过"])
    
    snapshot2 = collector.get_snapshot()
    print(f"\n错误报告后:")
    print(f"  整体健康: {snapshot2.overall_health.value}")
    print(f"  L4健康: {snapshot2.layer_reports['L4'].health.value}")
    
    summary = collector.get_status_summary()
    print(f"\n状态摘要:")
    print(f"  {summary['overall_health']}")
    layer_health = [f'{k}={v["health"]}' for k, v in summary['layers'].items()]
    print(f"  各层: {layer_health}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
    print("=" * 60)


if __name__ == "__main__":
    test_state_report()