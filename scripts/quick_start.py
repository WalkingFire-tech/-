"""
快速启动并测试
"""
import sys
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("="*60)
print("快速启动测试")
print("="*60)

# 直接导入并运行
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="测试服务")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "服务已启动", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok", "aphi": 86.43}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message", "")
    
    # 简单意图识别
    if "能力边界" in message or "决策" in message:
        response = f"""系统状态报告：

APHI指数: 86.43/100
运行模式: optimal
能力覆盖率: 100%

已注册模型: 19个
能力维度: 8个

收到消息: {message}"""
    else:
        response = f"收到: {message}"
    
    return {"response": response}

print("\n服务启动中...")
print("\n访问地址:")
print("  API文档: http://localhost:8000/docs")
print("  健康检查: http://localhost:8000/health")
print("\n按 Ctrl+C 停止")
print("="*60)

uvicorn.run(app, host="0.0.0.0", port=8000)