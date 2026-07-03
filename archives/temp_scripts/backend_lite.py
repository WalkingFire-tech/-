"""
轻量级后端服务 - 减少内存占用
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn

# 全局变量
planner = None
intent_parser = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """轻量级启动 - 只加载必要组件"""
    global planner, intent_parser
    
    logger.info("启动轻量级后端服务...")
    
    # 1. 意图解析器（轻量）
    from core.services.intent_parser import IntentParser
    intent_parser = IntentParser()
    logger.info("✓ 意图解析器已加载")
    
    # 2. 只加载一个模型适配器
    from adapters.llm.mock_adapter import MockAdapter
    adapters = {"mock": MockAdapter()}
    
    # 尝试加载Ollama（如果可用）
    try:
        from adapters.llm.ollama_adapter import OllamaAdapter
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("✓ MindChat已加载")
    except Exception as e:
        logger.warning(f"Ollama不可用，使用Mock适配器: {e}")
    
    # 3. 规划器
    from core.services.planner import Planner
    planner = Planner(adapters)
    logger.info("✓ 规划器已加载")
    
    logger.info(f"轻量级服务已就绪，加载了 {len(adapters)} 个模型")
    
    yield
    
    logger.info("关闭服务...")

app = FastAPI(
    title="联盟拓荒者（轻量级）",
    description="减少内存占用的轻量级服务",
    version="3.4-lite",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """主页"""
    return {
        "message": "联盟拓荒者（轻量级）",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """健康检查"""
    try:
        from infrastructure.health_dashboard import health_dashboard
        aphi = health_dashboard.calculate_aphi()
        return {
            "status": "healthy",
            "aphi": aphi["aphi"],
            "mode": aphi["mode"],
            "memory": "lite"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/chat")
async def chat(request: Request):
    """聊天接口"""
    try:
        data = await request.json()
        message = data.get("message", "")
        
        # 意图识别
        intent = intent_parser.parse(message)
        
        # 简单响应（不调用模型）
        if intent.type == "meta":
            from infrastructure.health_dashboard import health_dashboard
            aphi = health_dashboard.calculate_aphi()
            response = f"""系统状态报告：
            
APHI指数: {aphi['aphi']}/100
运行模式: {aphi['mode']}
能力覆盖率: {aphi['capability_coverage']}%
任务成功率: {aphi['task_success_rate']}%

意图类型: {intent.type}
置信度: {intent.confidence:.2f}"""
        else:
            response = f"收到消息: {message}\n意图: {intent.type}\n置信度: {intent.confidence:.2f}"
        
        return {
            "response": response,
            "intent": intent.type,
            "confidence": intent.confidence
        }
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        return {"error": str(e)}

@app.get("/api/aphi")
async def get_aphi():
    """APHI仪表盘"""
    try:
        from infrastructure.health_dashboard import health_dashboard
        return health_dashboard.calculate_aphi()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("="*60)
    print("联盟拓荒者 - 轻量级服务")
    print("="*60)
    print("\n特点:")
    print("  - 只加载1-2个模型")
    print("  - 禁用后台线程")
    print("  - 减少内存占用")
    print("\n访问地址:")
    print("  API文档: http://localhost:8000/docs")
    print("  健康检查: http://localhost:8000/health")
    print("\n按 Ctrl+C 停止")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")