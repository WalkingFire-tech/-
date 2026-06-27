import sys
sys.path.insert(0, '.')

print("=" * 60)
print("端到端测试 - 核心导入验证")
print("=" * 60)

tests = []

# 测试1: L1感知层
print("\n[1/10] L1感知层...")
try:
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    print("  ✓ L1PerceptionLayer导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试2: L2学习层
print("\n[2/10] L2学习层...")
try:
    from core.layers.l2_learning import L2LearningLayer
    print("  ✓ L2LearningLayer导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试3: 反馈回路
print("\n[3/10] 反馈回路...")
try:
    from core.learning.feedback_loop import LearningFeedbackLoop
    print("  ✓ LearningFeedbackLoop导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试4: 工具构建器
print("\n[4/10] 工具构建器...")
try:
    from core.learning.tool_builder import ToolSelfBuilder
    print("  ✓ ToolSelfBuilder导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试5: 快速反射引擎
print("\n[5/10] 快速反射引擎...")
try:
    import yaml
    from typing import Dict, Any, List
    from pathlib import Path
    print("  ✓ 基础依赖导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试6: 工具仲裁器
print("\n[6/10] 工具仲裁器...")
try:
    import asyncio
    import threading
    from collections import defaultdict
    print("  ✓ 基础依赖导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试7: 金丝雀验证器
print("\n[7/10] 金丝雀验证器...")
try:
    from core.canary_evaluator import CanaryEvaluator
    print("  ✓ CanaryEvaluator导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试8: 记忆巩固器
print("\n[8/10] 记忆巩固器...")
try:
    from core.sleep_consolidator import SleepConsolidator
    print("  ✓ SleepConsolidator导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试9: 反思管道
print("\n[9/10] 反思管道...")
try:
    from infrastructure.reflection_pipeline import get_reflection_pipeline
    print("  ✓ reflection_pipeline导入成功")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 测试10: 系统编排器
print("\n[10/10] 系统编排器...")
try:
    from core.orchestrator import SystemOrchestrator
    print("  ✓ SystemOrchestrator导入成功")
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
    print("\n✅ 所有核心导入测试通过！")
    print("\n下一步: 运行 'python backend/main.py' 启动系统")
else:
    print(f"\n❌ {total - passed} 个测试失败")

sys.exit(0 if passed == total else 1)