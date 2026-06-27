"""快速验证系统"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_integrated import AlliancePioneer

print("\n" + "=" * 60)
print("  快速验证 - 有知识储备后的回答")
print("=" * 60)

pioneer = AlliancePioneer()

# 测试问题
questions = [
    "什么是机器学习?",
    "Python是什么?",
]

for q in questions:
    print(f"\n问题: {q}")
    result = pioneer.process_question(q, enable_metacognition=False)
    print(f"回答: {result['response'][:100]}...")
    print(f"客观分: {result['objective_score']:.1f}")
    print(f"事实数: {result['facts_used']}")

print("\n" + "=" * 60)
print("✅ 验证完成")
print("=" * 60)