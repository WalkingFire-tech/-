"""
完整后端服务启动脚本
"""
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("="*60)
print("联盟拓荒者 - 完整后端服务")
print("="*60)
print("\n正在启动服务...")
print("\n🌐 测试界面地址:")
print("  API文档: http://localhost:8000/docs")
print("  健康检查: http://localhost:8000/health")
print("  主页: http://localhost:8000")
print("\n💡 测试步骤:")
print("  1. 等待服务启动完成")
print("  2. 浏览器访问 http://localhost:8000/docs")
print("  3. 使用Swagger UI测试接口")
print("\n按 Ctrl+C 停止服务")
print("="*60)
print()

# 启动完整后端
subprocess.run([sys.executable, "backend/main.py"])