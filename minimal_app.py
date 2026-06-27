"""
最小化FastAPI应用 - 用于测试
"""
import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from loguru import logger

# 确保ROOT_DIR是项目根目录
ROOT_DIR = Path(__file__).parent.resolve()
os.chdir(ROOT_DIR)
sys.path.insert(0, str(ROOT_DIR))

# 前端目录
FRONTEND_DIR = ROOT_DIR / "frontend"

logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"FRONTEND_DIR: {FRONTEND_DIR}")
logger.info(f"frontend/index.html存在: {(FRONTEND_DIR / 'index.html').exists()}")

# 全局模型列表
AVAILABLE_MODELS = []

def scan_ollama_models():
    """扫描Ollama模型"""
    global AVAILABLE_MODELS
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            AVAILABLE_MODELS = [
                {"name": m['name'], "type": "OllamaAdapter"}
                for m in models
            ]
            logger.info(f"扫描到 {len(AVAILABLE_MODELS)} 个Ollama模型")
            return True
        else:
            logger.warning(f"Ollama响应异常: {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"无法连接Ollama: {e}")
        AVAILABLE_MODELS = [{"name": "mock", "type": "MockAdapter"}]
        return False

# 启动时扫描模型
scan_ollama_models()

app = FastAPI(
    title="联盟拓荒者 API",
    description="生产级自我进化智能体系统 API",
    version="3.1.1"
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
    logger.info(f"查找前端文件: {frontend_index}")
    logger.info(f"文件存在: {frontend_index.exists()}")
    
    if frontend_index.exists():
        with open(frontend_index, 'r', encoding='utf-8') as f:
            html_content = f.read()
        logger.info(f"返回前端页面: {len(html_content)} 字节")
        return HTMLResponse(content=html_content)
    
    logger.warning(f"前端文件不存在，返回API信息")
    return {"message": "联盟拓荒者 API", "docs": "/docs"}

@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "version": "3.1.1",
        "message": "系统运行正常"
    }

@app.get("/api/knowledge/health")
async def knowledge_health():
    """知识库健康检查"""
    return {
        "status": "ok",
        "knowledge_store": "available",
        "message": "知识库运行正常"
    }

@app.get("/learning")
async def learning_dashboard():
    """学习仪表盘页面"""
    dashboard_file = FRONTEND_DIR / "learning_dashboard.html"
    if dashboard_file.exists():
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"error": "Learning dashboard not found"}

@app.get("/knowledge-panel")
async def knowledge_panel():
    """知识水平面板页面"""
    panel_file = FRONTEND_DIR / "knowledge_panel.html"
    if panel_file.exists():
        with open(panel_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"error": "Knowledge panel not found"}

@app.get("/api/stats")
async def get_stats():
    """获取系统统计"""
    import sqlite3
    
    stats = {}
    
    # 经验池统计
    try:
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiences")
        stats["experiences"] = cursor.fetchone()[0]
        conn.close()
    except:
        stats["experiences"] = 0
    
    # 学习规则统计
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
    """获取可用模型列表"""
    global AVAILABLE_MODELS
    
    # 如果没有模型，尝试重新扫描
    if not AVAILABLE_MODELS:
        scan_ollama_models()  # 同步调用
    
    return {
        "models": AVAILABLE_MODELS,
        "count": len(AVAILABLE_MODELS)
    }

@app.get("/api/models/scan")
async def scan_ollama_models_endpoint():
    """扫描Ollama服务中的可用模型"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            
            return {
                "success": True,
                "ollama_available": True,
                "models": [
                    {
                        "name": m['name'],
                        "size": m.get('size', 0),
                        "modified_at": m.get('modified_at', '')
                    }
                    for m in models
                ],
                "count": len(models)
            }
        else:
            return {
                "success": False,
                "ollama_available": False,
                "error": f"Ollama响应异常: {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "ollama_available": False,
            "error": f"无法连接Ollama服务: {str(e)}",
            "hint": "请启动Ollama服务: ollama serve"
        }

@app.post("/api/models/reload")
async def reload_models():
    """重新加载模型"""
    global AVAILABLE_MODELS
    
    success = scan_ollama_models()  # 调用同步函数
    
    if success:
        return {
            "success": True,
            "added": [m['name'] for m in AVAILABLE_MODELS],
            "total": len(AVAILABLE_MODELS),
            "message": f"发现{len(AVAILABLE_MODELS)}个Ollama模型"
        }
    else:
        return {
            "success": False,
            "added": [],
            "total": 0,
            "message": "无法连接Ollama服务",
            "hint": "请启动Ollama服务: ollama serve"
        }


@app.get("/api/external_models")
async def get_external_models():
    """获取外部模型配置"""
    return {
        "models": [],
        "message": "使用minimal_app.py，外部模型功能受限"
    }

@app.post("/api/chat")
async def chat(request: dict):
    """聊天接口"""
    user_input = request.get("message", "")
    model = request.get("model", "auto")
    
    # 简单响应
    response_text = f"收到消息: {user_input}\n\n"
    response_text += "⚠️ 使用minimal_app.py，功能受限。\n\n"
    response_text += "完整功能请使用:\n"
    response_text += "  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    
    return {
        "success": True,
        "response": response_text,
        "model": model
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("联盟拓荒者 - 最小化启动")
    print("=" * 70)
    print()
    print("访问地址:")
    print("  - 主页: http://localhost:8000/")
    print("  - API文档: http://localhost:8000/docs")
    print()
    print("按 Ctrl+C 停止")
    print("=" * 70)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)