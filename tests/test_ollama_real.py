"""
真实测试 - 检查Ollama连接和模型加载
"""
import requests

print("=" * 60)
print("真实测试 - Ollama连接")
print("=" * 60)

# 测试Ollama连接
print("\n[测试1] Ollama服务")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=3)
    print(f"状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"✓ Ollama服务可用")
        print(f"✓ 检测到 {len(models)} 个模型:")
        for m in models:
            size_gb = m.get('size', 0) / (1024**3)
            print(f"  - {m['name']} ({size_gb:.2f} GB)")
    else:
        print(f"✗ Ollama响应异常: {response.status_code}")
        
except Exception as e:
    print(f"✗ Ollama服务不可用: {e}")

# 测试后端API（需要后端运行）
print("\n[测试2] 后端API")
try:
    response = requests.get("http://localhost:8000/api/health", timeout=2)
    print(f"✓ 后端服务运行中 (状态: {response.status_code})")
    
    # 测试刷新API
    print("\n[测试3] 刷新API")
    response = requests.post("http://localhost:8000/api/models/reload", timeout=10)
    print(f"状态: {response.status_code}")
    data = response.json()
    print(f"成功: {data.get('success')}")
    print(f"总计: {data.get('total')}")
    print(f"新增: {data.get('added', [])}")
    print(f"消息: {data.get('message', '')}")
    print(f"错误: {data.get('error', '无')}")
    
except requests.exceptions.ConnectionError:
    print("✗ 后端服务未运行")
    print("\n启动方法:")
    print("  python backend/main.py")
except Exception as e:
    print(f"✗ 请求失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)