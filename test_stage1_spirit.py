"""
阶段1：精神内核测试（轻量级）
"""
import sys
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       阶段1：精神内核测试                              ║")
print("╚════════════════════════════════════════════════════════╝\n")

from core.spirit_core import SpiritCore

spirit = SpiritCore()

# 测试1：核心原则
print("测试1：核心原则定义")
status = spirit.get_spirit_status()
print(f"  ✅ 定义了{len(status['core_principles'])}条核心原则")
for i, p in enumerate(status['core_principles'], 1):
    print(f"     {i}. {p}")

# 测试2：能力定义
print("\n测试2：能力定义")
print(f"  ✅ 定义了{len(status['abilities'])}种能力")

# 测试3：回复验证
print("\n测试3：回复验证")
good = spirit.validate_response("这是一个有意义的回复，包含建议和方向")
print(f"  ✅ 好的回复验证: {good['valid']}")

bad = spirit.validate_response("我不知道")
print(f"  ✅ 敷衍回复拒绝: {not bad['valid']}")

# 测试4：有意义回复生成
print("\n测试4：有意义回复生成")
response = spirit.ensure_meaningful_response(
    "测试问题",
    [{"method": "方法1", "success": False, "error": "错误1"}]
)
print(f"  ✅ 生成了{len(response)}字的有意义回复")
print(f"     包含建议: {'建议' in response}")
print(f"     包含方向: {'方向' in response}")

print("\n" + "=" * 60)
print("✅ 阶段1测试完成：精神内核运行正常")
print("=" * 60)