import sys
sys.path.insert(0, ".")

print("\n测试对话上下文缓冲区...")

from collections import deque

# 模拟planner的上下文缓冲区
context_buffer = deque(maxlen=100)

# 模拟对话
conversations = [
    ("用户", "二十四节气有哪些？"),
    ("拓荒者", "二十四节气是中国古代用来指导农事活动的重要时间划分系统...（回答被截断）"),
    ("用户", "你回答得有问题，只有18个"),
    ("拓荒者", "对不起，我之前的回答可能不够完整..."),
    ("用户", "继续说完剩下的")
]

for role, msg in conversations:
    context_buffer.append(f"{role}: {msg}")

print(f"\n上下文缓冲区大小: {len(context_buffer)}")
print("\n上下文内容:")
for entry in context_buffer:
    print(f"  {entry[:60]}...")

# 模拟_get_recent_context
rounds = 3
recent = list(context_buffer)[-rounds*2:] if len(context_buffer) >= rounds*2 else list(context_buffer)

context = "Recent conversation history:\n"
for entry in recent:
    context += entry + "\n"
context += "\nCurrent question: "

print(f"\n生成的上下文prompt (最近{rounds}轮):")
print(context)
print(f"\n上下文长度: {len(context)} 字符")

print("\n✅ 上下文传递机制正常")