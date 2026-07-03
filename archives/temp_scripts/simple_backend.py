"""
简化后端启动脚本 - 用于测试
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="联盟拓荒者测试接口")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "联盟拓荒者服务已启动", "status": "ok"}

@app.get("/health")
async def health():
    """健康检查"""
    try:
        from infrastructure.health_dashboard import health_dashboard
        aphi = health_dashboard.calculate_aphi()
        return {
            "status": "healthy",
            "aphi": aphi["aphi"],
            "mode": aphi["mode"]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/chat")
async def chat(message: str):
    """简单聊天接口"""
    try:
        from core.services.intent_parser import IntentParser
        parser = IntentParser()
        intent = parser.parse(message)
        
        return {
            "response": f"收到消息: {message}",
            "intent": intent.type,
            "confidence": intent.confidence
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/test")
async def test():
    """测试接口"""
    return {
        "status": "ok",
        "message": "测试接口正常",
        "endpoints": ["/", "/health", "/chat", "/test"]
    }

if __name__ == "__main__":
    print("="*60)
    print("联盟拓荒者测试服务")
    print("="*60)
    print("\n访问地址:")
    print("  主页: http://localhost:8000")
    print("  健康检查: http://localhost:8000/health")
    print("  测试接口: http://localhost:8000/test")
    print("  API文档: http://localhost:8000/docs")
    print("\n按 Ctrl+C 停止服务")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")