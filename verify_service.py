"""
服务验证脚本 - 测试API是否真的在运行
"""
import sys
import time
import requests
import subprocess
import signal

print("=" * 70)
print("服务验证测试")
print("=" * 70)
print()

# 1. 检查端口是否被占用
print("[1/3] 检查端口8000...")
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8000))
    sock.close()
    
    if result == 0:
        print("  ✓ 端口8000已被占用（可能有服务在运行）")
        
        # 尝试访问
        try:
            response = requests.get("http://127.0.0.1:8000/", timeout=2)
            print(f"  ✓ 服务响应: {response.status_code}")
            print(f"  ✓ 服务正在运行！")
            print()
            print("访问地址:")
            print("  - http://localhost:8000/")
            print("  - http://localhost:8000/docs")
            sys.exit(0)
        except Exception as e:
            print(f"  ✗ 无法访问服务: {e}")
    else:
        print("  ✗ 端口8000未被占用（服务未启动）")
except Exception as e:
    print(f"  ✗ 检查失败: {e}")

# 2. 尝试启动服务
print("\n[2/3] 尝试启动最小化服务...")

process = subprocess.Popen(
    [sys.executable, "minimal_app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
)

print(f"  启动进程PID: {process.pid}")
print("  等待服务就绪...")

# 3. 等待并测试
max_wait = 15
for i in range(max_wait):
    time.sleep(1)
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=1)
        if response.status_code == 200:
            print(f"\n  ✓ 服务启动成功！(耗时: {i+1}秒)")
            print(f"  ✓ 状态码: {response.status_code}")
            print(f"  ✓ 内容长度: {len(response.content)} 字节")
            
            # 测试前端
            print("\n[3/3] 测试前端访问...")
            try:
                response = requests.get("http://127.0.0.1:8000/frontend/index.html", timeout=2)
                print(f"  ✓ 前端可访问: {response.status_code}")
            except Exception as e:
                print(f"  ⚠ 前端访问: {e}")
            
            print()
            print("=" * 70)
            print("✅ 服务验证成功！")
            print("=" * 70)
            print()
            print("访问地址:")
            print("  - 主页: http://localhost:8000/")
            print("  - API文档: http://localhost:8000/docs")
            print("  - 学习仪表盘: http://localhost:8000/learning")
            print()
            print("按 Ctrl+C 停止服务")
            print()
            
            # 保持服务运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n停止服务...")
                process.terminate()
                sys.exit(0)
            
    except requests.exceptions.ConnectionError:
        print(f"  等待中... ({i+1}/{max_wait})")
    except Exception as e:
        print(f"  等待中... ({i+1}/{max_wait}) - {e}")

print("\n✗ 服务启动超时")
print()
print("可能的原因:")
print("  1. minimal_app.py有错误")
print("  2. 端口被其他进程占用")
print("  3. 防火墙阻止")

# 读取错误输出
stdout, stderr = process.communicate(timeout=1)
if stderr:
    print(f"\n错误输出:\n{stderr}")

process.terminate()
sys.exit(1)