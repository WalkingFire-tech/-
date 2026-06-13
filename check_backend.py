"""
检查后端服务状态
"""
import time
import requests

print("等待后端服务启动...")
time.sleep(3)

try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print("✅ 后端服务已启动")
        print(f"健康状态: {response.json()}")
    else:
        print(f"⚠️ 服务响应异常: {response.status_code}")
except Exception as e:
    print(f"❌ 无法连接到服务: {e}")
    print("\n请检查:")
    print("1. 后端服务是否正在运行: python backend/main.py")
    print("2. 端口8000是否被占用")