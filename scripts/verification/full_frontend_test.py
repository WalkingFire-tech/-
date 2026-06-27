"""
完整端到端测试 - 包含服务启动
"""
import sys
import os
import time
import subprocess
import requests

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 70)
print("端到端测试 - 前端功能（含服务启动）")
print("=" * 70)
print()

# 启动服务
print("[启动] 启动minimal_app服务...")
process = subprocess.Popen(
    [sys.executable, "minimal_app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
)

print(f"  进程PID: {process.pid}")
print("  等待服务就绪...")

# 等待服务启动
API_BASE = "http://localhost:8000"
max_wait = 15
service_ready = False

for i in range(max_wait):
    time.sleep(1)
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=1)
        if response.status_code == 200:
            print(f"  ✓ 服务就绪 (耗时: {i+1}秒)")
            service_ready = True
            break
    except:
        print(f"  等待中... ({i+1}/{max_wait})")

if not service_ready:
    print("  ✗ 服务启动超时")
    process.terminate()
    sys.exit(1)

print()

# 运行测试
tests = []

# 1. 主页
print("[1/6] 测试主页...")
try:
    response = requests.get(f"{API_BASE}/", timeout=5)
    if "联盟拓荒者" in response.text:
        print(f"  ✓ 主页正常")
        tests.append(True)
    else:
        print(f"  ✗ 主页内容异常")
        tests.append(False)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 2. 模型列表
print("\n[2/6] 测试模型列表...")
try:
    response = requests.get(f"{API_BASE}/api/models", timeout=5)
    data = response.json()
    print(f"  ✓ 模型: {data}")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 3. Ollama扫描
print("\n[3/6] 测试Ollama扫描...")
try:
    response = requests.get(f"{API_BASE}/api/models/scan", timeout=5)
    data = response.json()
    if data.get("ollama_available"):
        print(f"  ✓ Ollama可用: {data['count']}个模型")
    else:
        print(f"  ⚠ Ollama未运行: {data.get('hint', '')}")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 4. 模型重载
print("\n[4/6] 测试模型重载...")
try:
    response = requests.post(f"{API_BASE}/api/models/reload", timeout=5)
    data = response.json()
    print(f"  ✓ {data.get('message', '')}")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 5. 统计信息
print("\n[5/6] 测试统计信息...")
try:
    response = requests.get(f"{API_BASE}/api/stats", timeout=5)
    data = response.json()
    print(f"  ✓ 经验={data.get('experiences', 0)}, 规则={data.get('rules', 0)}")
    tests.append(True)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 6. 学习仪表盘
print("\n[6/6] 测试学习仪表盘...")
try:
    response = requests.get(f"{API_BASE}/learning", timeout=5)
    if response.status_code == 200:
        print(f"  ✓ 学习仪表盘正常")
        tests.append(True)
    else:
        print(f"  ✗ 状态码: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ {e}")
    tests.append(False)

# 停止服务
print("\n[停止] 停止服务...")
process.terminate()
try:
    process.wait(timeout=5)
except:
    process.kill()
print("  ✓ 服务已停止")

# 总结
print("\n" + "=" * 70)
passed = sum(tests)
total = len(tests)
print(f"测试结果: {passed}/{total} 通过")
print("=" * 70)

if passed == total:
    print("\n✅ 所有测试通过！")
    print("\n前端功能:")
    print("  ✓ 主页显示正常")
    print("  ✓ 模型API正常")
    print("  ✓ Ollama扫描正常")
    print("  ✓ 统计信息正常")
    print("\n注意事项:")
    print("  - Ollama服务未运行，需要启动: ollama serve")
    print("  - 完整功能请使用: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
else:
    print(f"\n❌ {total - passed} 个测试失败")

sys.exit(0 if passed == total else 1)