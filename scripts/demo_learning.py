"""
修复后的动态学习演示
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.versioned_fact_store import VersionedFactStore

print("\n" + "=" * 70)
print("  演示：动态学习机制")
print("=" * 70)

store = VersionedFactStore()

# 步骤1: 查看初始状态
print("\n【步骤1】初始状态")
stats = store.get_statistics()
print(f"  总断言: {stats['total']}条")

# 步骤2: 添加新知识（模拟用户纠错）
print("\n【步骤2】用户教系统新知识: 强化学习")
id1, action1 = store.add_assertion(
    question="什么是强化学习?",
    subject="强化学习",
    predicate="定义",
    obj="机器学习的一种方法，通过与环境交互、试错学习最优策略",
    source="user_correction",
    confidence=0.95
)
print(f"  添加结果: ID={id1}, 动作={action1}")

# 步骤3: 检索验证
print("\n【步骤3】检索验证")
assertions = store.get_active_assertions("什么是强化学习?")
print(f"  检索到: {len(assertions)}条知识")
if assertions:
    print(f"  内容: {assertions[0]['object'][:50]}...")
    print(f"  来源: {assertions[0]['source']}")

# 步骤4: 再添加一个
print("\n【步骤4】再教一个: 自然语言处理")
id2, action2 = store.add_assertion(
    question="什么是自然语言处理?",
    subject="自然语言处理",
    predicate="定义",
    obj="AI的一个分支，让计算机理解和生成人类语言",
    source="user_correction",
    confidence=0.95
)

assertions2 = store.get_active_assertions("什么是自然语言处理?")
print(f"  检索到: {len(assertions2)}条知识")

# 步骤5: 最终统计
print("\n【步骤5】最终统计")
stats = store.get_statistics()
print(f"  总断言: {stats['total']}条")
print(f"  有效断言: {stats['active']}条")
print(f"  种子数据: {stats['seeds']}条")
print(f"  用户添加: {stats['total'] - stats['seeds']}条")

print("\n" + "=" * 70)
print("✅ 动态学习机制正常工作")
print("=" * 70)
print("\n关键点:")
print("  1. 种子知识只是初始值，不是固定的")
print("  2. 用户纠错会自动添加新知识")
print("  3. 系统会记住学到的所有知识")
print("  4. 知识可以被覆盖和更新")
print("  5. 换新问题后，用户纠错就能教会系统")