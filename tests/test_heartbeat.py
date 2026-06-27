"""
心跳机制测试
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.introspection.heartbeat import get_heartbeat_manager, HeartbeatStatus
from core.reporting.state_collector import get_state_collector


def test_heartbeat():
    """测试心跳机制"""
    print("=" * 60)
    print("层间心跳机制测试")
    print("=" * 60)
    
    hbm = get_heartbeat_manager()
    collector = get_state_collector()
    
    layers = ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]
    for layer in layers:
        hbm.register_layer(layer)
    
    hbm.start_background()
    
    print("\n心跳服务已启动，等待5秒收集心跳...")
    time.sleep(5)
    
    print("\n各层状态:")
    for layer in layers:
        status = hbm.get_layer_status(layer)
        neighbors = hbm.get_neighbor_status(layer)
        print(f"  {layer}: {status.value}")
        if neighbors:
            neighbor_status = {k: v.value for k, v in neighbors.items()}
            print(f"    相邻层: {neighbor_status}")
    
    print("\nL1 → L2 心跳:")
    heartbeat = hbm.get_heartbeat("L1", "L2")
    if heartbeat:
        print(f"  状态: {heartbeat.status.value}")
        print(f"  负载: {heartbeat.load:.2f}")
        print(f"  最后操作: {heartbeat.last_operation}")
        print(f"  时间: {heartbeat.timestamp}")
    else:
        print("  ❌ 未收到L1 → L2心跳")
    
    print("\n层存活检测:")
    for layer in layers:
        alive = hbm.is_layer_alive(layer)
        print(f"  {layer}: {'✅ 存活' if alive else '❌ 死亡'}")
    
    hbm.stop_background()
    
    print("\n" + "=" * 60)
    print("✅ 心跳测试完成")
    print("=" * 60)


def test_heartbeat_integration():
    """测试心跳与状态报告的集成"""
    print("\n" + "=" * 60)
    print("心跳与状态报告集成测试")
    print("=" * 60)
    
    from core.introspection.layer_reporter import LayerReporter
    
    hbm = get_heartbeat_manager()
    collector = get_state_collector()
    
    for layer in ["L0", "L1", "L2", "L3", "L4", "L5"]:
        reporter = LayerReporter(layer)
        reporter.report_completed(
            metrics={"load": 0.5, "throughput": 100},
            confidence=0.9
        )
    
    hbm.start_background()
    time.sleep(3)
    
    print("\n各层状态（从心跳获取）:")
    for layer in ["L0", "L1", "L2", "L3", "L4", "L5"]:
        status = hbm.get_layer_status(layer)
        load = hbm._get_layer_load(layer)
        print(f"  {layer}: {status.value}, 负载={load:.2f}")
    
    print("\n相邻层状态:")
    neighbors = hbm.get_neighbor_status("L2")
    for neighbor, status in neighbors.items():
        print(f"  L2的相邻层 {neighbor}: {status.value}")
    
    hbm.stop_background()
    
    print("\n✅ 集成测试完成")


if __name__ == "__main__":
    test_heartbeat()
    test_heartbeat_integration()