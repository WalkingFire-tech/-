"""
详细诊断启动脚本
"""
import sys
import os
import traceback
from pathlib import Path

print("=" * 60)
print("详细诊断启动")
print("=" * 60)

# 设置路径
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

print(f"\n工作目录: {os.getcwd()}")
print(f"Python: {sys.version}")

# 步骤1: 导入必要的模块
print("\n[步骤1] 导入模块...")
modules_to_import = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("loguru", "Logger"),
    ("dotenv", "Dotenv"),
]

for module_name, display_name in modules_to_import:
    try:
        __import__(module_name)
        print(f"  ✓ {display_name}")
    except Exception as e:
        print(f"  ✗ {display_name}: {e}")
        sys.exit(1)

# 步骤2: 导入backend.main
print("\n[步骤2] 导入backend.main...")
try:
    from backend import main as backend_main
    print("  ✓ 导入成功")
    print(f"  FastAPI app: {backend_main.app}")
except Exception as e:
    print(f"  ✗ 导入失败")
    print("\n详细错误:")
    traceback.print_exc()
    sys.exit(1)

# 步骤3: 检查app对象
print("\n[步骤3] 检查FastAPI app...")
try:
    app = backend_main.app
    print(f"  ✓ App类型: {type(app)}")
    print(f"  ✓ App标题: {app.title}")
    print(f"  ✓ 路由数量: {len(app.routes)}")
except Exception as e:
    print(f"  ✗ 检查失败: {e}")
    traceback.print_exc()
    sys.exit(1)

# 步骤4: 启动uvicorn
print("\n[步骤4] 启动uvicorn...")
print("  地址: http://127.0.0.1:8000")
print("  API文档: http://127.0.0.1:8000/docs")
print("\n按Ctrl+C停止服务...")
print("=" * 60)

try:
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=True
    )
except KeyboardInterrupt:
    print("\n服务已停止")
except Exception as e:
    print(f"\n启动失败: {e}")
    traceback.print_exc()