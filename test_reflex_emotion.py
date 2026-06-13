"""测试反射引擎和情绪推断"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("反射引擎 + 情绪推断 测试")
print("="*60)

# 1. 反射引擎测试
print("\n1️⃣ 反射引擎测试")
from infrastructure.reflex_engine import reflex_engine

# 测试危险命令拦截
print("\n  测试: 危险命令拦截")
result = reflex_engine.check({"user_input": "rm -rf /"})
if result:
    print(f"  ✅ 拦截成功: {result}")
else:
    print("  ❌ 拦截失败")

# 测试内存保护
print("\n  测试: 内存保护")
result = reflex_engine.check({"memory_percent": 95})
if result:
    print(f"  ✅ 保护触发: {result}")
else:
    print("  ❌ 保护未触发")

# 测试用户挫折响应
print("\n  测试: 用户挫折响应")
result = reflex_engine.check({"recent_failures": 4})
if result:
    print(f"  ✅ 响应触发: {result}")
else:
    print("  ❌ 响应未触发")

# 获取统计
stats = reflex_engine.get_statistics()
print(f"\n  统计: {stats['total_rules']}条规则, {stats['total_triggers']}次触发")

# 2. 情绪推断测试
print("\n2️⃣ 情绪推断测试")
from infrastructure.emotion_inferencer import emotion_inferencer

test_cases = [
    "快帮我解决这个问题！",
    "烦死了，怎么又失败了",
    "谢谢，太棒了！",
    "我不明白这是什么意思",
    "唉，好失望",
]

for text in test_cases:
    result = emotion_inferencer.infer(text)
    print(f"\n  输入: {text[:20]}")
    print(f"  情绪: {result['emotion']}")
    print(f"  耐心: {result['patience']:.2f}")
    print(f"  紧迫度: {result['urgency']:.2f}")
    if result['signals']:
        print(f"  信号: {', '.join(result['signals'])}")

# 3. 用户状态分析
print("\n3️⃣ 用户状态分析")
user_state = emotion_inferencer.get_user_state()
print(f"  整体状态: {user_state['state']}")
print(f"  趋势: {user_state['trend']}")
print(f"  平均耐心: {user_state['patience_avg']}")

print("\n" + "="*60)
print("测试完成！")
print("="*60)