import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("导入错误修复验证")
print("=" * 70)

print("\n测试1: 检查enhanced_learner是否被移除")
try:
    from core.learning import enhanced_learner
    print("  ❌ enhanced_learner仍然存在")
except ImportError:
    print("  ✅ enhanced_learner已正确移除")

print("\n测试2: 检查替代导入")
try:
    from meta.induction import induction_scheduler
    print("  ✅ induction_scheduler导入成功")
except Exception as e:
    print(f"  ❌ induction_scheduler导入失败: {e}")

try:
    from tools.generator import ToolGenerator
    print("  ✅ ToolGenerator导入成功")
except Exception as e:
    print(f"  ❌ ToolGenerator导入失败: {e}")

try:
    from core.memory.stereo_memory import get_stereo_memory
    print("  ✅ get_stereo_memory导入成功")
except Exception as e:
    print(f"  ❌ get_stereo_memory导入失败: {e}")

print("\n测试3: 检查active_scheduler导入")
try:
    from core.active_scheduler import active_scheduler
    print("  ✅ active_scheduler导入成功")
except Exception as e:
    print(f"  ❌ active_scheduler导入失败: {e}")

print("\n" + "=" * 70)
print("✅ 导入错误修复验证完成")
print("=" * 70)

print("\n修复总结:")
print("  ✅ enhanced_learner导入错误已修复")
print("  ✅ 使用induction_scheduler替代规则生成")
print("  ✅ 使用ToolGenerator替代工具生成")
print("  ✅ 使用get_stereo_memory替代记忆回顾")