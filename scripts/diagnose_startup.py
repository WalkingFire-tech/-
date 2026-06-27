"""
诊断脚本 - 检查服务启动问题
"""
import sys
import os

sys.path.insert(0, '.')

print("=" * 70)
print("服务启动诊断")
print("=" * 70)
print()

# 1. 检查uvicorn是否安装
print("[1/5] 检查uvicorn...")
try:
    import uvicorn
    print(f"  ✓ uvicorn已安装: {uvicorn.__version__}")
except ImportError:
    print("  ✗ uvicorn未安装")
    print("  解决: pip install uvicorn")
    sys.exit(1)

# 2. 检查FastAPI
print("\n[2/5] 检查FastAPI...")
try:
    from fastapi import FastAPI
    import fastapi
    print(f"  ✓ FastAPI已安装: {fastapi.__version__}")
except ImportError:
    print("  ✗ FastAPI未安装")
    print("  解决: pip install fastapi")
    sys.exit(1)

# 3. 检查backend.main模块
print("\n[3/5] 检查backend.main模块...")
try:
    from backend.main import app
    print(f"  ✓ backend.main:app 已加载")
    print(f"    路由数: {len(app.routes)}")
except Exception as e:
    print(f"  ✗ 加载失败: {e}")
    sys.exit(1)

# 4. 检查端口占用
print("\n[4/5] 检查端口8000...")
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('127.0.0.1', 8000))
sock.close()

if result == 0:
    print("  ⚠ 端口8000已被占用")
    print("  解决: 结束占用进程或使用其他端口")
else:
    print("  ✓ 端口8000可用")

# 5. 尝试启动测试
print("\n[5/5] 启动测试...")
print("  尝试在后台启动服务...")

import threading
import time

def run_server():
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
    except Exception as e:
        print(f"  启动错误: {e}")

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

# 等待启动
print("  等待服务就绪...")
max_wait = 10
for i in range(max_wait):
    time.sleep(1)
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/", timeout=1)
        if response.status_code == 200:
            print(f"  ✓ 服务启动成功！")
            print(f"\n访问地址:")
            print(f"  - http://localhost:8000/")
            print(f"  - http://localhost:8000/docs")
            
            # 测试前端
            print(f"\n测试前端访问...")
            try:
                response = requests.get("http://127.0.0.1:8000/frontend/index.html", timeout=2)
                if response.status_code == 200:
                    print(f"  ✓ 前端可访问")
                else:
                    print(f"  ⚠ 前端返回: {response.status_code}")
            except Exception as e:
                print(f"  ✗ 前端访问失败: {e}")
            
            sys.exit(0)
    except:
        print(f"  等待中... ({i+1}/{max_wait})")

print("  ✗ 服务启动超时")
print("\n可能的原因:")
print("  1. lifespan函数中有阻塞操作")
print("  2. 某个初始化步骤卡住")
print("  3. 依赖服务未就绪")

sys.exit(1)