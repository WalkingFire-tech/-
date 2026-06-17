"""
快速测试 - 验证Ollama响应速度
"""
import requests
import time

print("\n=== 测试后端健康 ===")
try:
    response = requests.get("http://localhost:8000/api/health", timeout=5)
    print(f"✅ 后端健康: {response.json()}")
except Exception as e:
    print(f"❌ 后端未响应: {e}")
    print("请等待后端启动...")
    exit(1)

print("\n=== 测试对话功能 ===")
test_cases = [
    "你好",
    "1+1等于几？",
    "什么是机器学习？"
]

for text in test_cases:
    try:
        start = time.time()
        response = requests.post(
            "http://localhost:8000/api/chat",
            json={"message": text},
            timeout=60
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ '{text}' - {duration:.2f}秒 - {data.get('model_used', 'unknown')}")
        else:
            print(f"❌ '{text}' - {response.status_code}")
    except Exception as e:
        print(f"❌ '{text}' - 错误: {e}")

print("\n测试完成")