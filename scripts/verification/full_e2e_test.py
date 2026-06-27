"""
完整端到端测试 - 包括启动服务
"""
import sys
import os
import time
import subprocess
import requests
import signal

sys.path.insert(0, '.')

print("=" * 70)
print("联盟拓荒者 - 端到端测试")
print("=" * 70)
print()

# 测试结果
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

# 1. 检查前端文件
print("[1/6] 检查前端文件...")
frontend_files = [
    "frontend/index.html",
    "frontend/styles.css",
    "frontend/app.js",
]

for f in frontend_files:
    if os.path.exists(f):
        print(f"  ✓ {f}")
    else:
        print(f"  ✗ {f} 不存在")
        results["failed"].append(f"前端文件缺失: {f}")

if all(os.path.exists(f) for f in frontend_files):
    results["passed"].append("前端文件检查")

# 2. 检查后端文件
print("\n[2/6] 检查后端文件...")
backend_files = [
    "backend/main.py",
    "core/orchestrator.py",
    "infrastructure/reflection_pipeline.py",
]

for f in backend_files:
    if os.path.exists(f):
        print(f"  ✓ {f}")
    else:
        print(f"  ✗ {f} 不存在")
        results["failed"].append(f"后端文件缺失: {f}")

if all(os.path.exists(f) for f in backend_files):
    results["passed"].append("后端文件检查")

# 3. 检查数据库
print("\n[3/6] 检查数据库...")
import sqlite3

dbs = {
    "经验池": "data/experience_pool.db",
    "学习规则": "data/learning_rules.db",
    "反思日志": "logs/campfire_log.db",
}

db_ok = True
for name, path in dbs.items():
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchone()[0]
        conn.close()
        print(f"  ✓ {name}: {tables}张表")
    else:
        print(f"  ✗ {name}: 不存在")
        db_ok = False

if db_ok:
    results["passed"].append("数据库检查")

# 4. 测试核心导入
print("\n[4/6] 测试核心模块导入...")
modules = [
    ("L1感知层", "core.layers.l1_perception_enhanced", "L1PerceptionLayer"),
    ("L2学习层", "core.layers.l2_learning", "L2LearningLayer"),
    ("编排器", "core.orchestrator", "SystemOrchestrator"),
]

import_ok = True
for name, module_path, class_name in modules:
    try:
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"  ✓ {name}")
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        import_ok = False

if import_ok:
    results["passed"].append("核心模块导入")

# 5. 启动API服务
print("\n[5/6] 启动API服务...")
print("  启动uvicorn服务...")

# 启动子进程
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待服务启动
print("  等待服务就绪...")
max_wait = 30
start_time = time.time()
service_started = False

while time.time() - start_time < max_wait:
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=2)
        if response.status_code == 200:
            service_started = True
            print(f"  ✓ 服务已启动 (耗时: {time.time() - start_time:.1f}s)")
            results["passed"].append("API服务启动")
            break
    except:
        time.sleep(1)
        print(f"  等待中... ({int(time.time() - start_time)}s)")

if not service_started:
    print("  ✗ 服务启动超时")
    results["failed"].append("API服务启动超时")

# 6. 测试API端点
if service_started:
    print("\n[6/6] 测试API端点...")
    
    endpoints = [
        ("根路径", "http://127.0.0.1:8000/"),
        ("API文档", "http://127.0.0.1:8000/docs"),
        ("健康检查", "http://127.0.0.1:8000/api/health"),
    ]
    
    api_ok = True
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ {name}: {response.status_code}")
            else:
                print(f"  ⚠ {name}: {response.status_code}")
                results["warnings"].append(f"{name}返回{response.status_code}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            api_ok = False
    
    if api_ok:
        results["passed"].append("API端点测试")
    
    # 停止服务
    print("\n停止API服务...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()
    print("  ✓ 服务已停止")

# 打印结果
print("\n" + "=" * 70)
print("测试结果")
print("=" * 70)
print(f"✅ 通过: {len(results['passed'])}")
print(f"❌ 失败: {len(results['failed'])}")
print(f"⚠️  警告: {len(results['warnings'])}")

if results['passed']:
    print("\n通过的测试:")
    for item in results['passed']:
        print(f"  ✓ {item}")

if results['failed']:
    print("\n失败的测试:")
    for item in results['failed']:
        print(f"  ✗ {item}")

if results['warnings']:
    print("\n警告:")
    for item in results['warnings']:
        print(f"  ⚠ {item}")

print("\n" + "=" * 70)

if results['failed']:
    print("结果: ❌ 存在失败的测试")
    sys.exit(1)
else:
    print("结果: ✅ 所有测试通过")
    sys.exit(0)