"""前端集成测试"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 60)
print("联盟拓荒者 - 前端集成测试")
print("=" * 60)

# 测试1: 检查前端文件
print("\n[1/4] 检查前端文件...")
frontend_files = [
    "frontend/index.html",
    "frontend/styles.css",
    "frontend/app.js",
]

for file in frontend_files:
    if Path(file).exists():
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} 不存在")

# 测试2: 检查后端静态文件服务
print("\n[2/4] 检查后端配置...")
try:
    from backend.main import app, FRONTEND_DIR
    print(f"  ✓ FastAPI应用: {app.title}")
    print(f"  ✓ 前端目录: {FRONTEND_DIR}")
    print(f"  ✓ 前端目录存在: {FRONTEND_DIR.exists()}")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")

# 测试3: 检查API端点
print("\n[3/4] 检查API端点...")
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # 健康检查
    response = client.get("/api/health")
    if response.status_code == 200:
        print(f"  ✓ /api/health: {response.json()}")
    
    # 统计信息
    response = client.get("/api/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"  ✓ /api/stats: 经验池={stats['experiences']}, 规则={stats['active_rules']}")
    
    # 模型列表
    response = client.get("/api/models")
    if response.status_code == 200:
        models = response.json()['models']
        print(f"  ✓ /api/models: {len(models)}个模型")
    
    # 根路径
    response = client.get("/")
    if response.status_code == 200:
        print(f"  ✓ /: 返回状态码 {response.status_code}")
    
except Exception as e:
    print(f"  ✗ API测试失败: {e}")

# 测试4: 检查启动脚本
print("\n[4/4] 检查启动脚本...")
scripts = [
    "启动.bat",
    "scripts/start_backend.bat",
    "scripts/start_all.bat",
]

for script in scripts:
    if Path(script).exists():
        print(f"  ✓ {script}")
    else:
        print(f"  ✗ {script} 不存在")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print("\n启动方式:")
print("  1. 双击 启动.bat")
print("  2. 或运行: python -m uvicorn api:app --reload --port 8000")
print("  3. 浏览器访问: http://localhost:8000/")
print()