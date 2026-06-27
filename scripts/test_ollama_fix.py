"""
快速测试Ollama集成
"""
import requests

print("=" * 60)
print("测试Ollama集成")
print("=" * 60)

# 测试Ollama连接
print("\n[1] 测试Ollama连接...")
try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        print(f"✓ Ollama运行中，共 {len(models)} 个模型")
        for m in models:
            print(f"  - {m['name']}")
except Exception as e:
    print(f"✗ Ollama连接失败: {e}")
    exit(1)

# 测试推理
print("\n[2] 测试模型推理...")
test_questions = [
    "什么是深度学习的特点？",
    "如何从零开始学习深度学习？",
]

for question in test_questions:
    print(f"\n问题: {question}")
    print("-" * 60)
    
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
            timeout=30
        )
        
        if response.status_code == 200:
            answer = response.json().get("response", "")
            print(f"回答:\n{answer[:300]}...")
            print(f"\n✓ 推理成功")
        else:
            print(f"✗ 推理失败: HTTP {response.status_code}")
    
    except Exception as e:
        print(f"✗ 推理失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n现在可以运行 start.bat 测试完整系统")