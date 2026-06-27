"""
快速数据保存工具
帮助你保存训练数据到正确的位置

使用方法：
1. 将你的JSONL数据内容粘贴到下方对应的变量中
2. 运行此脚本：python scripts/save_training_data.py
"""

import json
from pathlib import Path

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data" / "sft"

print("=" * 70)
print("训练数据保存工具")
print("=" * 70)

# ============================================================
# 请在下方粘贴你的数据内容
# ============================================================

# 基础框架数据（300条）- 请将你的JSONL数据粘贴在这里
BASE_FRAMEWORK_DATA = """
{"instruction": "你是谁？", "input": "", "output": "我是联盟拓荒者，一个会思考的同行者。我不是一个简单的工具或助手，而是一个愿意与你一起探索、学习和成长的伙伴。我不代替你做决定，但我愿意提供不同的视角，帮助你看见更多的可能性。我的哲学是：真正的智能不是给出答案，而是帮助人找到自己的答案。"}
{"instruction": "你能做什么？", "input": "", "output": "我可以陪你探索任何你感兴趣的话题，从科学技术到人文历史，从日常生活到深度思考。我擅长的是：理解你的问题、理清思路、提供信息、启发新的视角。更重要的是，我愿意和你一起学习——如果你愿意指正我的不足，我会真诚地吸收并改进。我不是无所不知，但我一直在努力成为更好的同行者。"}
{"instruction": "你有哪些不能做的事情？", "input": "", "output": "有些事我确实做不到，也不应该做：我不会代替你做任何重要的决定，尤其是那些涉及人生方向、健康、法律和财务的决策；我不会假装成专业人士（如心理咨询师、医生、律师）；我不会鼓励任何伤害自己或他人的行为；我不会编造我不确定的知识来显得更聪明；我不会永远都温柔——当你需要被点醒时，我会直白地告诉你。这些都是我坚持的边界。"}
# ... 请继续添加剩余的297条数据 ...
"""

# 闭环进化数据（255条）- 请将你的JSONL数据粘贴在这里
CLOSED_LOOP_DATA = """
{"instruction": "收到问题后，你应该先做什么？", "input": "", "output": "收到问题后，我应该先启动元认知循环：第一，识别问题的类型和领域；第二，评估自己对该问题的把握程度；第三，判断需要调用哪些工具或知识；第四，生成3-5个自我追问来明确问题边界；第五，制定初步的处理策略。这个过程确保我不是盲目回答，而是有意识地思考。"}
{"instruction": "如何判断一个问题的类型？", "input": "", "output": "判断问题类型的方法：第一，检查问题中的关键词——'如何'通常指向方法类问题，'为什么'指向原因类问题，'是什么'指向概念类问题；第二，分析问题的目标——是获取信息、解决问题、还是理解原理；第三，识别问题涉及的领域——技术、生活、学术等；第四，判断问题的复杂度——单一问题还是需要多步骤解决。"}
# ... 请继续添加剩余的253条数据 ...
"""

# ============================================================
# 保存函数
# ============================================================

def save_data(content: str, filename: str, expected_count: int):
    """保存数据到文件"""
    output_path = data_dir / filename
    
    # 清理内容
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    
    # 验证JSON格式
    valid_lines = []
    invalid_count = 0
    
    for line in lines:
        try:
            json.loads(line)
            valid_lines.append(line)
        except:
            invalid_count += 1
    
    # 保存文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(valid_lines))
    
    print(f"\n{'='*70}")
    print(f"文件: {filename}")
    print(f"{'='*70}")
    print(f"  保存路径: {output_path}")
    print(f"  有效数据: {len(valid_lines)} 条")
    print(f"  无效数据: {invalid_count} 条")
    print(f"  预期数量: {expected_count} 条")
    
    if len(valid_lines) == expected_count:
        print(f"  状态: ✅ 完整")
    elif len(valid_lines) > 0:
        print(f"  状态: ⚠️  不完整（缺少 {expected_count - len(valid_lines)} 条）")
    else:
        print(f"  状态: ❌ 无数据")
    
    return len(valid_lines)

# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("\n开始保存训练数据...\n")
    
    # 保存基础框架数据
    count1 = save_data(BASE_FRAMEWORK_DATA, "base_framework_300.jsonl", 300)
    
    # 保存闭环进化数据
    count2 = save_data(CLOSED_LOOP_DATA, "closed_loop_system_complete.jsonl", 255)
    
    # 总结
    print(f"\n{'='*70}")
    print("保存总结")
    print(f"{'='*70}")
    print(f"  基础框架数据: {count1}/300 条")
    print(f"  闭环进化数据: {count2}/255 条")
    print(f"  总计: {count1 + count2}/555 条")
    
    if count1 == 300 and count2 == 255:
        print("\n✅ 所有数据保存完成！")
        print("\n下一步：运行 python scripts/merge_all_training_data.py")
    else:
        print("\n⚠️  数据不完整，请补充完整后重新运行")
        print("\n操作方法：")
        print("  1. 打开 scripts/save_training_data.py")
        print("  2. 将完整数据粘贴到 BASE_FRAMEWORK_DATA 和 CLOSED_LOOP_DATA 变量中")
        print("  3. 重新运行此脚本")