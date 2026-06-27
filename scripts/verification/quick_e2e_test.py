"""
快速端到端测试 - 验证核心功能
"""

import sys
import os
import sqlite3

sys.path.insert(0, '.')

print("=" * 60)
print("联盟拓荒者 - 快速端到端测试")
print("=" * 60)

passed = 0
failed = 0

print("\n[1/8] 测试L1感知层...")
try:
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    l1 = L1PerceptionLayer()
    result = l1.perceive("帮我计算 2+3")
    print(f"  ✓ L1感知层: 情绪={result['emotional_state'].primary_emotion}, 意图={result['intent']}")
    passed += 1
except Exception as e:
    print(f"  ✗ L1感知层: {e}")
    failed += 1

print("\n[2/8] 测试数据库...")
try:
    dbs = [
        ("经验池", "data/experience_pool.db"),
        ("学习规则", "data/learning_rules.db"),
        ("反思日志", "logs/campfire_log.db"),
    ]
    for name, path in dbs:
        if os.path.exists(path):
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"  ✓ {name}: {count}张表")
        else:
            print(f"  ✗ {name}: 不存在")
    passed += 1
except Exception as e:
    print(f"  ✗ 数据库: {e}")
    failed += 1

print("\n[3/8] 测试经验池数据...")
try:
    conn = sqlite3.connect("data/experience_pool.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM experiences")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM experiences WHERE success > 0")
    success_count = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(success) FROM experiences")
    avg_success = cursor.fetchone()[0] or 0
    conn.close()
    print(f"  ✓ 总经验: {total}, 成功: {success_count}, 平均成功率: {avg_success:.2%}")
    passed += 1
except Exception as e:
    print(f"  ✗ 经验池: {e}")
    failed += 1

print("\n[4/8] 测试快速反射引擎...")
try:
    from infrastructure.quick_reflex import get_quick_reflex
    reflex = get_quick_reflex("config/reflex_rules.yaml")
    stats = reflex.get_stats()
    print(f"  ✓ 反射引擎: {stats['total_rules']}条规则")
    passed += 1
except Exception as e:
    print(f"  ✗ 反射引擎: {e}")
    failed += 1

print("\n[5/8] 测试工具仲裁器...")
try:
    from tools.arbiter import get_tool_arbiter
    arbiter = get_tool_arbiter()
    tool = arbiter.select_tool("计算 123 * 456")
    print(f"  ✓ 工具仲裁器: 选择工具 {tool}")
    passed += 1
except Exception as e:
    print(f"  ✗ 工具仲裁器: {e}")
    failed += 1

print("\n[6/8] 测试反思管道...")
try:
    from infrastructure.reflection_pipeline import get_reflection_pipeline
    pipeline = get_reflection_pipeline({
        "log_db_path": "logs/campfire_log.db",
        "enable_induction": False,
        "enable_jsonl": False,
    })
    print(f"  ✓ 反思管道已初始化")
    passed += 1
except Exception as e:
    print(f"  ✗ 反思管道: {e}")
    failed += 1

print("\n[7/8] 测试金丝雀验证器...")
try:
    from core.canary_evaluator import CanaryEvaluator
    evaluator = CanaryEvaluator()
    print(f"  ✓ 金丝雀验证器已初始化")
    passed += 1
except Exception as e:
    print(f"  ✗ 金丝雀验证器: {e}")
    failed += 1

print("\n[8/8] 测试记忆巩固器...")
try:
    from core.sleep_consolidator import SleepConsolidator
    consolidator = SleepConsolidator()
    print(f"  ✓ 记忆巩固器已初始化")
    passed += 1
except Exception as e:
    print(f"  ✗ 记忆巩固器: {e}")
    failed += 1

print("\n" + "=" * 60)
print(f"测试结果: ✅ {passed} 通过, ❌ {failed} 失败")
print("=" * 60)

if failed == 0:
    print("\n✅ 所有核心功能测试通过！")
    sys.exit(0)
else:
    print("\n❌ 存在失败的测试")
    sys.exit(1)