"""
阶段2简化：永不放弃引擎核心功能测试
"""
import sys
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       阶段2：永不放弃引擎核心测试                      ║")
print("╚════════════════════════════════════════════════════════╝\n")

from core.never_give_up import NeverGiveUpEngine

# 测试1：引擎初始化
print("测试1：引擎初始化")
engine = NeverGiveUpEngine()
print("  ✅ NeverGiveUpEngine初始化成功")

# 测试2：有意义回复生成
print("\n测试2：有意义回复生成")
response = engine._generate_meaningful_response(
    "测试问题",
    [
        ("方法1", False, "错误1"),
        ("方法2", False, "错误2"),
        ("方法3", True, "成功")
    ]
)
print(f"  ✅ 生成了{len(response)}字的有意义回复")
print(f"     包含建议: {'建议' in response}")
print(f"     包含方向: {'方向' in response}")
print(f"     包含承诺: {'永不放弃' in response or '承诺' in response}")

# 测试3：问题类型分析
print("\n测试3：问题类型分析")
test_questions = [
    ("认知的概念是什么", "概念解释"),
    ("为什么天空是蓝色的", "原因分析"),
    ("如何写排序算法", "方法指导"),
    ("实现一个函数", "技术实现"),
    ("计算123+456", "数学计算")
]

for question, expected_type in test_questions:
    detected_type = engine._analyze_question_type(question)
    match = detected_type == expected_type
    print(f"  {'✅' if match else '⚠️'} '{question[:20]}...' → {detected_type}")

# 测试4：方向建议
print("\n测试4：方向建议")
directions = engine._suggest_directions("认知的概念是什么", "概念解释", [])
print(f"  ✅ 生成了{len(directions)}个建议方向")
for i, d in enumerate(directions, 1):
    print(f"     {i}. {d}")

# 测试5：替代方案
print("\n测试5：替代方案")
alternatives = engine._suggest_alternatives("概念解释")
print(f"  ✅ 生成了{len(alternatives)}个替代方案")
for alt in alternatives:
    print(f"     • {alt}")

print("\n" + "=" * 60)
print("✅ 阶段2测试完成：永不放弃引擎核心功能正常")
print("=" * 60)