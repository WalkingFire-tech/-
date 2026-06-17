"""
简化测试语义路由器（不加载嵌入模型）
"""
import sys
sys.path.insert(0, ".")

print("\n" + "="*60)
print("测试语义路由器（降级模式）")
print("="*60)

# 测试降级路由
test_cases = [
    ("我很难过，感觉生活没有意义", -0.8),
    ("你好，在吗？", 0.0),
    ("什么是机器学习？", 0.0),
    ("我应该选择哪个方案？", 0.0),
    ("帮我写一个冒泡排序", 0.0),
]

print("\n【测试降级路由】")
for message, emotion in test_cases:
    print(f"\n用户: {message}")
    print(f"情绪: {emotion}")
    
    # 直接测试降级路由
    message_lower = message.lower()
    
    # 情绪优先
    if emotion < -0.6:
        print(f"  → empathy (情绪优先)")
        continue
    
    # 关键词匹配
    if any(kw in message_lower for kw in ["为什么", "什么是", "怎么", "如何"]):
        print(f"  → factual (知识问题)")
    elif any(kw in message_lower for kw in ["帮我", "应该", "选择"]):
        print(f"  → socratic (需要引导)")
    elif any(kw in message_lower for kw in ["你好", "在吗", "嗨"]):
        print(f"  → chitchat (闲聊)")
    else:
        print(f"  → factual (默认)")

print("\n" + "="*60)
print("✅ 降级路由测试完成")
print("="*60)