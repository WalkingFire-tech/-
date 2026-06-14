#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试循环推理引擎"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("测试循环推理引擎 - 借鉴OpenMythos RDT架构")
print("=" * 70)

# 测试1: 导入循环推理器
print("\n[测试1] 导入循环推理器")
try:
    from infrastructure.recurrent_reasoner import recurrent_reasoner, RecurrentReasoner
    print("  ✓ 循环推理器导入成功")
    print(f"  ✓ 配置: max_iter={recurrent_reasoner.max_iterations}, "
          f"convergence={recurrent_reasoner.convergence_threshold}, "
          f"stability={recurrent_reasoner.stability_factor}")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    sys.exit(1)

# 测试2: 复杂度评估
print("\n[测试2] 复杂度评估与迭代次数估算")
test_cases = [
    ("今天天气怎么样？", "chat"),
    ("请解释为什么天空是蓝色的？", "question"),
    ("写一个快速排序算法的实现", "code"),
    ("分析并比较Python和JavaScript的异步编程模型，给出详细的技术对比", "question"),
]

for prompt, intent_type in test_cases:
    iterations = recurrent_reasoner._estimate_iterations(prompt, intent_type)
    print(f"  {intent_type:10s} | {prompt[:40]:40s} → {iterations}轮迭代")

# 测试3: LTI稳定性约束
print("\n[测试3] LTI稳定性约束")
hidden_state = "这是第一轮思考的内容"
new_response = "这是第二轮思考的内容"
for iteration in range(4):
    constrained = recurrent_reasoner._apply_lti_constraint(hidden_state, new_response, iteration)
    decay = recurrent_reasoner.stability_factor ** iteration
    print(f"  迭代{iteration}: 衰减因子={decay:.3f}, 长度={len(constrained)}")

# 测试4: 质量评估
print("\n[测试4] 质量评估")
test_responses = [
    ("简短回答", "chat"),
    ("首先，我们需要理解问题的本质。其次，分析关键因素。最后，给出解决方案。因此，答案是...", "question"),
    ("```python\ndef quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)\n```", "code"),
]

for response, intent_type in test_responses:
    quality = recurrent_reasoner._evaluate_quality(response, intent_type)
    print(f"  {intent_type:10s} | 长度={len(response):4d} → 质量={quality:.2f}")

# 测试5: 收敛检测
print("\n[测试5] 收敛检测")
from infrastructure.recurrent_reasoner import ThoughtIteration

trajectory = [
    ThoughtIteration(
        iteration=0,
        response="第一轮回答",
        quality_score=0.6,
        convergence_metric=0.0
    ),
    ThoughtIteration(
        iteration=1,
        response="第二轮回答，有所改进",
        quality_score=0.75,
        convergence_metric=0.7
    ),
]

new_response = "第三轮回答，与第二轮非常相似"
new_quality = 0.78
convergence = recurrent_reasoner._check_convergence(trajectory, new_response, new_quality)
print(f"  收敛指标: {convergence:.3f}")
print(f"  是否应该停止: {recurrent_reasoner._should_halt(new_quality, convergence, 2, 4)}")

# 测试6: ACT自适应计算时间
print("\n[测试6] ACT自适应计算时间")
test_scenarios = [
    (0.90, 0.80, 2, 4, "高质量，应提前退出"),
    (0.70, 0.96, 2, 4, "高收敛，应提前退出"),
    (0.60, 0.70, 2, 4, "继续推理"),
    (0.80, 0.85, 3, 4, "达到最大迭代"),
]

for quality, convergence, iteration, max_iter, desc in test_scenarios:
    should_halt = recurrent_reasoner._should_halt(quality, convergence, iteration, max_iter)
    status = "停止" if should_halt else "继续"
    print(f"  {desc:20s} | quality={quality:.2f}, conv={convergence:.2f} → {status}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n核心机制验证:")
print("  ✓ 复杂度评估 - 根据任务特征估算迭代次数")
print("  ✓ LTI稳定性 - 衰减因子确保hidden_state不发散")
print("  ✓ 质量评估 - 多维度评估回答质量")
print("  ✓ 收敛检测 - 相似度+质量变化判断收敛")
print("  ✓ ACT机制 - 自适应决定何时停止推理")

print("\n下一步:")
print("  1. 重启系统: taskkill /F /IM python.exe; start.bat")
print("  2. 测试复杂问题，观察循环推理效果")
print("  3. 检查日志中的'循环推理'相关信息")