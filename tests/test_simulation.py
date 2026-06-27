"""
功能模块模拟测试
模拟真实场景下的完整交互流程
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from datetime import datetime

print("\n" + "=" * 70)
print("  🎭 功能模块模拟测试")
print("=" * 70)


def simulate_ice_hail_scenario():
    """模拟场景1: 冰雹问题完整流程"""
    print("\n【场景1】冰雹问题完整流程")
    print("-" * 50)
    
    from infrastructure.fitness_evaluator import fitness_evaluator
    from infrastructure.feedback_classifier import feedback_classifier
    from infrastructure.fact_store import fact_store
    from infrastructure.triple_extractor import triple_extractor
    
    # 用户提问
    question = "我问你为什么会有冰雹"
    print(f"\n👤 用户: {question}")
    
    # 系统回答（包含错误）
    wrong_response = """
冰雹的形成是一个复杂且需要特定气象条件的过程。它主要发生在大气中温度较低，同时存在冰晶和雨滴混合的情况下。以下是冰雹形成的详细过程：

1. 云层中的上升气流：首先，冰雹形成于对流云或积雨云中。这些云层通常在夏季和初秋出现，并且天气晴朗。

2. 冰晶的形成：当水蒸气遇冷凝结成小滴时，如果温度足够低（一般低于零度），这些小滴会直接变成冰晶而不是水滴。这种现象称为"露点"或"冰点"。

3. 冰雹核心的形成：在云层底部，由于强烈的上升气流，冰晶不断被带到更高的地方。在这个过程中，如果气温继续降低，冰晶可能会吸收更多的水蒸气并逐渐增长。然而，当这些冰晶到达一定高度时（通常在-10°C到-30°C之间），它们会遇到温度升高，开始融化成水滴。
"""
    
    print(f"\n🤖 系统(错误回答): {wrong_response[:100]}...")
    
    # 评估错误回答
    score_wrong = fitness_evaluator.evaluate(
        question=question,
        response=wrong_response,
        user_feedback=0,
        intent_type="question"
    )
    
    print(f"\n📊 初始评估:")
    print(f"   总分: {score_wrong.final_score:.1f}")
    print(f"   客观分: {score_wrong.objective_score:.1f}")
    print(f"   主观分: {score_wrong.subjective_score:.1f}")
    print(f"   事实性问题: {score_wrong.is_factual_question}")
    
    # 检查是否匹配到否定断言（错误示例）
    if score_wrong.match_details.get('negation_matched'):
        print(f"   ⚠️ 匹配到错误示例！")
    
    # 用户纠错
    correction = """
总体框架大致正确，但存在几处非常明显的科学概念错误和逻辑硬伤。

❌ 主要错误（硬伤）
1. 第2条："露点"或"冰点"概念完全用错
   错误原因：水蒸气直接变成冰晶，在物理上叫做凝华，绝不能用"露点"或"冰点"来称呼。

2. 第3条：温度变化逻辑完全相反（致命硬伤）
   错误原因：在对流层中，高度越高，气温越低。-10℃到-30℃远比0℃要冷，冰晶在这个温度下绝对不会"温度升高"或"融化成水滴"。

3. 第1条："天气晴朗"描述不准确
   错误原因：冰雹发生时天空必定是黑压压的积雨云（雷暴云），伴有狂风暴雨，绝对不是"天气晴朗"。
"""
    
    print(f"\n👤 用户(纠错): {correction[:100]}...")
    
    # 分类反馈
    fb_result = feedback_classifier.process_feedback(correction)
    print(f"\n🔍 反馈分类:")
    print(f"   类型: {fb_result['type']}")
    print(f"   更新事实库: {fb_result['should_update_facts']}")
    print(f"   更新适应度: {fb_result['should_update_fitness']}")
    
    # 如果是纠错，更新事实库
    if fb_result['should_update_facts']:
        print(f"\n💾 更新事实库:")
        
        # 添加纠错断言
        fact_store.add_correction(
            question=question,
            old_subject="水蒸气",
            old_predicate="相变",
            old_obj="露点或冰点",
            new_subject="水蒸气",
            new_predicate="相变",
            new_obj="凝华或冻结核化",
            correction_source="user_correction_detailed"
        )
        print(f"   ✅ 已添加纠错: (水蒸气, 相变, 露点或冰点) → (水蒸气, 相变, 凝华)")
        
        fact_store.add_correction(
            question=question,
            old_subject="冰晶",
            old_predicate="高空温度变化",
            old_obj="温度升高融化",
            new_subject="冰晶",
            new_predicate="高空温度变化",
            new_obj="温度降低继续冻结",
            correction_source="user_correction_detailed"
        )
        print(f"   ✅ 已添加纠错: (冰晶, 高空温度变化, 温度升高融化) → (冰晶, 高空温度变化, 温度降低)")
    
    # 系统重新回答（正确）
    correct_response = """
冰雹的形成，本质上是一种发生在强对流云（积雨云）中的特殊"冰粒生长"过程。它的核心秘密在于强烈的上升气流和云中过冷水的共同作用。

具体形成过程可以分为以下四个关键阶段：

1. 初始"胚胎"形成
在积雨云中，高层温度极低（通常在-10℃到-40℃）。云中的水蒸气会直接凝华成微小的冰晶，或者过冷水滴附着在凝结核上冻结，形成冰雹的"胚胎"。

2. 在云中上下翻滚"滚雪球"
强烈的上升气流将雹胚向上托举，送入富含过冷水滴的云层生长区。雹胚与过冷水滴碰撞时，水滴会瞬间在雹胚表面冻结。

3. 重量超过上升气流承载力
随着冰雹不断长大，其重量最终会超过上升气流所能托举的极限，冰雹便开始下落。

4. 下落至地面
如果冰雹直径足够大，且下落速度快，经过暖区时来不及完全融化，就会以固态形式到达地面。
"""
    
    print(f"\n🤖 系统(正确回答): {correct_response[:100]}...")
    
    # 评估正确回答
    score_correct = fitness_evaluator.evaluate(
        question=question,
        response=correct_response,
        user_feedback=1,  # 用户点赞
        intent_type="question"
    )
    
    print(f"\n📊 重新评估:")
    print(f"   总分: {score_correct.final_score:.1f}")
    print(f"   客观分: {score_correct.objective_score:.1f}")
    print(f"   主观分: {score_correct.subjective_score:.1f}")
    
    # 对比改进
    improvement = score_correct.final_score - score_wrong.final_score
    print(f"\n📈 改进:")
    print(f"   分数提升: {improvement:.1f}")
    
    return True


def simulate_chat_scenario():
    """模拟场景2: 开放性聊天"""
    print("\n【场景2】开放性聊天")
    print("-" * 50)
    
    from infrastructure.fitness_evaluator import fitness_evaluator
    from infrastructure.feedback_classifier import feedback_classifier
    
    # 用户提问
    question = "我们来交谈交谈吧"
    print(f"\n👤 用户: {question}")
    
    # 系统回答
    response = "好的，我们来聊天吧！有什么想聊的话题吗？"
    print(f"\n🤖 系统: {response}")
    
    # 评估
    score = fitness_evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=0,
        intent_type="chat"
    )
    
    print(f"\n📊 评估:")
    print(f"   总分: {score.final_score:.1f}")
    print(f"   客观分: {score.objective_score:.1f}")
    print(f"   主观分: {score.subjective_score:.1f}")
    print(f"   事实性问题: {score.is_factual_question}")
    
    # 用户点赞
    fb_result = feedback_classifier.process_feedback("👍")
    print(f"\n👤 用户: 👍")
    print(f"   反馈类型: {fb_result['type']}")
    print(f"   适应度调整: {fb_result['fitness_delta']}")
    
    # 重新评估
    score_after = fitness_evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=1,
        intent_type="chat"
    )
    
    print(f"\n📊 点赞后评估:")
    print(f"   总分: {score_after.final_score:.1f}")
    
    return True


def simulate_math_scenario():
    """模拟场景3: 数学问题"""
    print("\n【场景3】数学问题")
    print("-" * 50)
    
    from infrastructure.fitness_evaluator import fitness_evaluator
    
    # 用户提问
    question = "圆周率是多少"
    print(f"\n👤 用户: {question}")
    
    # 系统回答
    response = "圆周率π约等于3.14159，是一个无限不循环小数"
    print(f"\n🤖 系统: {response}")
    
    # 评估
    score = fitness_evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=0,
        intent_type="question"
    )
    
    print(f"\n📊 评估:")
    print(f"   总分: {score.final_score:.1f}")
    print(f"   客观分: {score.objective_score:.1f}")
    print(f"   主观分: {score.subjective_score:.1f}")
    print(f"   事实性问题: {score.is_factual_question}")
    
    return True


def simulate_negative_feedback_scenario():
    """模拟场景4: 负面反馈"""
    print("\n【场景4】负面反馈处理")
    print("-" * 50)
    
    from infrastructure.fitness_evaluator import fitness_evaluator
    from infrastructure.feedback_classifier import feedback_classifier
    
    # 用户提问
    question = "为什么会有冰雹"
    print(f"\n👤 用户: {question}")
    
    # 系统回答
    response = "冰雹是因为天气晴朗时水蒸气变成露点形成的"
    print(f"\n🤖 系统: {response}")
    
    # 用户点踩
    print(f"\n👤 用户: 👎 完全错误")
    
    fb_result = feedback_classifier.process_feedback("👎 完全错误")
    print(f"   反馈类型: {fb_result['type']}")
    print(f"   适应度调整: {fb_result['fitness_delta']}")
    
    # 评估
    score = fitness_evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=-1,
        intent_type="question"
    )
    
    print(f"\n📊 评估:")
    print(f"   总分: {score.final_score:.1f}")
    print(f"   客观分: {score.objective_score:.1f}")
    print(f"   主观分: {score.subjective_score:.1f}")
    
    # 检查是否应该触发学习
    from infrastructure.fitness_evaluator import fitness_evaluator
    should_inject, reason = fitness_evaluator.should_inject_knowledge(score)
    
    print(f"\n🔄 知识注入:")
    print(f"   是否触发: {should_inject}")
    print(f"   原因: {reason}")
    
    return True


def simulate_fact_assertion_matching():
    """模拟场景5: 事实断言匹配"""
    print("\n【场景5】事实断言匹配")
    print("-" * 50)
    
    from infrastructure.fact_store import fact_store
    from infrastructure.triple_extractor import triple_extractor
    
    # 查询冰雹相关断言
    question = "为什么会有冰雹"
    assertions = fact_store.get_assertions(question)
    negations = fact_store.get_negations(question)
    
    print(f"\n📚 事实断言库:")
    print(f"   正向断言: {len(assertions)}条")
    for a in assertions[:3]:
        print(f"   - ({a['subject']}, {a['predicate']}, {a['object'][:20]})")
    
    print(f"\n   否定断言: {len(negations)}条")
    for n in negations[:3]:
        print(f"   ✗ ({n['subject']}, {n['predicate']}, {n['object'][:20]})")
    
    # 测试正确回答
    correct_response = "冰雹由过冷水滴在强对流云中反复冻结形成"
    extracted = triple_extractor.extract(correct_response)
    
    print(f"\n✅ 正确回答测试:")
    print(f"   回答: {correct_response}")
    print(f"   提取三元组: {len(extracted)}个")
    
    # 计算匹配度
    match_rate = triple_extractor.calculate_overlap(extracted, assertions)
    print(f"   匹配度: {match_rate:.2f}")
    
    # 测试错误回答
    wrong_response = "冰雹发生时天气晴朗"
    extracted_wrong = triple_extractor.extract(wrong_response)
    
    print(f"\n❌ 错误回答测试:")
    print(f"   回答: {wrong_response}")
    print(f"   提取三元组: {len(extracted_wrong)}个")
    
    # 检查是否匹配否定断言
    negation_matched = triple_extractor.check_negation_match(extracted_wrong, negations)
    print(f"   匹配否定断言: {negation_matched}")
    
    return True


def main():
    """运行所有模拟场景"""
    scenarios = [
        ("冰雹问题完整流程", simulate_ice_hail_scenario),
        ("开放性聊天", simulate_chat_scenario),
        ("数学问题", simulate_math_scenario),
        ("负面反馈处理", simulate_negative_feedback_scenario),
        ("事实断言匹配", simulate_fact_assertion_matching),
    ]
    
    results = []
    
    for name, func in scenarios:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总
    print("\n" + "=" * 70)
    print("  📊 模拟场景测试结果")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print("\n" + "-" * 70)
    print(f"  总计: {passed}/{total} 通过")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)