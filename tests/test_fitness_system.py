"""
测试适应度评估系统
验证客观分+主观分的重构效果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.fitness_evaluator import fitness_evaluator, FitnessScore
from infrastructure.feedback_classifier import feedback_classifier, FeedbackType
from infrastructure.fact_store import fact_store
from infrastructure.triple_extractor import triple_extractor
from infrastructure.fitness_config import FitnessConfig


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_fact_store():
    """测试事实锚点库"""
    print_separator("1. 测试事实锚点库")
    
    # 获取统计
    stats = fact_store.get_stats()
    print(f"总断言数: {stats['total']}")
    print(f"正向断言: {stats['positive']}")
    print(f"否定断言: {stats['negations']}")
    print(f"纠错记录: {stats['corrections']}")
    
    # 查询冰雹相关断言
    print("\n冰雹相关断言:")
    assertions = fact_store.get_assertions("为什么会有冰雹")
    for a in assertions[:5]:
        print(f"  - ({a['subject']}, {a['predicate']}, {a['object']})")
    
    # 查询否定断言
    print("\n否定断言（错误示例）:")
    negations = fact_store.get_negations("为什么会有冰雹")
    for n in negations:
        print(f"  ✗ ({n['subject']}, {n['predicate']}, {n['object']})")


def test_triple_extractor():
    """测试三元组提取器"""
    print_separator("2. 测试三元组提取器")
    
    test_texts = [
        "冰雹的形成是由于过冷水滴在强对流云中反复冻结",
        "水蒸气遇冷会凝华成冰晶",
        "高空温度升高，冰晶开始融化成水滴",
        "冰雹发生在天气晴朗的时候",
        "圆周率π约等于3.14159"
    ]
    
    for text in test_texts:
        print(f"\n文本: {text[:50]}...")
        triples = triple_extractor.extract(text)
        print(f"提取到 {len(triples)} 个三元组:")
        for t in triples[:3]:
            print(f"  - ({t.subject}, {t.predicate}, {t.object})")


def test_fitness_evaluator():
    """测试适应度评估器"""
    print_separator("3. 测试适应度评估器")
    
    test_cases = [
        {
            "question": "为什么会有冰雹",
            "response": "冰雹的形成是由于过冷水滴在强对流云中反复冻结。水蒸气会凝华成冰晶。",
            "feedback": 0,
            "intent": "question"
        },
        {
            "question": "为什么会有冰雹",
            "response": "冰雹发生时天气晴朗。水蒸气变成冰晶叫做露点或冰点。",
            "feedback": 0,
            "intent": "question"
        },
        {
            "question": "你觉得今天天气怎么样",
            "response": "今天天气不错，适合出门散步。",
            "feedback": 1,
            "intent": "chat"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case['question'][:30]}...")
        
        score = fitness_evaluator.evaluate(
            question=case['question'],
            response=case['response'],
            user_feedback=case['feedback'],
            intent_type=case['intent']
        )
        
        print(f"  最终分: {score.final_score:.1f}")
        print(f"  客观分: {score.objective_score:.1f}")
        print(f"  主观分: {score.subjective_score:.1f}")
        print(f"  事实性问题: {score.is_factual_question}")
        print(f"  匹配详情: {score.match_details}")


def test_feedback_classifier():
    """测试反馈分类器"""
    print_separator("4. 测试反馈分类器")
    
    test_messages = [
        "第2条错误：露点概念用错，应该是凝华",
        "不对，高空温度不会升高，而是降低",
        "👍 回答得很好",
        "点踩，这个回答没用",
        "能详细解释一下吗",
        "今天天气不错"
    ]
    
    for msg in test_messages:
        fb_type = feedback_classifier.classify(msg)
        result = feedback_classifier.process_feedback(msg)
        print(f"\n消息: {msg[:30]}...")
        print(f"  类型: {fb_type.value}")
        print(f"  适应度调整: {result['fitness_delta']}")
        print(f"  更新事实库: {result['should_update_facts']}")


def test_shadow_mode():
    """测试影子模式"""
    print_separator("5. 测试影子模式")
    
    # 启用影子模式
    FitnessConfig.enable_shadow()
    print(f"影子模式: {FitnessConfig.SHADOW_MODE_ENABLED}")
    print(f"旧版模式: {FitnessConfig.USE_LEGACY_FITNESS}")
    
    # 测试对比
    question = "为什么会有冰雹"
    response = "冰雹由过冷水滴在上升气流中反复冻结形成"
    
    # 新版评分
    new_score = fitness_evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=0,
        intent_type="question"
    )
    
    # 旧版评分
    FitnessConfig.enable_legacy()
    legacy_score = fitness_evaluator.evaluate(
        question=question,
        response=response,
        user_feedback=0,
        intent_type="question"
    )
    
    print(f"\n问题: {question}")
    print(f"回答: {response[:50]}...")
    print(f"\n新版评分: {new_score.final_score:.1f}")
    print(f"  - 客观分: {new_score.objective_score:.1f}")
    print(f"  - 主观分: {new_score.subjective_score:.1f}")
    print(f"\n旧版评分: {legacy_score.final_score:.1f}")
    print(f"\n差异: {abs(new_score.final_score - legacy_score.final_score):.1f}")


def main():
    print("\n" + "=" * 70)
    print("  🧪 适应度评估系统测试")
    print("=" * 70)
    
    test_fact_store()
    test_triple_extractor()
    test_fitness_evaluator()
    test_feedback_classifier()
    test_shadow_mode()
    
    print("\n" + "=" * 70)
    print("  ✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()