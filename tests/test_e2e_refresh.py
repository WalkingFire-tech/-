"""
端到端测试 - 模型刷新功能
"""
import subprocess
import time
import requests
import sys
import signal

print("=" * 60)
print("端到端测试 - 模型刷新功能")
print("=" * 60)

# 设置环境变量
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 启动后端服务
print("\n[步骤1] 启动后端服务...")
backend_process = subprocess.Popen(
    [sys.executable, 'backend/main.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    env=os.environ
)

# 等待服务启动
print("等待服务启动...")
time.sleep(5)

# 测试API
print("\n[步骤2] 测试API端点...")

try:
    # 测试健康检查
    print("\n测试 GET /api/health")
    r = requests.get('http://localhost:8000/api/health', timeout=5)
    print(f"状态: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 测试模型列表
    print("\n测试 GET /api/models")
    r = requests.get('http://localhost:8000/api/models', timeout=5)
    print(f"状态: {r.status_code}")
    data = r.json()
    print(f"模型数量: {len(data.get('models', []))}")
    for m in data.get('models', []):
        print(f"  - {m['name']} ({m['type']})")
    
    # 测试模型刷新
    print("\n测试 POST /api/models/reload")
    r = requests.post('http://localhost:8000/api/models/reload', timeout=10)
    print(f"状态: {r.status_code}")
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"总计: {data.get('total')}")
    print(f"新增: {data.get('added', [])}")
    print(f"消息: {data.get('message', '')}")
    
    # 再次获取模型列表
    print("\n再次测试 GET /api/models")
    r = requests.get('http://localhost:8000/api/models', timeout=5)
    print(f"状态: {r.status_code}")
    data = r.json()
    print(f"模型数量: {len(data.get('models', []))}")
    for m in data.get('models', []):
        print(f"  - {m['name']} ({m['type']})")
    
    print("\n✅ API测试通过")
    
except Exception as e:
    print(f"\n❌ API测试失败: {e}")
    
finally:
    # 停止后端服务
    print("\n[步骤3] 停止后端服务...")
    backend_process.terminate()
    try:
        backend_process.wait(timeout=5)
    except:
        backend_process.kill()
    print("✓ 后端服务已停止")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)