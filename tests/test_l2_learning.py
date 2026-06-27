"""
L2学习层测试
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l2_learning import get_l2_learning, LearningResult
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager


def test_l2_initialization():
    """测试L2初始化"""
    print("=" * 60)
    print("L2学习层初始化测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    
    assert l2 is not None
    assert l2.reporter is not None
    assert l2.collector is not None
    assert l2.heartbeat is not None
    
    print("✅ L2初始化测试通过")


def test_l2_learning():
    """测试L2学习流程"""
    print("\n" + "=" * 60)
    print("L2学习流程测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    
    target = {
        'name': '26650电池保护芯片',
        'keywords': ['26650', '电池', '保护芯片', 'BMS']
    }
    
    result = l2.learn(target)
    
    print(f"\n学习结果:")
    print(f"  成功: {result.success}")
    print(f"  获取知识: {result.knowledge_gained}条")
    print(f"  知识ID: {result.knowledge_ids}")
    print(f"  来源: {result.sources_used}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  错误: {result.error}")
    
    assert result is not None
    assert isinstance(result, LearningResult)
    
    print("\n✅ L2学习流程测试通过")


def test_l2_status_report():
    """测试L2状态报告"""
    print("\n" + "=" * 60)
    print("L2状态报告测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    collector = get_state_collector()
    
    target = {
        'name': '锂电保护电路设计',
        'keywords': ['锂电池', '保护电路', '设计']
    }
    
    result = l2.learn(target)
    
    latest_report = collector.get_latest("L2")
    
    print(f"\nL2最新状态报告:")
    print(f"  层名: {latest_report.layer_name}")
    print(f"  状态: {latest_report.status.value}")
    print(f"  健康度: {latest_report.health.value}")
    print(f"  置信度: {latest_report.confidence_score:.2f}")
    print(f"  指标: {latest_report.metrics}")
    print(f"  问题: {latest_report.issues}")
    print(f"  警告: {latest_report.warnings}")
    
    assert latest_report is not None
    assert latest_report.layer_name == "L2"
    
    print("\n✅ L2状态报告测试通过")


def test_l2_heartbeat_integration():
    """测试L2心跳集成"""
    print("\n" + "=" * 60)
    print("L2心跳集成测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    hbm = get_heartbeat_manager()
    
    hbm.start_background()
    time.sleep(3)
    
    status = l2.get_learning_status()
    
    print(f"\nL2学习状态:")
    print(f"  层: {status['layer']}")
    print(f"  统计: {status['stats']}")
    print(f"  相邻层状态: {status['neighbor_status']}")
    print(f"  待处理目标: {status['pending_targets']}")
    
    neighbor_status = hbm.get_neighbor_status("L2")
    print(f"\nL2相邻层心跳状态:")
    for neighbor, hb_status in neighbor_status.items():
        print(f"  {neighbor}: {hb_status.value}")
    
    hbm.stop_background()
    
    print("\n✅ L2心跳集成测试通过")


def test_l2_multiple_learning():
    """测试L2多次学习"""
    print("\n" + "=" * 60)
    print("L2多次学习测试")
    print("=" * 60)
    
    l2 = get_l2_learning()
    
    targets = [
        {'name': '芯片选型', 'keywords': ['芯片', '选型']},
        {'name': '电路保护', 'keywords': ['电路', '保护']},
        {'name': '电池管理', 'keywords': ['电池', '管理', 'BMS']}
    ]
    
    results = []
    for target in targets:
        result = l2.learn(target)
        results.append(result)
        print(f"  学习 '{target['name']}': {result.knowledge_gained}条知识")
    
    status = l2.get_learning_status()
    
    print(f"\n学习统计:")
    print(f"  总尝试: {status['stats']['total_learning_attempts']}")
    print(f"  成功次数: {status['stats']['total_successful_learning']}")
    print(f"  总知识量: {status['stats']['total_knowledge_gained']}")
    print(f"  学习来源: {status['stats']['learning_sources']}")
    
    assert len(results) == 3
    assert status['stats']['total_learning_attempts'] >= 3
    
    print("\n✅ L2多次学习测试通过")


if __name__ == "__main__":
    test_l2_initialization()
    test_l2_learning()
    test_l2_status_report()
    test_l2_heartbeat_integration()
    test_l2_multiple_learning()
    
    print("\n" + "=" * 60)
    print("所有L2测试通过 ✅")
    print("=" * 60)