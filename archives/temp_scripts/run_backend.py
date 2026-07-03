"""
最简启动脚本 - 直接启动uvicorn
"""
import subprocess
import sys

print("=" * 60)
print("启动联盟拓荒者后端")
print("=" * 60)
print("\n地址: http://localhost:8000")
print("API文档: http://localhost:8000/docs")
print("\n按Ctrl+C停止服务")
print("=" * 60 + "\n")

# 直接使用uvicorn命令启动
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "backend.main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--log-level", "info"
])