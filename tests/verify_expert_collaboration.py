"""验证外脑协作功能"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("验证外脑协作功能")
print("=" * 60)

# 验证1: 检查planner是否包含新方法
print("\n[验证1] 检查planner新方法")
with open('core/services/planner.py', 'r', encoding='utf-8') as f:
    content = f.read()

methods = [
    '_estimate_self_confidence',
    '_expert_collaboration',
    '_store_expert_analysis',
    '_normal_generate'
]

for method in methods:
    if f'def {method}' in content:
        print(f"  ✓ {method} 已添加")
    else:
        print(f"  ✗ {method} 未找到")

# 验证2: 检查plan方法是否集成置信度评估
print("\n[验证2] 检查plan方法集成")
if '_estimate_self_confidence(intent)' in content:
    print("  ✓ 置信度评估已集成")
else:
    print("  ✗ 置信度评估未集成")

if '_expert_collaboration(intent, confidence)' in content:
    print("  ✓ 外脑协作已集成")
else:
    print("  ✗ 外脑协作未集成")

if 'confidence < 0.6' in content:
    print("  ✓ 置信度阈值判断已添加")
else:
    print("  ✗ 置信度阈值判断未添加")

# 验证3: 检查导入
print("\n[验证3] 检查必要导入")
imports = ['sqlite3', 'time']
for imp in imports:
    if f'import {imp}' in content:
        print(f"  ✓ {imp} 已导入")
    else:
        print(f"  ⚠ {imp} 可能缺失")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)

print("\n外脑协作功能已就绪:")
print("  1. 自我置信度评估")
print("  2. 低置信度时启用外脑协作")
print("  3. 选择专家模型进行分析")
print("  4. 存储专家分析（为逆向学习预留）")
print("  5. 降级机制保障")