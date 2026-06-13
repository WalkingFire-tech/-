"""
诊断启动脚本
"""
import sys
import os
from pathlib import Path

print("=" * 60)
print("诊断启动脚本")
print("=" * 60)

# 1. 检查Python版本
print(f"\n[1] Python版本: {sys.version}")

# 2. 检查工作目录
print(f"[2] 工作目录: {os.getcwd()}")

# 3. 检查backend目录
backend_dir = Path("backend")
print(f"[3] backend目录存在: {backend_dir.exists()}")
print(f"    main.py存在: {(backend_dir / 'main.py').exists()}")

# 4. 添加路径
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
print(f"[4] 已添加路径: {ROOT_DIR}")

# 5. 检查关键依赖
print("\n[5] 检查关键依赖:")
dependencies = [
    "fastapi",
    "uvicorn",
    "loguru",
    "dotenv",
]
for dep in dependencies:
    try:
        __import__(dep)
        print(f"    ✓ {dep}")
    except ImportError as e:
        print(f"    ✗ {dep}: {e}")

# 6. 尝试导入backend.main
print("\n[6] 尝试导入backend.main:")
try:
    sys.path.insert(0, str(ROOT_DIR / "backend"))
    import main
    print("    ✓ 导入成功")
except Exception as e:
    print(f"    ✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    
# 7. 尝试直接运行uvicorn
print("\n[7] 尝试启动uvicorn:")
try:
    import uvicorn
    print("    uvicorn可用")
    print("    尝试启动服务（3秒后自动停止）...")
    
    # 创建一个简单的测试app
    from fastapi import FastAPI
    test_app = FastAPI()
    
    @test_app.get("/")
    def root():
        return {"message": "test"}
    
    # 不实际启动，只是测试配置
    config = uvicorn.Config(test_app, host="127.0.0.1", port=8000)
    print(f"    ✓ uvicorn配置成功: {config}")
    
except Exception as e:
    print(f"    ✗ uvicorn测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)