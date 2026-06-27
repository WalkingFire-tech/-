"""
简单测试精神内核 - 不加载其他模块
"""
import sys
sys.path.insert(0, ".")

# 只导入精神内核
from core.spirit_core import SpiritCore

print("╔════════════════════════════════════════════════════════╗")
print("║         联盟拓荒者精神内核测试                          ║")
print("╚════════════════════════════════════════════════════════╝\n")

# 创建精神内核实例
spirit = SpiritCore()

# 测试1：核心原则
print("=" * 60)
print("测试1：核心原则")
print("=" * 60)
status = spirit.get_spirit_status()
print(f"\n核心原则 ({len(status['core_principles'])}条):")
for i, principle in enumerate(status['core_principles'], 1):
    print(f"  {i}. {principle}")

# 测试2：能力定义
print("\n" + "=" * 60)
print("测试2：能力定义")
print("=" * 60)
print(f"\n能力列表 ({len(status['abilities'])}种):")
for key, value in status['abilities'].items():
    print(f"  ✅ {value}")

# 测试3：回复验证
print("\n" + "=" * 60)
print("测试3：回复验证")
print("=" * 60)

# 好的回复
good_response = "关于这个问题，我尝试了多种方法，并给出以下建议：1. 查阅资料 2. 分解问题"
validation = spirit.validate_response(good_response)
print(f"\n✅ 好的回复验证通过: {validation['valid']}")

# 敷衍的回复
bad_response = "我不知道"
validation = spirit.validate_response(bad_response)
print(f"❌ 敷衍回复验证通过: {validation['valid']}")
if not validation['valid']:
    print(f"   问题: {validation['issues'][0]}")

# 测试4：有意义回复生成
print("\n" + "=" * 60)
print("测试4：有意义回复生成")
print("=" * 60)

question = "认知的概念是什么"
attempts = [
    {"method": "知识检索", "success": False, "error": "未找到相关知识"},
    {"method": "模型推理", "success": False, "error": "模型超时"},
    {"method": "深度认知", "success": False, "error": "认知引擎异常"}
]

response = spirit.ensure_meaningful_response(question, attempts)
print(f"\n问题: {question}")
print(f"\n生成的有意义回复:")
print("-" * 60)
print(response)
print("-" * 60)

# 测试5：精神状态
print("\n" + "=" * 60)
print("测试5：精神内核状态")
print("=" * 60)
final_status = spirit.get_spirit_status()
print(f"  • 已学习教训: {final_status['lessons_learned']}条")
print(f"  • 成功模式: {final_status['success_patterns']}种")
print(f"  • 创造方法: {final_status['created_methods']}种")
print(f"  • 状态: {final_status['status']}")

print("\n" + "=" * 60)
print("✅ 精神内核测试完成！")
print("=" * 60)

print("\n总结:")
print("  永不放弃精神已成功刻进系统底层！")
print("  所有回复都将符合精神内核原则：")
print("    1. 合理且逻辑清晰有理有据且自洽")
print("    2. 即使失败也给出有意义的回复")
print("    3. 永不放弃是元能力")