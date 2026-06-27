import sys
sys.path.insert(0, ".")

from core.dialogue.scene_perceiver import ScenePerceiver, SceneRole

print("\n" + "="*60)
print("测试对话场景识别")
print("="*60)

perceiver = ScenePerceiver()

test_cases = [
    "一年有几个季节？",
    "那么一年有多少个节气？",
    "这对么？",
    "你回答得有问题，只有18个",
    "继续说完剩下的",
    "不对吧，应该是24个",
    "真的吗？",
    "那如果换一种情况呢？"
]

for i, text in enumerate(test_cases, 1):
    print(f"\n[测试{i}] 输入: {text}")
    
    result = perceiver.perceive(text)
    
    print(f"  主角色: {result.primary_role.value} (置信度: {result.confidence:.2f})")
    print(f"  匹配指示词: {result.indicators_matched}")
    
    if result.secondary_roles:
        print(f"  次要角色: {[r.value for r in result.secondary_roles]}")
    
    print(f"  上下文线索: {result.context_clues[:3]}")

print("\n" + "="*60)
print("测试完成")
print("="*60)