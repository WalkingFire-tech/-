"""测试情绪推断优化"""
from infrastructure.emotion_inferencer import emotion_inferencer

test_cases = [
    ("你好，请帮我写代码", "neutral"),
    ("快点！我要结果！", "urgent"),
    ("这个不对，再试一次", "frustrated"),
    ("谢谢你的帮助", "happy"),
    ("太棒了！完美！", "happy"),
    ("什么破系统，太烂了！", "angry"),
    ("我不明白这是什么意思", "confused"),
    ("唉，有点失望", "disappointed"),
    ("非常着急，马上要！", "urgent"),
    ("受不了了，崩溃！", "frustrated"),
]

print("="*60)
print("情绪推断测试")
print("="*60)

for text, expected in test_cases:
    result = emotion_inferencer.infer(text)
    status = "✅" if result["emotion"] == expected or (expected == "neutral" and result["emotion"] in ["neutral", "happy"]) else "⚠️"
    print(f"{status} '{text[:30]}...'")
    print(f"   情绪: {result['emotion']} (期望: {expected})")
    print(f"   耐心: {result['patience']:.2f}")
    print(f"   紧迫: {result['urgency']:.2f}")
    if result["signals"]:
        print(f"   信号: {', '.join(result['signals'])}")
    print()