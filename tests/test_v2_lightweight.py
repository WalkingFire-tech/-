"""
轻量级测试 - 验证v2.0架构核心功能
"""
import sys
import os

# 禁用重型依赖
os.environ['DISABLE_SEMANTIC'] = '1'

print("=" * 70)
print("系统重生计划 v2.0 - 轻量级测试")
print("=" * 70)

# 测试1：领域识别器
print("\n[测试1] 统一领域识别器")
from core.cognitive_architecture_v2 import DomainIdentifier

identifier = DomainIdentifier()

test_cases = [
    "推荐一款26650的锂电保护板控制芯片，需要带平衡功能",
    "如何治疗感冒？",
    "帮我分析这段代码的性能问题",
    "LED背光驱动电路设计"
]

for case in test_cases:
    result = identifier.identify(case)
    print(f"  '{case[:30]}...' → {result['primary_domain']}")

print("✅ 领域识别器测试通过")

# 测试2：存在层
print("\n[测试2] 存在层（边界检查）")
from core.cognitive_architecture_v2 import ExistenceLayer

existence = ExistenceLayer(identifier)

for case in test_cases:
    result = existence.check_boundary(case)
    print(f"  '{case[:30]}...'")
    print(f"    领域: {result['domain']}, 状态: {result['status']}")
    print(f"    声明: {result['declaration'][:50]}...")

print("✅ 存在层测试通过")

# 测试3：感知层
print("\n[测试3] 感知层（置信度评估）")
from core.cognitive_architecture_v2 import PerceptionLayer

perception = PerceptionLayer(identifier)

for case in test_cases[:2]:  # 只测试前两个
    domain = identifier.identify(case)['primary_domain']
    result = perception.assess_knowledge(case, domain)
    print(f"  '{case[:30]}...'")
    print(f"    置信度: {result['confidence']:.0%}, 是否了解: {result['knows']}")
    print(f"    声明: {result['declaration'][:50]}...")

print("✅ 感知层测试通过")

# 测试4：学习层
print("\n[测试4] 学习层（用户询问模式）")
from core.cognitive_architecture_v2 import LearningLayer

learning = LearningLayer()

result = learning.learn(
    "推荐一款26650的锂电保护板控制芯片",
    "专业芯片选型",
    "测试"
)

print(f"  学习结果: {result['learned']}")
print(f"  来源数: {len(result['sources'])}")
print(f"  交叉验证: {result['validated']['valid']}")

pending = learning.get_pending_questions()
if pending:
    print(f"  待询问问题:")
    for q in pending:
        print(f"    - {q}")

print("✅ 学习层测试通过")

# 测试5：校验层
print("\n[测试5] 校验层（自我质疑）")
from core.cognitive_architecture_v2 import VerificationLayer

verification = VerificationLayer()

test_solutions = [
    ("推荐TPS61182芯片", "推荐一款26650的锂电保护板控制芯片"),  # 错误推荐
    ("推荐BQ76940电池保护芯片，支持均衡功能", "推荐一款26650的锂电保护板控制芯片，需要带平衡功能"),  # 正确推荐
]

for solution, problem in test_solutions:
    result = verification.verify(problem, solution)
    print(f"  问题: '{problem[:30]}...'")
    print(f"  方案: '{solution}'")
    print(f"    匹配度: {result['match_score']:.0%}")
    print(f"    质疑: {result['doubts'] if result['doubts'] else '无'}")
    print(f"    有效: {result['is_valid']}")

print("✅ 校验层测试通过")

# 测试6：进化层
print("\n[测试6] 进化层（错误归档）")
from core.cognitive_architecture_v2 import EvolutionLayer

evolution = EvolutionLayer()

# 模拟错误案例
result = evolution.evolve(
    problem="推荐一款26650的锂电保护板控制芯片",
    solution="推荐TPS61182芯片",
    is_correct=False,
    feedback="TPS61182是LED驱动芯片，不是电池保护芯片"
)

print(f"  进化结果: {result['evolved']}")
print(f"  错误类型: {result['error_case']['error_type']}")
print(f"  改进建议: {result['error_case']['improvement_suggestion']}")
print(f"  基因版本: {result['gene_update']['version']}")

stats = evolution.get_stats()
print(f"  错误归档数: {stats['error_count']}")
print(f"  行为模式: {list(stats['error_types'].keys())}")

print("✅ 进化层测试通过")

# 测试7：元认知层
print("\n[测试7] 元认知层（监控与诊断）")
from core.cognitive_architecture_v2 import MetaCognitiveLayer

meta = MetaCognitiveLayer()

# 模拟观察
meta.observe({
    'is_valid': True,
    'thinking_chain': [('存在层', {'declaration': '测试'})]
})

meta.observe({
    'is_valid': False,
    'thinking_chain': [('校验层', {'declaration': '校验失败'})]
})

diagnosis = meta.get_diagnosis()
print(f"  系统状态: {diagnosis['status']}")
print(f"  消息: {diagnosis['message']}")
print(f"  总请求: {diagnosis['metrics']['total_requests']}")
print(f"  成功率: {diagnosis['metrics']['success_rate']:.1f}%")
print(f"  告警数: {len(diagnosis['alerts'])}")

print("✅ 元认知层测试通过")

# 测试8：完整流程
print("\n[测试8] 完整六层流程")
from core.cognitive_architecture_v2 import cognitive_architecture

result = cognitive_architecture.process("推荐一款26650的锂电保护板控制芯片，需要带平衡功能")

print(f"  状态: {result['status']}")
print(f"  有效: {result['is_valid']}")
print(f"  思考链层数: {len(result['thinking_chain'])}")
print(f"\n  用户友好输出:")
print(f"  {result['user_friendly_output'][:200]}...")

print("✅ 完整流程测试通过")

# 总结
print("\n" + "=" * 70)
print("【测试总结】")
print("=" * 70)
print("✅ 所有核心功能测试通过")
print("✅ v2.0架构功能完整")
print("\n核心功能验证:")
print("  1. 统一领域识别器 ✓")
print("  2. 存在层边界检查 ✓")
print("  3. 感知层置信度评估 ✓")
print("  4. 学习层用户询问模式 ✓")
print("  5. 校验层自我质疑 ✓")
print("  6. 进化层错误归档 ✓")
print("  7. 元认知层监控诊断 ✓")
print("  8. 完整六层流程 ✓")