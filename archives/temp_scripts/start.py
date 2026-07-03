#!/usr/bin/env python
"""
启动脚本 - 联盟拓荒者
"""
import sys
import os

# 设置工作目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 70)
print("联盟拓荒者 - 自我进化AI系统")
print("=" * 70)
print()
print("启动中...")
print()
print("访问地址:")
print("  - 主页: http://localhost:8000/")
print("  - API文档: http://localhost:8000/docs")
print("  - 学习仪表盘: http://localhost:8000/learning")
print("  - 知识面板: http://localhost:8000/knowledge-panel")
print()
print("按 Ctrl+C 停止服务")
print("=" * 70)
print()

# 启动uvicorn
import uvicorn
uvicorn.run(
    "backend.main:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    reload_dirs=["backend", "core", "infrastructure", "tools", "meta"],
    log_level="info"
)