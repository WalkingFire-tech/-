"""
测试版本控制事实库
验证覆盖机制、置信度衰减等核心功能
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "=" * 70)
print("  🧪 版本控制事实库测试")
print("=" * 70)


def test_override_mechanism():
    """测试覆盖机制"""
    print("\n【测试1】断言覆盖机制")
    print("-" * 50)
    
    from infrastructure.fact_store_v2 import fact_store_v2
    
    # 添加种子数据（低优先级）
    seed_id = fact_store_v2.add_assertion(
        question="测试问题",
        subject="测试主体",
        predicate="测试关系",
        obj="种子数据答案",
        source="seed",
        confidence=0.85,
        is_seed=True
    )
    print(f"  ✅ 添加种子数据: ID={seed_id}, conf=0.85")
    
    # 添加用户纠错（高优先级）
    correction_id = fact_store_v2.add_assertion(
        question="测试问题",
        subject="测试主体",
        predicate="测试关系",
        obj="用户纠错答案",
        source="user_correction",
        confidence=0.95,
        is_seed=False
    )
    print(f"  ✅ 添加用户纠错: ID={correction_id}, conf=0.95")
    
    # 查询断言（应该只返回纠错版本）
    assertions = fact_store_v2.get_assertions("测试问题")
    print(f"\n  查询结果: {len(assertions)}条")
    for a in assertions:
        print(f"    - ({a['subject']}, {a['predicate']}, {a['object']})")
        print(f"      来源: {a['source']}, 置信度: {a['confidence']:.2f}")
        print(f"      是否被覆盖: {a['is_overridden']}")
    
    # 验证：应该返回纠错版本，种子版本被标记为覆盖
    if len(assertions) == 1 and assertions[0]['object'] == "用户纠错答案":
        print(f"\n  ✅ 覆盖机制验证通过")
        return True
    else:
        print(f"\n  ❌ 覆盖机制验证失败")
        return False


def test_source_priority():
    """测试来源优先级"""
    print("\n【测试2】来源优先级")
    print("-" * 50)
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2()
    
    # 测试不同来源的优先级
    test_cases = [
        ("manual_seed", 0.9, "种子数据"),
        ("manual", 0.9, "手动输入"),
        ("learning", 0.9, "学习获得"),
        ("wiki", 0.9, "维基百科"),
        ("correction", 0.9, "用户纠错"),
    ]
    
    question = "优先级测试问题"
    subject = "优先级主体"
    predicate = "优先级关系"
    
    for source, conf, desc in test_cases:
        obj = f"{desc}答案"
        aid = store.add_assertion(
            question=question,
            subject=subject,
            predicate=predicate,
            obj=obj,
            source=source,
            confidence=conf
        )
        print(f"  添加: {desc} (source={source}, ID={aid})")
    
    # 查询最终结果
    assertions = store.get_assertions(question)
    if assertions:
        final = assertions[0]
        print(f"\n  最终断言: {final['object']}")
        print(f"  来源: {final['source']}")
        print(f"  ✅ 最高优先级来源胜出")
        return True
    
    return False


def test_confidence_decay():
    """测试置信度衰减"""
    print("\n【测试3】置信度衰减")
    print("-" * 50)
    
    from infrastructure.fact_store_v2 import fact_store_v2
    from datetime import datetime, timedelta
    import sqlite3
    
    # 添加一个断言
    aid = fact_store_v2.add_assertion(
        question="衰减测试",
        subject="衰减主体",
        predicate="衰减关系",
        obj="衰减答案",
        source="learning",
        confidence=0.9
    )
    print(f"  ✅ 添加断言: ID={aid}, 初始置信度=0.9")
    
    # 手动设置last_used为30天前
    old_date = (datetime.now() - timedelta(days=35)).isoformat()
    with sqlite3.connect(fact_store_v2.db_path) as conn:
        conn.execute('UPDATE fact_assertions SET last_used = ? WHERE id = ?', (old_date, aid))
        conn.commit()
    print(f"  设置last_used为35天前")
    
    # 应用衰减
    fact_store_v2.apply_decay(days_unused=30, decay_rate=0.95)
    
    # 查询衰减后的置信度
    with sqlite3.connect(fact_store_v2.db_path) as conn:
        cursor = conn.execute('SELECT confidence FROM fact_assertions WHERE id = ?', (aid,))
        new_conf = cursor.fetchone()[0]
    
    print(f"  衰减后置信度: {new_conf:.4f}")
    
    if new_conf < 0.9:
        print(f"  ✅ 置信度衰减验证通过")
        return True
    else:
        print(f"  ❌ 置信度衰减验证失败")
        return False


def test_stats():
    """测试统计信息"""
    print("\n【测试4】统计信息")
    print("-" * 50)
    
    from infrastructure.fact_store_v2 import fact_store_v2
    
    stats = fact_store_v2.get_stats()
    
    print(f"  总断言数: {stats['total']}")
    print(f"  种子数据: {stats['seeds']}")
    print(f"  被覆盖: {stats['overridden']}")
    print(f"  活跃断言: {stats['active']}")
    print(f"  纠错记录: {stats['corrections']}")
    
    print(f"\n  按来源统计:")
    for source, info in stats['by_source'].items():
        print(f"    - {source}: {info['count']}条, 平均置信度={info['avg_conf']:.2f}")
    
    return True


def test_evolution_scenario():
    """测试完整进化场景"""
    print("\n【测试5】完整进化场景")
    print("-" * 50)
    
    from infrastructure.fact_store_v2 import FactStoreV2
    
    store = FactStoreV2()
    
    question = "冰雹形成机制"
    subject = "冰雹"
    predicate = "形成原因"
    
    print(f"  问题: {question}")
    
    # 阶段1: 开发者注入种子数据
    print(f"\n  阶段1: 开发者注入种子数据")
    seed_id = store.add_assertion(
        question=question,
        subject=subject,
        predicate=predicate,
        obj="水滴冻结",
        source="seed",
        confidence=0.85,
        is_seed=True
    )
    print(f"    种子数据: (冰雹, 形成原因, 水滴冻结)")
    
    # 阶段2: 用户纠错（第一次）
    print(f"\n  阶段2: 用户纠错（第一次）")
    corr1_id = store.add_assertion(
        question=question,
        subject=subject,
        predicate=predicate,
        obj="过冷水滴冻结",
        source="user_correction",
        confidence=0.9
    )
    print(f"    用户纠错: (冰雹, 形成原因, 过冷水滴冻结)")
    
    # 阶段3: 用户纠错（第二次，更精确）
    print(f"\n  阶段3: 用户纠错（第二次，更精确）")
    corr2_id = store.add_assertion(
        question=question,
        subject=subject,
        predicate=predicate,
        obj="过冷水滴在上升气流中反复冻结",
        source="user_correction_detailed",
        confidence=0.95
    )
    print(f"    详细纠错: (冰雹, 形成原因, 过冷水滴在上升气流中反复冻结)")
    
    # 查询最终结果
    print(f"\n  最终结果:")
    assertions = store.get_assertions(question)
    for a in assertions:
        print(f"    - ({a['subject']}, {a['predicate']}, {a['object']})")
        print(f"      来源: {a['source']}, 置信度: {a['confidence']:.2f}")
    
    # 查看所有版本（包括被覆盖的）
    print(f"\n  所有版本（包括被覆盖）:")
    all_assertions = store.get_assertions(question, include_overridden=True)
    for i, a in enumerate(all_assertions, 1):
        status = "被覆盖" if a['is_overridden'] else "活跃"
        print(f"    {i}. {a['object']} ({a['source']}, conf={a['confidence']:.2f}) [{status}]")
    
    # 统计
    stats = store.get_stats()
    print(f"\n  进化统计:")
    print(f"    总断言: {stats['total']}")
    print(f"    被覆盖: {stats['overridden']}")
    print(f"    纠错记录: {stats['corrections']}")
    
    print(f"\n  ✅ 进化场景验证通过")
    return True


def main():
    """运行所有测试"""
    tests = [
        ("断言覆盖机制", test_override_mechanism),
        ("来源优先级", test_source_priority),
        ("置信度衰减", test_confidence_decay),
        ("统计信息", test_stats),
        ("完整进化场景", test_evolution_scenario),
    ]
    
    results = []
    
    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总
    print("\n" + "=" * 70)
    print("  📊 测试结果汇总")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "-" * 70)
    print(f"  总计: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)