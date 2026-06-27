"""
简化版后端 - 快速启动
"""
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from loguru import logger

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

@asynccontextmanager
async def lifespan(app: FastAPI):
    """简化的lifespan - 快速启动"""
    logger.info("🚀 启动后端服务...")
    
    # 初始化编排器
    try:
        from core.orchestrator import SystemOrchestrator
        orchestrator = SystemOrchestrator({"persistence_dir": "data/orchestrator"})
        orchestrator.start()
        logger.info("✅ 系统编排器已启动")
    except Exception as e:
        logger.warning(f"编排器启动失败: {e}")
    
    yield
    
    logger.info("后端服务关闭")

app = FastAPI(
    title="联盟拓荒者 API",
    description="生产级自我进化智能体系统 API",
    version="3.1.1",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 挂载前端静态文件
FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/")
async def root():
    """根路径返回前端页面"""
    frontend_index = FRONTEND_DIR / "index.html"
    if frontend_index.exists():
        with open(frontend_index, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"message": "联盟拓荒者 API", "docs": "/docs"}

@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "version": "3.1.1"}

@app.get("/api/stats")
async def get_stats():
    """获取系统统计"""
    import sqlite3
    stats = {}
    try:
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiences")
        stats["experiences"] = cursor.fetchone()[0]
        conn.close()
    except:
        stats["experiences"] = 0
    try:
        conn = sqlite3.connect("data/learning_rules.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rules")
        stats["rules"] = cursor.fetchone()[0]
        conn.close()
    except:
        stats["rules"] = 0
    return stats

@app.get("/api/models")
async def get_models():
    """获取模型列表"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return {"models": [{"name": m['name'], "type": "Ollama"} for m in models], "count": len(models)}
    except:
        pass
    return {"models": [], "count": 0}

@app.get("/api/knowledge/health")
async def knowledge_health():
    """知识库健康检查"""
    return {"status": "ok", "knowledge_store": "available"}

@app.post("/api/chat")
async def chat(request: dict):
    """聊天接口"""
    user_input = request.get("message", "")
    return {"success": True, "response": f"收到: {user_input}", "model": "auto"}

@app.post("/api/models/reload")
async def models_reload():
    """重新加载模型"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return {"success": True, "added": [m['name'] for m in models], "total": len(models)}
    except:
        pass
    return {"success": False, "added": [], "total": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)