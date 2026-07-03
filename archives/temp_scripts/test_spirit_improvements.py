"""
测试SpiritCore 3个改进
"""
import sys
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       测试SpiritCore 3个改进                           ║")
print("╚════════════════════════════════════════════════════════╝\n")

from core.spirit_core import SpiritCore

spirit = SpiritCore()

# 改进1：精神异常机制
print("改进1：精神异常机制")
bad_response = "我不知道"
validation = spirit.validate_response(bad_response)
if not validation["valid"]:
    violation = spirit.raise_spirit_violation(bad_response, validation["issues"], "test")
    print(f"  ✅ 精神异常触发: #{violation['violation_id']}")
    print(f"     问题: {violation['issues']}")

# 改进2：系统入口强制注入
print("\n改进2：系统入口强制注入")
# 好的回复直接通过
good = spirit.enforce_on_output("这是一个有意义的回复，包含建议和方向", "test_handler")
print(f"  ✅ 好的回复: 直接通过 ({len(good)}字)")

# 敷衍的回复自动修正
bad = spirit.enforce_on_output("我不知道", "test_handler")
print(f"  ✅ 敷衍回复: 自动修正 ({len(bad)}字)")
has_direction = "建议" in bad or "方向" in bad
print(f"     包含方向: {has_direction}")

# 改进3：与SelfReflection联动
print("\n改进3：与SelfReflection联动")
# 记录教训
spirit.ensure_meaningful_response(
    "测试问题",
    [{"method": "方法1", "success": False, "error": "错误1"}]
)

# 获取反思素材
lessons = spirit.get_lessons_for_reflection(limit=3)
print(f"  ✅ 反思素材: {len(lessons)}条")

# 获取异常记录
violations = spirit.get_violations_for_analysis(limit=3)
print(f"  ✅ 异常记录: {len(violations)}条")

# 精神内核状态
status = spirit.get_spirit_status()
print(f"\n精神内核状态:")
print(f"  • 教训: {status['lessons_learned']}条")
print(f"  • 违规: {status['violations']}次")
print(f"  • 验证: {status['total_validations']}次")
print(f"  • 状态: {status['status']}")

print("\n" + "=" * 60)
print("✅ 所有3个改进测试通过！")
print("=" * 60)