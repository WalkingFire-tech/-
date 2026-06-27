"""
端到端测试 - 前端功能
"""
import sys
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ".")
import requests
import time

API_BASE = "http://localhost:8000"

print("=" * 70)
print("端到端测试 - 前端功能")
print("=" * 70)
print()

tests = []

# 1. 测试主页
print("[1/8] 测试主页...")
try:
    response = requests.get(f"{API_BASE}/", timeout=5)
    if response.status_code == 200 and "联盟拓荒者" in response.text:
        print(f"  ✓ 主页正常: {len(response.content)} 字节")
        tests.append(True)
    else:
        print(f"  ✗ 主页异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ 主页失败: {e}")
    tests.append(False)

# 2. 测试API文档
print("\n[2/8] 测试API文档...")
try:
    response = requests.get(f"{API_BASE}/docs", timeout=5)
    if response.status_code == 200:
        print(f"  ✓ API文档正常")
        tests.append(True)
    else:
        print(f"  ✗ API文档异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ API文档失败: {e}")
    tests.append(False)

# 3. 测试健康检查
print("\n[3/8] 测试健康检查...")
try:
    response = requests.get(f"{API_BASE}/api/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ 健康检查: {data}")
        tests.append(True)
    else:
        print(f"  ✗ 健康检查异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ 健康检查失败: {e}")
    tests.append(False)

# 4. 测试模型列表
print("\n[4/8] 测试模型列表...")
try:
    response = requests.get(f"{API_BASE}/api/models", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ 模型列表: {data}")
        tests.append(True)
    else:
        print(f"  ✗ 模型列表异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ 模型列表失败: {e}")
    tests.append(False)

# 5. 测试Ollama扫描
print("\n[5/8] 测试Ollama扫描...")
try:
    response = requests.get(f"{API_BASE}/api/models/scan", timeout=5)
    if response.status_code == 200:
        data = response.json()
        if data.get("ollama_available"):
            print(f"  ✓ Ollama可用: {data['count']}个模型")
            for model in data.get("models", []):
                print(f"    - {model['name']}")
        else:
            print(f"  ⚠ Ollama未运行: {data.get('error', '')}")
            print(f"    提示: {data.get('hint', '启动Ollama: ollama serve')}")
        tests.append(True)
    else:
        print(f"  ✗ Ollama扫描异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ Ollama扫描失败: {e}")
    tests.append(False)

# 6. 测试模型重载
print("\n[6/8] 测试模型重载...")
try:
    response = requests.post(f"{API_BASE}/api/models/reload", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ 模型重载: {data.get('message', '')}")
        tests.append(True)
    else:
        print(f"  ✗ 模型重载异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ 模型重载失败: {e}")
    tests.append(False)

# 7. 测试统计信息
print("\n[7/8] 测试统计信息...")
try:
    response = requests.get(f"{API_BASE}/api/stats", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ 统计信息: 经验={data.get('experiences', 0)}, 规则={data.get('rules', 0)}")
        tests.append(True)
    else:
        print(f"  ✗ 统计信息异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ 统计信息失败: {e}")
    tests.append(False)

# 8. 测试学习仪表盘
print("\n[8/8] 测试学习仪表盘...")
try:
    response = requests.get(f"{API_BASE}/learning", timeout=5)
    if response.status_code == 200:
        print(f"  ✓ 学习仪表盘正常: {len(response.content)} 字节")
        tests.append(True)
    else:
        print(f"  ✗ 学习仪表盘异常: {response.status_code}")
        tests.append(False)
except Exception as e:
    print(f"  ✗ 学习仪表盘失败: {e}")
    tests.append(False)

# 总结
print("\n" + "=" * 70)
passed = sum(tests)
total = len(tests)
print(f"测试结果: {passed}/{total} 通过")
print("=" * 70)

if passed == total:
    print("\n✅ 所有前端功能测试通过！")
    print("\n注意事项:")
    print("  - Ollama服务未运行，模型功能受限")
    print("  - 启动Ollama: ollama serve")
    print("  - 查看模型: ollama list")
    print("  - 完整功能: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
else:
    print(f"\n❌ {total - passed} 个测试失败")

sys.exit(0 if passed == total else 1)