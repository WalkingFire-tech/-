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

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

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
    if frontend_index.exists():
        with open(frontend_index, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"message": "联盟拓荒者 API", "docs": "/docs"}

@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "version": "3.1.1",
        "message": "系统运行正常"
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