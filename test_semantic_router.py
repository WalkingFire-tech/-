"""
测试语义路由器
"""
import sys
sys.path.insert(0, ".")

from infrastructure.semantic_router import semantic_router

print("\n" + "="*60)
print("测试语义路由器")
print("="*60)

# 测试用例
test_cases = [
    ("我很难过，感觉生活没有意义", -0.8, 1),
    ("你好，在吗？", 0.0, 0),
    ("什么是机器学习？", 0.0, 2),
    ("我应该选择哪个方案？", 0.0, 3),
    ("帮我写一个冒泡排序", 0.0, 1),
    ("我想学习Python", 0.1, 4),
    ("这个问题太复杂了，我不知道怎么办", -0.3, 5),
]

print("\n【测试路由】")
for message, emotion, rounds in test_cases:
    print(f"\n用户: {message}")
    print(f"情绪: {emotion}, 轮次: {rounds}")
    
    results = semantic_router.route(
        user_message=message,
        emotion_score=emotion,
        dialogue_round=rounds,
        top_k=2
    )
    
    for i, (skill, confidence, prompt) in enumerate(results, 1):
        print(f"  Top{i}: {skill} (置信度: {confidence:.3f})")
        if i == 1:
            print(f"       提示: {prompt[:50]}...")

# 测试反馈记录
print("\n\n【测试反馈记录】")
semantic_router.record_feedback(
    user_message="我很难过",
    chosen_skill="empathy",
    user_satisfaction=0.9,
    response_quality=85
)
print("✅ 反馈已记录")

# 测试进化
print("\n【测试进化】")
print(f"反馈缓冲区: {len(semantic_router.feedback_buffer)}条")

# 获取报告
print("\n" + "="*60)
print(semantic_router.get_routing_report())
print("="*60)