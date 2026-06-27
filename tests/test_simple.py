"""
简化测试 - 验证后端服务和Ollama响应
"""
import requests
import time
import sys

def test_backend_health():
    print("\n=== 测试后端健康 ===")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ 后端健康: {response.json()}")
            return True
        else:
            print(f"❌ 后端异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 后端未响应: {e}")
        return False

def test_chat():
    print("\n=== 测试对话功能 ===")
    try:
        start = time.time()
        response = requests.post(
            "http://localhost:8000/chat",
            json={"message": "你好"},
            timeout=30
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 响应时间: {duration:.2f}秒")
            print(f"响应内容: {data.get('response', '')[:100]}...")
            print(f"使用模型: {data.get('model_used', 'unknown')}")
            return True
        else:
            print(f"❌ 对话失败: {response.status_code}")
            print(f"错误: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_intent():
    print("\n=== 测试意图识别 ===")
    test_cases = [
        "你好",
        "写一个冒泡排序",
        "什么是机器学习？",
        "为什么世界上有那么多种类的动物？"
    ]
    
    for text in test_cases:
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={"message": text},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                intent = data.get('intent', 'unknown')
                print(f"✅ '{text[:20]}...' -> {intent}")
            else:
                print(f"❌ '{text[:20]}...' 失败")
        except Exception as e:
            print(f"❌ '{text[:20]}...' 错误: {e}")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("联盟拓荒者 - 简化测试")
    print("="*60)
    
    # 测试后端
    if not test_backend_health():
        print("\n❌ 后端未启动，请先运行 start.bat")
        sys.exit(1)
    
    # 测试对话
    if not test_chat():
        print("\n❌ 对话功能异常")
        sys.exit(1)
    
    # 测试意图识别
    test_intent()
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)