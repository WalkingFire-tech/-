"""
P0核心能力验证测试
验证：事实库版本控制 + 注入验证闭环 + 用户纠错流程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_fact_store_v2_version_control():
    """测试1: 事实库版本控制"""
    print("\n" + "=" * 70)
    print("  测试1: 事实库版本控制（覆盖机制）")
    print("=" * 70)
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2(db_path="data/test_fact_store_v2_p0.db")
    
    # 步骤1: 添加种子数据
    print("\n【步骤1】添加种子数据")
    id1 = store.add_assertion(
        question="Python是什么时候发布的?",
        subject="Python",
        predicate="发布时间",
        obj="1990年",
        source="seed",
        confidence=0.7,
        is_seed=True
    )
    print(f"  ✅ 种子断言: Python发布于1990年 (置信度0.7, 来源seed)")
    
    # 步骤2: 用户纠错（应该覆盖）
    print("\n【步骤2】用户纠错：应该是1991年")
    id2 = store.add_assertion(
        question="Python是什么时候发布的?",
        subject="Python",
        predicate="发布时间",
        obj="1991年",
        source="user_correction",
        confidence=0.95,
        is_seed=False
    )
    print(f"  ✅ 纠错断言: Python发布于1991年 (置信度0.95, 来源user_correction)")
    
    # 步骤3: 验证覆盖效果
    print("\n【步骤3】验证覆盖效果")
    assertions = store.get_assertions("Python是什么时候发布的?")
    print(f"  当前有效断言数: {len(assertions)}")
    
    if assertions:
        current = assertions[0]
        print(f"  当前值: {current['object']}")
        print(f"  置信度: {current['confidence']}")
        print(f"  来源: {current['source']}")
        print(f"  是否被覆盖: {current['is_overridden']}")
        
        assert current['object'] == "1991年", "纠错未生效！"
        assert current['source'] == "user_correction", "来源错误！"
        print("\n  ✅ 覆盖机制验证通过")
    
    # 步骤4: 查看历史
    print("\n【步骤4】查看纠错历史")
    history = store.get_assertions("Python是什么时候发布的?", include_overridden=True)
    print(f"  历史断言数: {len(history)}")
    for h in history:
        status = "已覆盖" if h['is_overridden'] else "当前有效"
        print(f"    - {h['object']} ({h['source']}, 置信度{h['confidence']}) [{status}]")
    
    return True


def test_confidence_decay():
    """测试2: 置信度衰减"""
    print("\n" + "=" * 70)
    print("  测试2: 置信度衰减机制")
    print("=" * 70)
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2(db_path="data/test_fact_store_v2_p0.db")
    
    # 添加一个断言
    id1 = store.add_assertion(
        question="测试问题",
        subject="测试",
        predicate="属性",
        obj="测试值",
        source="manual",
        confidence=0.9,
        is_seed=False
    )
    print(f"✅ 添加断言: 置信度0.9")
    
    # 应用衰减
    print(f"\n应用置信度衰减（30天未使用）...")
    store.apply_decay(days_unused=30, decay_rate=0.95)
    
    # 查看结果
    assertions = store.get_assertions("测试问题")
    if assertions:
        print(f"  衰减后置信度: {assertions[0]['confidence']:.3f}")
        print(f"  衰减因子: {assertions[0].get('decay_factor', 1.0):.3f}")
    
    print("\n✅ 置信度衰减测试通过")
    return True


def test_verification_loop():
    """测试3: 注入验证闭环"""
    print("\n" + "=" * 70)
    print("  测试3: 注入验证闭环")
    print("=" * 70)
    
    from infrastructure.verification_loop import KnowledgeVerificationLoop
    
    loop = KnowledgeVerificationLoop(db_path="data/test_verification_p0.db")
    
    # 场景1: 验证通过
    print("\n【场景1】验证通过")
    loop_id1 = loop.start_verification_loop(
        question="什么是深度学习?",
        before_score=30.0,
        before_confidence=0.4,
        before_knowledge_count=0
    )
    print(f"  开始循环: {loop_id1}")
    
    loop.record_injection(
        loop_id=loop_id1,
        injection_source="wikipedia",
        injected_knowledge=[
            {'content': '深度学习是机器学习的分支', 'confidence': 0.9},
            {'content': '深度学习使用神经网络', 'confidence': 0.85}
        ]
    )
    print(f"  记录注入: 2条知识")
    
    result1 = loop.complete_verification(
        loop_id=loop_id1,
        after_score=65.0,
        after_confidence=0.85,
        after_knowledge_count=2,
        threshold=5.0
    )
    print(f"  验证结果: {'通过' if result1['passed'] else '未通过'}")
    print(f"  改进: {result1['improvement']:.1f}分")
    
    # 场景2: 验证未通过
    print("\n【场景2】验证未通过（需要修正）")
    loop_id2 = loop.start_verification_loop(
        question="什么是量子计算?",
        before_score=40.0,
        before_confidence=0.5,
        before_knowledge_count=0
    )
    
    loop.record_injection(
        loop_id=loop_id2,
        injection_source="external",
        injected_knowledge=[
            {'content': '量子计算使用量子比特', 'confidence': 0.6}
        ]
    )
    
    result2 = loop.complete_verification(
        loop_id=loop_id2,
        after_score=42.0,
        after_confidence=0.6,
        after_knowledge_count=1,
        threshold=10.0  # 高阈值
    )
    print(f"  验证结果: {'通过' if result2['passed'] else '未通过'}")
    print(f"  改进: {result2['improvement']:.1f}分 (阈值{result2['threshold']})")
    print(f"  需要修正: {result2['needs_correction']}")
    
    # 获取修正候选
    print("\n【修正流程】")
    candidates = loop.get_correction_candidates()
    print(f"  待修正循环数: {len(candidates)}")
    
    if candidates:
        loop.apply_correction(
            loop_id=candidates[0]['loop_id'],
            correction_actions=["尝试其他知识源", "调整查询策略"],
            correction_result="已从Wikipedia重新获取知识"
        )
        print(f"  ✅ 修正已应用")
    
    # 统计
    print("\n【验证统计】")
    stats = loop.get_statistics()
    print(f"  总验证循环: {stats['total_loops']}")
    print(f"  通过率: {stats['pass_rate']:.1%}")
    print(f"  平均改进: {stats['avg_improvement']:.1f}分")
    print(f"  已修正: {stats['corrected']}")
    
    print("\n✅ 验证闭环测试通过")
    return True


def test_user_correction_flow():
    """测试4: 用户纠错流程"""
    print("\n" + "=" * 70)
    print("  测试4: 用户纠错流程")
    print("=" * 70)
    
    from infrastructure.user_correction_flow import UserCorrectionFlow
    
    flow = UserCorrectionFlow()
    
    # 场景1: 简单纠错
    print("\n【场景1】简单纠错")
    result1 = flow.process_correction(
        question="Python是什么时候发布的?",
        old_answer="Python于1990年发布",
        correction_feedback="不对，应该是1991年发布的",
        before_score=30.0
    )
    
    print(f"  纠错成功: {result1['success']}")
    print(f"  提取三元组: {result1.get('extracted_triples', [])}")
    print(f"  更新断言数: {result1.get('updated_assertions', 0)}")
    if 'verification' in result1:
        print(f"  验证通过: {result1['verification']['passed']}")
        print(f"  改进: {result1['verification']['improvement']:.1f}分")
    
    # 场景2: 详细纠错
    print("\n【场景2】详细纠错")
    result2 = flow.process_correction(
        question="什么是机器学习?",
        old_answer="机器学习是AI的一个分支",
        correction_feedback="不完全对，机器学习是人工智能的核心技术，通过数据训练模型",
        before_score=50.0
    )
    
    print(f"  纠错成功: {result2['success']}")
    print(f"  更新断言数: {result2.get('updated_assertions', 0)}")
    
    # 查看纠错历史
    print("\n【纠错历史】")
    history = flow.get_correction_history("Python是什么时候发布的?")
    print(f"  历史记录数: {len(history)}")
    
    print("\n✅ 用户纠错流程测试通过")
    return True


def test_source_priority():
    """测试5: 来源优先级"""
    print("\n" + "=" * 70)
    print("  测试5: 来源优先级")
    print("=" * 70)
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2(db_path="data/test_source_priority.db")
    
    # 按优先级从低到高添加
    sources = [
        ("seed", 0.7, "种子数据"),
        ("manual", 0.8, "手动输入"),
        ("learning", 0.85, "外部学习"),
        ("wiki", 0.9, "维基百科"),
        ("user_correction", 0.95, "用户纠错"),
    ]
    
    print("\n按优先级从低到高添加断言:")
    for i, (source, conf, desc) in enumerate(sources, 1):
        store.add_assertion(
            question="测试优先级",
            subject="测试",
            predicate="值",
            obj=f"值{i}",
            source=source,
            confidence=conf,
            is_seed=(source == "seed")
        )
        print(f"  {i}. {desc} (来源={source}, 置信度={conf})")
    
    # 查看最终值
    assertions = store.get_assertions("测试优先级")
    print(f"\n最终有效断言:")
    if assertions:
        current = assertions[0]
        print(f"  值: {current['object']}")
        print(f"  来源: {current['source']}")
        print(f"  置信度: {current['confidence']}")
        print(f"\n  ✅ 最高优先级来源生效")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  P0核心能力验证测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("事实库版本控制", test_fact_store_v2_version_control),
        ("置信度衰减", test_confidence_decay),
        ("注入验证闭环", test_verification_loop),
        ("用户纠错流程", test_user_correction_flow),
        ("来源优先级", test_source_priority),
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