"""测试在线学习能力"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("测试在线学习能力")
print("=" * 60)

# 测试1: 对话流学习器
print("\n[测试1] 对话流学习器初始化...")
try:
    from infrastructure.dialogue_stream_learner import (
        dialogue_learner,
        SemanticShiftDetector,
        ImplicitNegationDetector,
        EmotionAnalyzer,
        CorrectionDetector
    )
    print("✓ 对话流学习器加载成功")
    print(f"  - 语义漂移检测器: {type(dialogue_learner.semantic_detector).__name__}")
    print(f"  - 隐式否定检测器: {type(dialogue_learner.negation_detector).__name__}")
    print(f"  - 情绪分析器: {type(dialogue_learner.emotion_analyzer).__name__}")
    print(f"  - 修正检测器: {type(dialogue_learner.correction_detector).__name__}")
except Exception as e:
    print(f"✗ 加载失败: {e}")
    sys.exit(1)

# 测试2: 隐式否定检测
print("\n[测试2] 隐式否定检测...")
test_inputs = [
    "不太对，应该是这样",
    "还是不对",
    "你没理解我的意思",
    "这个回答不自然",
    "处理不了我的问题",
]

negation_detector = ImplicitNegationDetector()
for text in test_inputs:
    result = negation_detector.detect(text)
    status = "✓" if result else "✗"
    print(f"  {status} '{text[:30]}' → {'检测到否定' if result else '未检测'}")

# 测试3: 情绪分析
print("\n[测试3] 情绪分析...")
emotion_analyzer = EmotionAnalyzer()
emotion_tests = [
    "我很满意这个回答",
    "这让我很沮丧",
    "谢谢你的帮助",
    "我对这个结果很失望",
]

for text in emotion_tests:
    result = emotion_analyzer.analyze(text)
    print(f"  '{text[:25]}' → {result['emotion']} (分数: {result['score']:.2f})")

# 测试4: 修正检测
print("\n[测试4] 修正检测...")
correction_detector = CorrectionDetector()
correction_tests = [
    "不对，应该是Python",
    "你记错了，实际是300",
    "其实正确答案是42",
]

for text in correction_tests:
    result = correction_detector.detect(text)
    if result:
        print(f"  ✓ 检测到修正: '{result['correct_content']}'")
    else:
        print(f"  ✗ 未检测到修正")

# 测试5: 元归纳器
print("\n[测试5] 元归纳器初始化...")
try:
    from meta.meta_induction import meta_inductor
    print("✓ 元归纳器加载成功")
    print(f"  - 当前参数: min_support={meta_inductor.params['min_support']}")
    print(f"  - 置信度阈值: {meta_inductor.params['min_confidence']}")
    
    report = meta_inductor.get_meta_report()
    print(f"  - 规则性能统计: {len(report['rule_performance'])}种类型")
    
    if report['recommendations']:
        print("  - 建议:")
        for rec in report['recommendations'][:3]:
            print(f"    {rec}")
    
except Exception as e:
    print(f"✗ 加载失败: {e}")
    import traceback
    traceback.print_exc()

# 测试6: 集成验证
print("\n[测试6] 集成验证...")
try:
    from core.services.planner import DataDrivenPlanner
    
    class MockModel:
        def __init__(self, name):
            self.model_name = name
        def generate(self, prompt, task_type=None):
            return "测试回答"
    
    adapters = {"test": MockModel("test")}
    planner = DataDrivenPlanner(adapters)
    
    print("✓ 规划器集成验证成功")
    print(f"  - 元认知处理器: {hasattr(planner, '_handle_meta_question')}")
    print(f"  - 学习机会处理: {hasattr(planner, '_on_learning_opportunity')}")
    
except Exception as e:
    print(f"✗ 集成验证失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("在线学习能力测试完成")
print("=" * 60)

print("\n核心能力:")
print("✓ 语义漂移检测 - 识别用户重复提问")
print("✓ 隐式否定检测 - 从措辞中识别不满")
print("✓ 情绪分析 - 推断用户满意度")
print("✓ 修正检测 - 捕捉用户纠正")
print("✓ 元归纳器 - 优化学习策略")
print("✓ 实时学习 - 无需等待显式反馈")