"""
最小化端到端测试 - 只测试核心导入
"""

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("联盟拓荒者 - 最小化端到端测试")
print("=" * 60)

tests = []

print("\n[1] 测试L1感知层导入...")
try:
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    print("  ✓ L1PerceptionLayer导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[2] 测试L2学习层导入...")
try:
    from core.layers.l2_learning import L2LearningLayer
    print("  ✓ L2LearningLayer导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[3] 测试反馈回路导入...")
try:
    from core.learning.feedback_loop import LearningFeedbackLoop
    print("  ✓ LearningFeedbackLoop导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[4] 测试工具构建器导入...")
try:
    from core.learning.tool_builder import ToolSelfBuilder
    print("  ✓ ToolSelfBuilder导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[5] 测试快速反射引擎导入...")
try:
    from infrastructure.quick_reflex import get_quick_reflex
    print("  ✓ quick_reflex导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[6] 测试工具仲裁器导入...")
try:
    from tools.arbiter import get_tool_arbiter
    print("  ✓ tool_arbiter导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[7] 测试金丝雀验证器导入...")
try:
    from core.canary_evaluator import CanaryEvaluator
    print("  ✓ CanaryEvaluator导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n[8] 测试记忆巩固器导入...")
try:
    from core.sleep_consolidator import SleepConsolidator
    print("  ✓ SleepConsolidator导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

print("\n" + "=" * 60)
passed = sum(tests)
total = len(tests)
print(f"测试结果: {passed}/{total} 通过")
print("=" * 60)

if passed == total:
    print("\n✅ 所有导入测试通过！")
else:
    print(f"\n❌ {total - passed} 个测试失败")

sys.exit(0 if passed == total else 1)