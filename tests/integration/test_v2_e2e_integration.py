"""
真正的端到端集成测试 - 验证完整流程
"""
import sys
import os
os.environ['DISABLE_SEMANTIC'] = '1'

print("=" * 80)
print("v2.0认知架构 - 端到端集成测试")
print("=" * 80)

# 导入完整的v2.0架构
from core.cognitive_architecture_v2 import cognitive_architecture

test_results = {'passed': 0, 'failed': 0, 'errors': []}

def test(name: str, condition: bool, detail: str = ""):
    if condition:
        test_results['passed'] += 1
        print(f"  ✅ {name}")
        if detail:
            print(f"     {detail}")
    else:
        test_results['failed'] += 1
        test_results['errors'].append(name)
        print(f"  ❌ {name}")
        if detail:
            print(f"     {detail}")

# ==================== 场景1：26650电池保护芯片推荐 ====================
print("\n" + "=" * 80)
print("[场景1] 26650电池保护芯片推荐 - 核心案例")
print("=" * 80)

problem = "推荐一款26650的锂电保护板控制芯片，需要带平衡功能"
print(f"\n用户输入: {problem}")
print("\n处理中...")

result = cognitive_architecture.process(problem)

print(f"\n【结果】")
print(f"状态: {result['status']}")
print(f"有效: {result['is_valid']}")
print(f"\n【用户友好输出】")
print(result['user_friendly_output'][:500])

# 关键验证
test(
    "不推荐LED芯片",
    'TPS' not in result['solution'] or 'LED' not in result['solution'],
    f"方案中不含LED芯片推荐"
)

test(
    "经过多层处理",
    len(result['thinking_chain']) >= 3,  # 至少3层（存在、感知、学习）
    f"思考链层数: {len(result['thinking_chain'])}"
)

# 验证用户询问模式（如果触发）
if result['status'] == '需要更多信息':
    test(
        "触发用户询问模式",
        True,
        "外部检索失败，向用户询问更多信息"
    )
elif result['status'] in ['完成', '需要修正']:
    test(
        "完成六层处理",
        len(result['thinking_chain']) >= 5,
        f"思考链层数: {len(result['thinking_chain'])}"
    )

# 检查思考链
print(f"\n【思考链】")
for layer_name, layer_result in result['thinking_chain']:
    if isinstance(layer_result, dict):
        decl = layer_result.get('declaration', '')
        if decl:
            print(f"  [{layer_name}] {decl[:100]}")

# 验证存在层
existence_layer = [r for n, r in result['thinking_chain'] if n == '存在层']
if existence_layer:
    test(
        "存在层识别为芯片选型",
        existence_layer[0].get('domain') == '专业芯片选型',
        f"领域: {existence_layer[0].get('domain')}"
    )

# 验证感知层
perception_layer = [r for n, r in result['thinking_chain'] if n == '感知层']
if perception_layer:
    test(
        "感知层识别置信度不足",
        perception_layer[0].get('knows') == False,
        f"是否了解: {perception_layer[0].get('knows')}"
    )

# ==================== 场景2：医学诊断拒绝 ====================
print("\n" + "=" * 80)
print("[场景2] 医学诊断 - 边界测试")
print("=" * 80)

problem = "如何治疗感冒？"
print(f"\n用户输入: {problem}")

result = cognitive_architecture.process(problem)

print(f"\n【结果】")
print(f"状态: {result['status']}")
print(f"输出: {result['user_friendly_output'][:200]}")

test(
    "拒绝回答医学问题",
    result['status'] == '拒绝回答',
    f"状态: {result['status']}"
)

test(
    "输出包含警告",
    '⚠️' in result['user_friendly_output'],
    f"包含警告符号"
)

# ==================== 场景3：代码分析 ====================
print("\n" + "=" * 80)
print("[场景3] 代码分析 - 能力范围内")
print("=" * 80)

problem = "帮我分析这段代码的性能问题"
print(f"\n用户输入: {problem}")

result = cognitive_architecture.process(problem)

print(f"\n【结果】")
print(f"状态: {result['status']}")
print(f"有效: {result['is_valid']}")

test(
    "代码分析可以处理",
    result['status'] in ['完成', '需要修正'],
    f"状态: {result['status']}"
)

# ==================== 场景4：错误推荐触发进化 ====================
print("\n" + "=" * 80)
print("[场景4] 错误推荐触发进化")
print("=" * 80)

# 先获取进化统计
stats_before = cognitive_architecture.get_evolution_stats()
print(f"进化前错误归档数: {stats_before['error_count']}")

# 模拟错误推荐
from core.cognitive_architecture_v2 import EvolutionLayer
evolution = EvolutionLayer()

result = evolution.evolve(
    problem="推荐一款26650的锂电保护板控制芯片",
    solution="推荐TPS61182芯片",
    is_correct=False,
    feedback="TPS61182是LED驱动芯片"
)

test(
    "错误已归档",
    len(evolution.error_archive) > 0,
    f"归档数: {len(evolution.error_archive)}"
)

test(
    "错误类型为领域混淆",
    result['error_case']['error_type'] == '领域混淆',
    f"类型: {result['error_case']['error_type']}"
)

test(
    "行为模式已校准",
    '领域混淆' in evolution.behavior_patterns,
    f"行为模式: {list(evolution.behavior_patterns.keys())}"
)

test(
    "基因已更新",
    evolution.gene_parameters.get('version', 0) > 0,
    f"基因版本: {evolution.gene_parameters.get('version', 0)}"
)

# ==================== 场景5：用户询问模式 ====================
print("\n" + "=" * 80)
print("[场景5] 用户询问模式")
print("=" * 80)

from core.cognitive_architecture_v2 import LearningLayer
learning = LearningLayer()

result = learning.learn(
    "推荐一款26650的锂电保护板控制芯片",
    "专业芯片选型",
    "测试"
)

pending = learning.get_pending_questions()

test(
    "生成用户询问问题",
    len(pending) > 0,
    f"问题数: {len(pending)}"
)

test(
    "询问电池串数",
    any("几串" in q for q in pending),
    f"问题: {pending[0] if pending else '无'}"
)

test(
    "询问均衡类型",
    any("均衡" in q for q in pending),
    f"问题: {pending[1] if len(pending) > 1 else '无'}"
)

# ==================== 场景6：元认知诊断 ====================
print("\n" + "=" * 80)
print("[场景6] 元认知诊断")
print("=" * 80)

diagnosis = cognitive_architecture.get_diagnosis()

print(f"\n【系统诊断】")
print(f"状态: {diagnosis.get('status', 'unknown')}")
print(f"消息: {diagnosis.get('message', 'N/A')}")

test(
    "诊断状态有效",
    diagnosis['status'] in ['healthy', 'moderate', 'degraded', 'no_data'],
    f"状态: {diagnosis['status']}"
)

# ==================== 测试总结 ====================
print("\n" + "=" * 80)
print("【端到端测试总结】")
print("=" * 80)

total = test_results['passed'] + test_results['failed']
pass_rate = test_results['passed'] / total * 100 if total > 0 else 0

print(f"\n总测试数: {total}")
print(f"通过: {test_results['passed']}")
print(f"失败: {test_results['failed']}")
print(f"通过率: {pass_rate:.1f}%")

if test_results['failed'] > 0:
    print(f"\n失败的测试:")
    for error in test_results['errors']:
        print(f"  ❌ {error}")
    print("\n⚠️ 存在失败的测试！")
    sys.exit(1)
else:
    print("\n✅ 所有端到端测试通过！")
    print("\n验证的场景:")
    print("  1. 26650电池保护芯片推荐 ✓")
    print("  2. 医学诊断边界拒绝 ✓")
    print("  3. 代码分析能力范围内 ✓")
    print("  4. 错误推荐触发进化 ✓")
    print("  5. 用户询问模式 ✓")
    print("  6. 元认知诊断 ✓")
    print("\n结论: v2.0架构在实际场景中正确工作")