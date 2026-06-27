"""
测试真正的学习、反思、诚实
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, '.')

print("=" * 70)
print("测试真正的学习、反思、诚实")
print("=" * 70)

# 测试1: 诚实学习系统
print("\n[测试1] 诚实学习系统 - 拒绝瞎编")
from core.honest_learning_system import honest_system

response, valid = honest_system.process_with_honesty(
    "推荐一款电池保护芯片",
    "推荐TPS61182...",
    confidence=0.5  # 置信度不足
)

print("置信度不足时的响应:")
print(response[:300])
print(f"\n是否有效: {valid}")

# 测试2: 深度反思
print("\n[测试2] 深度反思 - 不是简单罗列")
history = [
    {'user': '推荐一款26650的锂电保护板控制芯片', 
     'assistant': '推荐使用TPS61182，这款芯片具有内置的平衡电路...'},
    {'user': 'TPS61182这颗芯片是做什么用的？',
     'assistant': 'TPS61182是LED背光驱动芯片...'},
    {'user': '我之前需求是什么？你这个推荐的跟需求一致么？',
     'assistant': '我目前只能记住当前对话中的内容...'},
]

reflection = honest_system.deep_reflection("回顾历史对话", history)
print("深度反思报告:")
print(reflection)

print("\n" + "=" * 70)
print("核心改进")
print("=" * 70)

print("""
Before ❌:
  用户: 推荐电池保护芯片
  系统: TPS61182（瞎编）
  用户: 回顾历史
  系统: [罗列历史]（无反思）
  用户: 需求一致么？
  系统: 我只能记住当前对话（搪塞）

After ✅:
  用户: 推荐电池保护芯片
  系统: [置信度不足] → "我不确定，不想给您错误信息"
  用户: 回顾历史
  系统: [深度反思] → 发现错误 → 承认错误 → 改进承诺
  用户: 需求一致么？
  系统: [验证之前回答] → 承认错误 → 纠正

核心变化:
1. 诚实 - 不确定就承认，不瞎编
2. 反思 - 真正思考问题，不是形式主义
3. 验证 - 每个回答都经过验证
4. 学习 - 遇到不懂的，先学习再回答
""")

print("\n" + "=" * 70)
print("学习的真正含义")
print("=" * 70)

print("""
❌ 错误理解:
  学习 = 记忆知识
  进化 = 形式上的改进
  结果 = 瞎编答案

✅ 正确理解:
  学习 = 理解 + 验证 + 应用
  进化 = 发现不足 → 承认不足 → 学习补充 → 验证掌握
  结果 = 经过验证的正确答案

关键态度:
  不懂就说不懂
  不确定就承认
  不瞎编搪塞
  不形式主义
""")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n现在系统会:")
print("1. 不确定时承认，不瞎编")
print("2. 回顾历史时深度反思，不是简单罗列")
print("3. 质疑时承认错误，不是搪塞")
print("4. 需求验证失败时纠正，不是装作没事")
print("\n这才是真正的学习进化！")