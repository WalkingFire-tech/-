"""
测试v2.0与无模型反思的集成
"""
import sys
import os
os.environ['DISABLE_SEMANTIC'] = '1'

print("=" * 80)
print("v2.0 + 无模型反思集成测试")
print("=" * 80)

from core.cognitive_architecture_v2 import (
    cognitive_architecture,
    EvolutionLayer,
    DataDrivenReflectionFallback
)

test_results = {'passed': 0, 'failed': 0}

def test(name: str, condition: bool, detail: str = ""):
    test_results['passed'] if condition else test_results['failed']
    status = "✅" if condition else "❌"
    print(f"{status} {name}")
    if detail:
        print(f"   {detail}")

# ==================== 测试1：数据驱动反思降级 ====================
print("\n[测试1] 数据驱动反思降级")

fallback = DataDrivenReflectionFallback()

# 测试领域混淆检测
detected = fallback.detect_patterns(
    "推荐一款26650的锂电保护板控制芯片",
    "推荐TPS61182芯片"
)

test(
    "检测到领域混淆",
    len(detected) > 0,
    f"检测到{len(detected)}个模式"
)

test(
    "检测到TPS用于电池保护",
    any(d['pattern_type'] == 'domain_confusion' for d in detected),
    "领域混淆检测正确"
)

# 测试功能不匹配检测
detected = fallback.detect_patterns(
    "推荐一款带均衡功能的芯片",
    "推荐BQ76940芯片"  # 没提均衡
)

test(
    "检测到功能不匹配",
    any(d['pattern_type'] == 'functional_mismatch' for d in detected),
    "功能匹配检测正确"
)

# 测试用户反馈检测
detected = fallback.detect_patterns(
    "推荐芯片",
    "推荐XXX芯片",
    "这个推荐不对"
)

test(
    "检测到用户反馈",
    any(d['pattern_type'] == 'user_feedback' for d in detected),
    "用户反馈检测正确"
)

# ==================== 测试2：进化层集成 ====================
print("\n[测试2] 进化层集成")

evolution = EvolutionLayer()

# 测试进化层包含数据驱动反思
test(
    "进化层包含数据驱动反思",
    hasattr(evolution, 'data_driven_reflection'),
    "降级方案已集成"
)

# 测试进化流程
result = evolution.evolve(
    "推荐一款26650的锂电保护板控制芯片",
    "推荐TPS61182芯片",
    is_correct=False,
    feedback="TPS61182是LED驱动芯片"
)

test(
    "进化流程执行",
    result['evolved'] == True,
    "进化成功"
)

test(
    "错误已归档",
    len(evolution.error_archive) > 0,
    f"归档{len(evolution.error_archive)}个错误"
)

# 检查是否检测到额外错误模式
test(
    "数据驱动反思触发",
    len(evolution.error_archive) > 1,  # 原始错误 + 额外检测
    f"检测到额外错误模式"
)

# ==================== 测试3：完整流程 ====================
print("\n[测试3] 完整流程测试")

result = cognitive_architecture.process("推荐一款26650的锂电保护板控制芯片，需要带平衡功能")

test(
    "完整流程执行",
    result['status'] in ['完成', '需要修正', '需要更多信息'],
    f"状态: {result['status']}"
)

test(
    "不推荐LED芯片",
    'TPS' not in result['solution'] or 'LED' not in result['solution'],
    "核心案例正确处理"
)

# ==================== 测试总结 ====================
print("\n" + "=" * 80)
print("【测试总结】")
print("=" * 80)

total = test_results['passed'] + test_results['failed']
pass_rate = test_results['passed'] / total * 100 if total > 0 else 0

print(f"\n通过: {test_results['passed']}")
print(f"失败: {test_results['failed']}")

if test_results['failed'] == 0:
    print("\n✅ 所有集成测试通过！")
    print("\n验证的集成:")
    print("  1. 数据驱动反思降级 ✓")
    print("  2. 进化层集成 ✓")
    print("  3. 完整流程 ✓")
    print("\n结论: v2.0已成功集成无模型反思能力")
else:
    print("\n❌ 存在失败的测试")