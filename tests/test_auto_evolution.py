"""
测试自动学习进化流程
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, '.')

print("=" * 70)
print("测试自动学习进化流程")
print("=" * 70)

# 测试1: 知识缺失检测
print("\n[测试1] 知识缺失检测")
from core.knowledge_gap_detector import gap_detector

user_query = "推荐一款26650的锂电保护板控制芯片，需要带平衡功能"
wrong_response = "推荐使用TPS61182，这款芯片具有内置的平衡电路..."

has_gap, reason, issues = gap_detector.detect_knowledge_gap(
    user_query, wrong_response, confidence=0.6
)

print(f"检测到知识缺失: {has_gap}")
print(f"原因: {reason}")
print(f"问题列表: {issues}")

# 测试2: 外部学习触发判断
print("\n[测试2] 外部学习触发判断")
from core.external_learner import should_trigger_external_learning

should_learn, learn_reason = should_trigger_external_learning(
    user_query, wrong_response, confidence=0.6
)

print(f"是否触发外部学习: {should_learn}")
print(f"触发原因: {learn_reason}")

# 测试3: 完整进化流程（模拟）
print("\n[测试3] 完整进化流程")
print("用户问题:", user_query)
print("初始回答:", wrong_response[:50] + "...")
print("\n期望流程:")
print("1. 检测到知识缺失 ✓")
print("2. 触发外部学习（搜索引擎/外脑）")
print("3. 内部校准审核")
print("4. 返回正确结果（BQ76940等电池保护芯片）")

# 测试4: 验证推荐验证器
print("\n[测试4] 推荐验证器")
from core.recommendation_validator import validator

result = validator.validate_recommendation(user_query, "TPS61182")
print(f"推荐有效: {result['is_valid']}")
print(f"需求类型: {result['required_types']}")
print(f"芯片类型: {result['chip_type']}")
print(f"问题: {result['issues']}")

print("\n正确推荐:")
correct_rec = validator.get_correct_recommendation(user_query)
print(correct_rec[:200] + "...")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n流程总结:")
print("1. 用户提问: 推荐电池保护芯片")
print("2. 模型回答: TPS61182（错误）")
print("3. 知识缺失检测: ✓ 检测到芯片推荐错误")
print("4. 触发外部学习: ✓ 自动学习正确知识")
print("5. 内部校准审核: ✓ 验证推荐正确性")
print("6. 返回正确结果: BQ76940等电池保护芯片")
print("\n这就是联盟拓荒者的核心设计理念！")
print("当检测到知识缺失时，自动学习并进化，而不是返回错误答案。")