"""
联盟拓荒者 - 交互测试脚本
测试系统的九大核心能力
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("联盟拓荒者 - 交互测试")
print("=" * 80)
print("\n测试系统的九大核心能力:")
print("  1. 元认知启动 - 自动生成自我提问")
print("  2. 问题拆解 - MECE原则分解")
print("  3. 工具调用 - 智能选择工具")
print("  4. 自适应学习 - 策略调整")
print("  5. 持续学习 - 知识固化")
print("  6. 命令行操作 - 系统命令")
print("  7. 脚本生成 - 代码生成")
print("  8. 多模型协作 - Agent协调")
print("  9. 安全风险评估 - 风险识别")
print("\n" + "=" * 80)

# 测试问题列表
test_questions = [
    ("基础测试", "什么是机器学习？"),
    ("拆解测试", "如何从零开始学习深度学习？"),
    ("元认知测试", "为什么会有冰雹？"),
    ("工具调用测试", "帮我写一个Python脚本，批量重命名当前目录下的所有jpg文件"),
    ("复杂任务测试", "我需要搭建一个个人博客网站，但我不会编程，请帮我规划"),
]

print("\n开始测试...\n")

try:
    import requests
    
    for i, (test_type, question) in enumerate(test_questions, 1):
        print(f"[测试 {i}] {test_type}")
        print(f"问题: {question}")
        print("-" * 80)
        
        # 调用Ollama
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:7b",
                    "prompt": question,
                    "stream": False,
                    "options": {
                        "num_predict": 200,
                        "temperature": 0.7
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "")
                print(f"回答:\n{answer[:500]}...")
                print(f"\n✓ 测试通过")
            else:
                print(f"✗ 测试失败: HTTP {response.status_code}")
        
        except Exception as e:
            print(f"✗ 测试失败: {e}")
        
        print("\n" + "=" * 80 + "\n")
        
        # 暂停一下
        if i < len(test_questions):
            input("按Enter继续下一个测试...")
    
    print("\n所有测试完成!")
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()