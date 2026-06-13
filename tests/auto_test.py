"""
自动化测试脚本
启动后端并运行完整测试
"""
import subprocess
import sys
import time
import json
from pathlib import Path

print("=" * 70)
print("联盟拓荒者 - 自动化测试")
print("=" * 70)

# 步骤1: 启动后端
print("\n[步骤1] 启动后端服务...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=Path(__file__).parent,
    bufsize=1
)

print(f"进程ID: {proc.pid}")
print("等待启动（10秒）...")

# 等待并读取输出
time.sleep(10)

# 步骤2: 测试API
print("\n[步骤2] 测试API端点...")

test_results = []

# 测试1: 健康检查
print("\n测试1: GET /api/health")
try:
    import urllib.request
    with urllib.request.urlopen("http://localhost:8000/api/health", timeout=5) as response:
        data = json.loads(response.read())
        print(f"  ✓ 状态: {data['status']}")
        print(f"  ✓ 版本: {data['version']}")
        print(f"  ✓ 模型: {data['models']}")
        test_results.append(("健康检查", True))
except Exception as e:
    print(f"  ✗ 失败: {e}")
    test_results.append(("健康检查", False))

# 测试2: 统计信息
print("\n测试2: GET /api/stats")
try:
    with urllib.request.urlopen("http://localhost:8000/api/stats", timeout=5) as response:
        data = json.loads(response.read())
        print(f"  ✓ 经验池: {data['experiences']}条")
        print(f"  ✓ 活跃规则: {data['active_rules']}条")
        print(f"  ✓ 待激活规则: {data['pending_rules']}条")
        print(f"  ✓ 模型数: {data['models']}个")
        test_results.append(("统计信息", True))
except Exception as e:
    print(f"  ✗ 失败: {e}")
    test_results.append(("统计信息", False))

# 测试3: 模型列表
print("\n测试3: GET /api/models")
try:
    with urllib.request.urlopen("http://localhost:8000/api/models", timeout=5) as response:
        data = json.loads(response.read())
        print(f"  ✓ 模型数量: {len(data['models'])}个")
        for model in data['models']:
            print(f"    - {model['name']} ({model['type']})")
        test_results.append(("模型列表", True))
except Exception as e:
    print(f"  ✗ 失败: {e}")
    test_results.append(("模型列表", False))

# 测试4: 根路径（前端）
print("\n测试4: GET / (前端)")
try:
    with urllib.request.urlopen("http://localhost:8000/", timeout=5) as response:
        content = response.read()
        print(f"  ✓ 状态码: {response.status}")
        print(f"  ✓ 内容长度: {len(content)} bytes")
        test_results.append(("前端页面", True))
except Exception as e:
    print(f"  ✗ 失败: {e}")
    test_results.append(("前端页面", False))

# 步骤3: 测试总结
print("\n" + "=" * 70)
print("测试总结")
print("=" * 70)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for test_name, result in test_results:
    status = "✓ 通过" if result else "✗ 失败"
    print(f"{test_name:20s} {status}")

print(f"\n总计: {passed}/{total} 通过")

if passed == total:
    print("\n🎉 所有测试通过！")
    print("\n访问地址:")
    print("  - 前端界面: http://localhost:8000/")
    print("  - API文档:  http://localhost:8000/docs")
else:
    print("\n⚠️  部分测试失败")
    
    # 读取错误日志
    print("\n后端日志（最后20行）:")
    print("-" * 70)
    try:
        # 非阻塞读取
        import select
        if proc.stderr:
            lines = []
            for _ in range(20):
                line = proc.stderr.readline()
                if line:
                    lines.append(line.strip())
            for line in lines:
                print(line)
    except:
        print("(无法读取日志)")

print("\n" + "=" * 70)
print(f"后端进程仍在运行 (PID: {proc.pid})")
print("停止后端: taskkill /PID {} /F".format(proc.pid))
print("=" * 70)

# 保持运行
input("\n按Enter键停止后端并退出...")
proc.terminate()
print("后端已停止")