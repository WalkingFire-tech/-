"""
交互数据收集系统测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_data_collection():
    """测试数据收集"""
    print("\n" + "=" * 70)
    print("  测试: 交互数据收集")
    print("=" * 70)
    
    from infrastructure.interaction_data_collector import InteractionDataCollector
    
    collector = InteractionDataCollector(db_path="data/test_interaction_data.db")
    
    # 场景1: 记录高质量交互
    print("\n【场景1】记录高质量交互")
    id1 = collector.save_interaction(
        session_id="test_session_001",
        question="什么是机器学习?",
        response="机器学习是人工智能的一个分支，通过数据训练模型，使计算机能够从数据中学习规律并做出预测。",
        feedback_type="positive",
        feedback_content="回答很好",
        objective_score=75.0,
        subjective_score=80.0,
        total_score=77.0,
        decision_chain_summary="L1:意图识别→L2:知识检索→L3:回答生成",
        knowledge_sources=["fact_store", "external_learn"],
        model_version="1.0",
        system_version="1.0"
    )
    print(f"  ✅ 记录ID: {id1}")
    
    # 场景2: 记录纠错交互
    print("\n【场景2】记录纠错交互")
    id2 = collector.save_interaction(
        session_id="test_session_001",
        question="Python是什么时候发布的?",
        response="Python于1990年发布。",
        feedback_type="correction",
        feedback_content="不对，应该是1991年发布的",
        objective_score=30.0,
        subjective_score=20.0,
        total_score=26.0,
        decision_chain_summary="L1:意图识别→L2:知识检索(失败)→L3:回答生成",
        knowledge_sources=[]
    )
    print(f"  ✅ 记录ID: {id2}")
    
    # 场景3: 记录低质量交互
    print("\n【场景3】记录低质量交互")
    id3 = collector.save_interaction(
        session_id="test_session_001",
        question="你好",
        response="你好！",
        feedback_type="neutral",
        feedback_content="",
        objective_score=50.0,
        subjective_score=50.0,
        total_score=50.0,
        decision_chain_summary="",
        knowledge_sources=[]
    )
    print(f"  ✅ 记录ID: {id3}")
    
    # 统计
    print("\n【统计信息】")
    stats = collector.get_statistics()
    print(f"  总交互数: {stats['total_interactions']}")
    print(f"  正面反馈: {stats['positive_feedback']}")
    print(f"  负面反馈: {stats['negative_feedback']}")
    print(f"  纠错: {stats['corrections']}")
    print(f"  高质量数据: {stats['high_quality_data']}")
    print(f"  平均分: {stats['avg_score']:.1f}")
    print(f"  可用于SFT: {stats['ready_for_sft']}")
    
    return True


def test_sft_export():
    """测试SFT数据导出"""
    print("\n" + "=" * 70)
    print("  测试: SFT数据导出")
    print("=" * 70)
    
    from infrastructure.interaction_data_collector import InteractionDataCollector
    
    collector = InteractionDataCollector(db_path="data/test_interaction_data.db")
    
    # 导出JSON格式
    print("\n【导出JSON格式】")
    count1 = collector.export_for_sft(
        output_path="data/sft_training_data.json",
        format_type="json",
        min_quality_score=0.5,
        include_corrections=True
    )
    print(f"  导出记录数: {count1}")
    
    # 导出JSONL格式
    print("\n【导出JSONL格式】")
    count2 = collector.export_for_sft(
        output_path="data/sft_training_data.jsonl",
        format_type="jsonl",
        min_quality_score=0.5,
        include_corrections=True
    )
    print(f"  导出记录数: {count2}")
    
    # 查看导出的数据
    if count1 > 0:
        import json
        with open("data/sft_training_data.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n【示例数据】")
        for i, item in enumerate(data[:2], 1):
            print(f"  {i}. 指令: {item['instruction']}")
            print(f"     输入: {item['input'][:50]}...")
            print(f"     输出: {item['output'][:50]}...")
    
    return True


def test_data_quality():
    """测试数据质量评估"""
    print("\n" + "=" * 70)
    print("  测试: 数据质量评估")
    print("=" * 70)
    
    from infrastructure.interaction_data_collector import InteractionDataCollector
    
    collector = InteractionDataCollector(db_path="data/test_interaction_data.db")
    
    # 获取高质量数据
    print("\n【获取高质量数据】")
    high_quality = collector.get_training_data(
        min_quality_score=0.7,
        feedback_types=['positive', 'correction'],
        limit=10
    )
    
    print(f"  高质量数据数: {len(high_quality)}")
    
    for i, record in enumerate(high_quality[:3], 1):
        print(f"\n  {i}. 问题: {record['question'][:40]}...")
        print(f"     反馈类型: {record['feedback_type']}")
        print(f"     总分: {record['total_score']:.1f}")
        print(f"     质量分: {record['quality_score']:.2f}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  交互数据收集系统测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("数据收集", test_data_collection),
        ("SFT数据导出", test_sft_export),
        ("数据质量评估", test_data_quality),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ 通过", None))
        except Exception as e:
            results.append((name, "❌ 失败", str(e)))
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)
    
    for name, status, error in results:
        print(f"{status} {name}")
        if error:
            print(f"     错误: {error[:100]}")
    
    passed = sum(1 for _, status, _ in results if "通过" in status)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)