"""
L6内省层测试
"""

import os
import sys
from datetime import datetime
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l6_introspection import get_l6_introspection, SystemHealthLevel, AnomalySeverity


def test_l6_initialization():
    """测试L6初始化"""
    print("=" * 60)
    print("L6内省层初始化测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    assert l6 is not None
    assert l6.reporter is not None
    assert l6.collector is not None
    assert l6.heartbeat is not None
    
    print("✅ L6初始化测试通过")


def test_health_assessment():
    """测试健康度评估"""
    print("\n" + "=" * 60)
    print("健康度评估测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    snapshot = l6.collector.get_snapshot()
    health = l6._assess_health(snapshot)
    
    print(f"\n健康度评估结果:")
    print(f"  整体健康度: {health.overall:.3f}")
    print(f"  健康级别: {health.get_level().value}")
    print(f"  层间协调性: {health.coordination:.3f}")
    print(f"  趋势: {health.trend}")
    
    print(f"\n各层健康度:")
    for layer, score in health.layers.items():
        print(f"  {layer}: {score:.3f}")
    
    assert 0.0 <= health.overall <= 1.0
    assert 0.0 <= health.coordination <= 1.0
    
    print("✅ 健康度评估测试通过")


def test_anomaly_detection():
    """测试异常检测"""
    print("\n" + "=" * 60)
    print("异常检测测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    snapshot = l6.collector.get_snapshot()
    health = l6._assess_health(snapshot)
    
    anomalies = l6._detect_anomalies(snapshot, health)
    
    print(f"\n异常检测结果:")
    print(f"  检测到异常: {len(anomalies)}个")
    
    for anomaly in anomalies[:5]:
        print(f"  - [{anomaly.severity.value}] {anomaly.title}")
        print(f"    描述: {anomaly.description[:50]}...")
    
    print("✅ 异常检测测试通过")


def test_introspection_report():
    """测试内省报告生成"""
    print("\n" + "=" * 60)
    print("内省报告生成测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    report = l6.generate_report()
    
    print(f"\n内省报告:")
    print(f"  时间戳: {report.timestamp}")
    print(f"  健康度: {report.health.overall:.3f}")
    print(f"  健康级别: {report.health.get_level().value}")
    print(f"  活跃异常: {len(report.active_anomalies)}个")
    print(f"  最近变更: {len(report.recent_changes)}项")
    print(f"  建议: {len(report.recommendations)}条")
    print(f"  摘要: {report.summary}")
    
    if report.recommendations:
        print(f"\n建议列表:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
    
    assert report.health is not None
    
    print("✅ 内省报告生成测试通过")


def test_background_introspection():
    """测试后台内省"""
    print("\n" + "=" * 60)
    print("后台内省测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    print("\n启动后台内省...")
    l6.start_background_introspection()
    
    time.sleep(2)
    
    status = l6.get_introspection_status()
    
    print(f"\n后台内省状态:")
    print(f"  运行中: {status['running']}")
    print(f"  总内省次数: {status['stats']['total_introspections']}")
    print(f"  健康检查次数: {status['stats']['health_checks']}")
    
    print("\n停止后台内省...")
    l6.stop_background_introspection()
    
    print("✅ 后台内省测试通过")


def test_get_introspection_status():
    """测试获取内省状态"""
    print("\n" + "=" * 60)
    print("内省状态测试")
    print("=" * 60)
    
    l6 = get_l6_introspection()
    
    status = l6.get_introspection_status()
    
    print(f"\n内省状态:")
    print(f"  层: {status['layer']}")
    print(f"  状态: {status['status']}")
    print(f"  平均健康度: {status['health']['avg']:.3f}")
    print(f"  历史记录数: {status['health']['history_count']}")
    print(f"  趋势: {status['health']['trend']}")
    print(f"  活跃异常: {status['anomalies']['active']}")
    print(f"  总检测异常: {status['anomalies']['total_detected']}")
    print(f"  总解决异常: {status['anomalies']['total_resolved']}")
    print(f"  相邻层状态: {status['neighbor_status']}")
    
    assert status['layer'] == 'L6'
    
    print("✅ 内省状态测试通过")


def test_system_health_level_enum():
    """测试系统健康级别枚举"""
    print("\n" + "=" * 60)
    print("系统健康级别枚举测试")
    print("=" * 60)
    
    print(f"\n健康级别:")
    print(f"  EXCELLENT: {SystemHealthLevel.EXCELLENT.value}")
    print(f"  GOOD: {SystemHealthLevel.GOOD.value}")
    print(f"  FAIR: {SystemHealthLevel.FAIR.value}")
    print(f"  POOR: {SystemHealthLevel.POOR.value}")
    print(f"  CRITICAL: {SystemHealthLevel.CRITICAL.value}")
    
    assert SystemHealthLevel.EXCELLENT.value == "excellent"
    assert SystemHealthLevel.CRITICAL.value == "critical"
    
    print("✅ 系统健康级别枚举测试通过")


def test_anomaly_severity_enum():
    """测试异常严重程度枚举"""
    print("\n" + "=" * 60)
    print("异常严重程度枚举测试")
    print("=" * 60)
    
    print(f"\n异常严重程度:")
    print(f"  CRITICAL: {AnomalySeverity.CRITICAL.value}")
    print(f"  MAJOR: {AnomalySeverity.MAJOR.value}")
    print(f"  MINOR: {AnomalySeverity.MINOR.value}")
    print(f"  OBSERVATION: {AnomalySeverity.OBSERVATION.value}")
    
    assert AnomalySeverity.CRITICAL.value == "critical"
    assert AnomalySeverity.MAJOR.value == "major"
    
    print("✅ 异常严重程度枚举测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("L6内省层完整测试")
    print("=" * 60)
    
    try:
        test_l6_initialization()
        test_health_assessment()
        test_anomaly_detection()
        test_introspection_report()
        test_get_introspection_status()
        test_system_health_level_enum()
        test_anomaly_severity_enum()
        
        print("\n" + "=" * 60)
        print("✅ 所有L6内省层测试通过!")
        print("=" * 60)
        
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)