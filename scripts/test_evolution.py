# -*- coding: utf-8 -*-
"""
测试自我进化功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.self_evolution import SelfEvolutionEngine

def test_evolution():
    """测试自我进化引擎"""
    print("="*60)
    print("测试自我进化引擎")
    print("="*60)
    print()
    
    # 创建引擎
    engine = SelfEvolutionEngine(
        data_threshold=10,  # 降低阈值用于测试
        training_interval_hours=0  # 立即训练
    )
    
    # 检查数据积累
    print("\n1. 检查数据积累")
    data_status = engine.check_data_accumulation()
    print(f"   总数据: {data_status['total_samples']} 条")
    print(f"   新增数据: {data_status['new_samples']} 条")
    print(f"   准备训练: {data_status['ready_for_training']}")
    
    # 检查训练时间
    print("\n2. 检查训练时间")
    time_status = engine.check_training_time()
    print(f"   应该训练: {time_status}")
    
    # 获取进化摘要
    print("\n3. 进化摘要")
    summary = engine.get_evolution_summary()
    print(f"   总进化次数: {summary['total_evolutions']}")
    print(f"   已训练数据: {summary['total_samples_trained']} 条")
    print(f"   上次进化: {summary['last_evolution']}")
    print(f"   下次进化: {summary['next_evolution_estimate']}")
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_evolution()