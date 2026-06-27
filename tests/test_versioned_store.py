"""
第一阶段验证测试
测试版本控制事实库的完整功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_version_control():
    """测试版本控制完整流程"""
    print("\n" + "=" * 70)
    print("  测试: 版本控制完整流程")
    print("=" * 70)
    
    from infrastructure.versioned_fact_store import VersionedFactStore
    
    store = VersionedFactStore(db_path="data/test_versioned_store.db")
    
    # 场景1: 种子数据 → 用户纠错
    print("\n【场景1】种子数据 → 用户纠错")
    
    id1, action1 = store.add_assertion(
        question="Python是什么时候发布的?",
        subject="Python",
        predicate="发布时间",
        obj="1990年",
        source="seed",
        confidence=0.7,
        is_seed=True,
        override_strategy="user"
    )
    print(f"  步骤1: 添加种子数据 - ID={id1}, 动作={action1}")
    
    id2, action2 = store.add_assertion(
        question="Python是什么时候发布的?",
        subject="Python",
        predicate="发布时间",
        obj="1991年",
        source="correction",
        confidence=0.95,
        is_seed=False,
        override_strategy="user"
    )
    print(f"  步骤2: 用户纠错 - ID={id2}, 动作={action2}")
    
    # 验证覆盖效果
    assertions = store.get_active_assertions("Python是什么时候发布的?")
    print(f"\n  当前有效断言:")
    for a in assertions:
        print(f"    - {a['object']} (来源={a['source']}, 版本={a['version']}, 置信度={a['confidence']})")
    
    assert len(assertions) == 1, "应该只有1个有效断言"
    assert assertions[0]['object'] == "1991年", "应该是纠错后的值"
    assert assertions[0]['source'] == "correction", "来源应该是correction"
    print("\n  ✅ 场景1通过: 用户纠错成功覆盖种子数据")
    
    # 场景2: 查看历史版本
    print("\n【场景2】查看历史版本")
    history = store.get_assertion_history(
        "Python是什么时候发布的?",
        "Python",
        "发布时间"
    )
    print(f"  历史版本数: {len(history)}")
    for h in history:
        status = "当前有效" if h['is_active'] else "已覆盖"
        print(f"    - 版本{h['version']}: {h['object']} ({h['source']}) [{status}]")
    
    assert len(history) == 2, "应该有2个历史版本"
    print("\n  ✅ 场景2通过: 历史版本正确记录")
    
    # 场景3: 版本回滚
    print("\n【场景3】版本回滚")
    success = store.rollback_to_version(id2, 1)
    print(f"  回滚结果: {success}")
    
    assertions = store.get_active_assertions("Python是什么时候发布的?")
    print(f"  回滚后有效断言:")
    for a in assertions:
        print(f"    - {a['object']} (版本={a['version']})")
    
    assert assertions[0]['object'] == "1990年", "应该回滚到种子数据"
    print("\n  ✅ 场景3通过: 版本回滚成功")
    
    # 场景4: 置信度策略
    print("\n【场景4】置信度策略")
    
    id3, action3 = store.add_assertion(
        question="测试问题",
        subject="测试",
        predicate="属性",
        obj="低置信度值",
        source="manual",
        confidence=0.6,
        override_strategy="confidence"
    )
    print(f"  步骤1: 低置信度断言 - ID={id3}, 动作={action3}")
    
    id4, action4 = store.add_assertion(
        question="测试问题",
        subject="测试",
        predicate="属性",
        obj="高置信度值",
        source="manual",
        confidence=0.9,
        override_strategy="confidence"
    )
    print(f"  步骤2: 高置信度断言 - ID={id4}, 动作={action4}")
    
    assertions = store.get_active_assertions("测试问题")
    print(f"  当前有效断言: {assertions[0]['object']}")
    
    assert assertions[0]['object'] == "高置信度值", "高置信度应该覆盖低置信度"
    print("\n  ✅ 场景4通过: 置信度策略正确")
    
    # 场景5: keep策略
    print("\n【场景5】keep策略（保留旧版本）")
    
    id5, action5 = store.add_assertion(
        question="保留测试",
        subject="测试",
        predicate="值",
        obj="初始值",
        source="manual",
        confidence=0.8
    )
    print(f"  步骤1: 初始断言 - ID={id5}, 动作={action5}")
    
    id6, action6 = store.add_assertion(
        question="保留测试",
        subject="测试",
        predicate="值",
        obj="新值",
        source="manual",
        confidence=0.9,
        override_strategy="keep"
    )
    print(f"  步骤2: 尝试覆盖（keep策略） - ID={id6}, 动作={action6}")
    
    assertions = store.get_active_assertions("保留测试")
    print(f"  当前有效断言: {assertions[0]['object']}")
    
    assert assertions[0]['object'] == "初始值", "keep策略应该保留旧版本"
    print("\n  ✅ 场景5通过: keep策略正确")
    
    # 统计信息
    print("\n【统计信息】")
    stats = store.get_statistics()
    print(f"  总断言数: {stats['total']}")
    print(f"  有效断言: {stats['active']}")
    print(f"  已覆盖: {stats['superseded']}")
    print(f"  种子数据: {stats['seeds']}")
    
    return True


def test_conflict_resolution():
    """测试冲突解决策略"""
    print("\n" + "=" * 70)
    print("  测试: 冲突解决策略")
    print("=" * 70)
    
    from infrastructure.versioned_fact_store import VersionedFactStore
    
    store = VersionedFactStore(db_path="data/test_conflict_resolution.db")
    
    # 测试来源优先级
    print("\n【来源优先级】")
    
    sources = [
        ("seed", 0.7, "种子数据"),
        ("manual", 0.8, "手动输入"),
        ("learning", 0.85, "外部学习"),
        ("correction", 0.95, "用户纠错"),
    ]
    
    for i, (source, conf, desc) in enumerate(sources, 1):
        id, action = store.add_assertion(
            question="优先级测试",
            subject="测试",
            predicate="值",
            obj=f"值{i}",
            source=source,
            confidence=conf,
            is_seed=(source == "seed"),
            override_strategy="user"
        )
        print(f"  {i}. {desc} (来源={source}, 置信度={conf}) - 动作={action}")
    
    assertions = store.get_active_assertions("优先级测试")
    print(f"\n最终有效断言: {assertions[0]['object']} (来源={assertions[0]['source']})")
    
    assert assertions[0]['source'] == "correction", "用户纠错应该优先级最高"
    print("\n✅ 来源优先级测试通过")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  第一阶段验证测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests = [
        ("版本控制完整流程", test_version_control),
        ("冲突解决策略", test_conflict_resolution),
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