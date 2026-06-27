"""
测试模型扫描和加载
"""
import requests

API_BASE = "http://localhost:8000"

print("=" * 70)
print("模型扫描测试")
print("=" * 70)
print()

# 1. 扫描模型
print("[1/3] 扫描Ollama模型...")
try:
    response = requests.get(f"{API_BASE}/api/models/scan", timeout=5)
    data = response.json()
    
    if data.get("success"):
        print(f"  ✓ Ollama可用: {data['count']}个模型")
        for model in data.get("models", []):
            print(f"    - {model['name']}")
    else:
        print(f"  ✗ {data.get('error', '未知错误')}")
except Exception as e:
    print(f"  ✗ {e}")

# 2. 获取模型列表
print("\n[2/3] 获取模型列表...")
try:
    response = requests.get(f"{API_BASE}/api/models", timeout=5)
    data = response.json()
    
    print(f"  ✓ 模型数量: {data.get('count', 0)}")
    for model in data.get("models", []):
        print(f"    - {model['name']} ({model['type']})")
except Exception as e:
    print(f"  ✗ {e}")

# 3. 重新加载
print("\n[3/3] 重新加载模型...")
try:
    response = requests.post(f"{API_BASE}/api/models/reload", timeout=5)
    data = response.json()
    
    print(f"  ✓ {data.get('message', '')}")
    print(f"  ✓ 总数: {data.get('total', 0)}")
except Exception as e:
    print(f"  ✗ {e}")

print("\n" + "=" * 70)