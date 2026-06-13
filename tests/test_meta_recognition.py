"""测试元认知意图识别（简化版）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.intent_parser import IntentParser

parser = IntentParser()

test_questions = [
    "你觉得如何才可以更好的理解需求？",
    "你如何理解用户意图？",
    "你怎么知道自己理解对了？",
    "你觉得自己有哪些能力？",
    "如何让你变得更聪明？",
    "你的自我进化是如何工作的？",
    "你能明白我的意思吗？",
    "我讲的是你",
    "你处理不了我的问题？"
]

print("=" * 60)
print("测试元认知意图识别")
print("=" * 60)

success_count = 0
for q in test_questions:
    intent = parser.parse(q)
    status = "✓" if intent.type == "meta" else "✗"
    if intent.type == "meta":
        success_count += 1
    print(f"{status} {q[:40]:<40} → {intent.type} ({intent.confidence:.2f})")

print("\n" + "=" * 60)
print(f"测试结果: {success_count}/{len(test_questions)} 正确识别为meta意图")
print("=" * 60)