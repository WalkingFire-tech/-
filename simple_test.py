"""简单测试 - 检查问题"""
import sys
from pathlib import Path

print("=" * 60)
print("后端服务诊断")
print("=" * 60)

# 测试1: 检查当前目录
print(f"\n[1] 当前目录: {Path.cwd()}")
print(f"    项目根目录: {Path(__file__).parent}")

# 测试2: 检查api.py
api_file = Path("api.py")
print(f"\n[2] api.py存在: {api_file.exists()}")
if api_file.exists():
    print(f"    文件大小: {api_file.stat().st_size} bytes")

# 测试3: 检查frontend目录
frontend_dir = Path("frontend")
print(f"\n[3] frontend目录存在: {frontend_dir.exists()}")
if frontend_dir.exists():
    files = list(frontend_dir.glob("*"))
    print(f"    文件数: {len(files)}")
    for f in files[:5]:
        print(f"      - {f.name}")

# 测试4: 检查backend/main.py
backend_file = Path("backend/main.py")
print(f"\n[4] backend/main.py存在: {backend_file.exists()}")

# 测试5: 尝试导入
print("\n[5] 尝试导入API...")
try:
    ROOT_DIR = Path(__file__).parent
    sys.path.insert(0, str(ROOT_DIR))
    from api import app
    print(f"    ✓ API导入成功: {app.title}")
    print(f"    ✓ 版本: {app.version}")
except Exception as e:
    print(f"    ✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
print("\n如果看到'API导入成功'，请运行:")
print("  python -m uvicorn api:app --host 0.0.0.0 --port 8000")
print("\n然后在浏览器访问:")
print("  http://localhost:8000/")