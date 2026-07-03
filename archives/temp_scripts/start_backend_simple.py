"""
简化启动脚本 - 直接启动uvicorn
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 60)
print("启动联盟拓荒者后端服务")
print("=" * 60)
print(f"工作目录: {os.getcwd()}")
print(f"Python版本: {sys.version}")
print("=" * 60)

# 直接启动uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )