"""
演示动态学习机制
展示系统如何通过用户纠错学习新知识
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_integrated import AlliancePioneer

print("\n" + "=" * 70)
print("  演示：系统动态学习新知识")
print("=" * 70)

pioneer = AlliancePioneer()

# 场景1: 问一个系统不知道的问题
print("\n【场景1】问一个新问题（系统不知道）")
question1 = "什么是强化学习?"
print(f"问题: {question1}")

result1 = pioneer.process_question(question1, enable_metacognition=False)
print(f"系统回答: {result1['response'][:80]}...")
print(f"客观分: {result1['objective_score']:.1f} (低分，因为没知识)")

# 场景2: 用户纠错，教系统新知识
print("\n【场景2】用户纠错，教系统新知识")
correction = "不对，强化学习是机器学习的一种方法，通过与环境交互、试错来学习最优策略，广泛应用于游戏AI、机器人控制等领域"

print(f"用户纠错: {correction[:50]}...")

feedback_result = pioneer.handle_feedback(
    question=question1,
    response=result1['response'],
    feedback=correction,
    objective_score=result1['objective_score']
)

print(f"纠错结果: {'成功' if feedback_result.get('correction_result', {}).get('success') else '失败'}")

# 场景3: 再次问同样的问题
print("\n【场景3】再次问同样的问题（系统已学会）")
result2 = pioneer.process_question(question1, enable_metacognition=False)
print(f"系统回答: {result2['response'][:100]}...")
print(f"客观分: {result2['objective_score']:.1f} (高分，因为有知识了)")
print(f"使用事实: {result2['facts_used']}条")

# 场景4: 问另一个新问题
print("\n【场景4】再教系统一个新知识")
question2 = "什么是自然语言处理?"
print(f"问题: {question2}")

result3 = pioneer.process_question(question2, enable_metacognition=False)
print(f"系统回答: {result3['response'][:80]}...")

correction2 = "不对，自然语言处理(NLP)是AI的一个分支，让计算机理解、生成人类语言，应用包括翻译、对话系统、文本分析"
print(f"用户纠错: {correction2[:50]}...")

pioneer.handle_feedback(
    question=question2,
    response=result3['response'],
    feedback=correction2,
    objective_score=result3['objective_score']
)

# 场景5: 查看事实库增长
print("\n【场景5】查看事实库增长")
stats = pioneer.fact_store.get_statistics()
print(f"事实库统计:")
print(f"  总断言: {stats['total']}条")
print(f"  有效断言: {stats['active']}条")
print(f"  种子数据: {stats['seeds']}条")
print(f"  用户添加: {stats['total'] - stats['seeds']}条")

print("\n" + "=" * 70)
print("✅ 演示完成：系统通过用户纠错学会了新知识")
print("=" * 70)
print("\n关键点:")
print("  1. 种子知识只是初始储备，不是固定的")
print("  2. 用户纠错会自动更新事实库")
print("  3. 系统会记住学到的知识")
print("  4. 知识可以被覆盖和更新")