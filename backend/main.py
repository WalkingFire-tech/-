import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from loguru import logger

# 将项目根目录加入 Python 路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from infrastructure.event_bus import bus
from core.services.intent_parser import IntentParser
from core.services.planner import Planner
from adapters.llm.ollama_adapter import OllamaAdapter
from adapters.llm.remote_adapter import RemoteAdapter
from infrastructure.logger import CampfireLogger
from infrastructure.model_stats import ModelStats
from infrastructure.config_manager import config
from dotenv import load_dotenv

load_dotenv()

# 全局实例（在 lifespan 中初始化）
planner = None
intent_parser = None
campfire = None
adapters = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    global planner, intent_parser, campfire, adapters
    
    logger.info("启动后端服务...")
    
    campfire = CampfireLogger()
    intent_parser = IntentParser()
    
    # 加载模型适配器（与原有 main.py 类似）
    adapters = {}
    
    try:
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("Loaded MindChat")
    except Exception as e:
        logger.warning(f"MindChat unavailable: {e}")
    
    try:
        adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
        logger.info("Loaded code model")
    except Exception as e:
        logger.warning(f"Code model unavailable: {e}")
    
    try:
        if os.getenv("OPENAI_API_KEY"):
            adapters["remote_gpt4"] = RemoteAdapter(model_name="gpt-4o-mini")
            logger.info("Loaded remote GPT")
    except Exception as e:
        logger.warning(f"Remote GPT unavailable: {e}")
    
    try:
        if os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"):
            adapters["deepseek-chat"] = RemoteAdapter(model_name="deepseek-chat")
            logger.info("Loaded DeepSeek Chat")
    except Exception as e:
        logger.warning(f"DeepSeek Chat unavailable: {e}")
    
    # 确保至少有一个适配器
    if not adapters:
        from adapters.llm.mock_adapter import MockAdapter
        adapters["default"] = MockAdapter()
        logger.warning("使用Mock适配器作为降级方案")
    
    planner = Planner(adapters)
    
    logger.info("后端服务初始化完成")
    
    yield
    
    # 关闭时清理
    logger.info("后端服务关闭")

app = FastAPI(
    title="联盟拓荒者 API",
    description="生产级自我进化智能体系统 API",
    version="3.1.1",
    lifespan=lifespan
)

# 允许前端跨域（Tauri 默认允许本地访问，但开发时可能跨端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    """健康检查端点"""
    return {
        "status": "ok",
        "version": "3.1.1",
        "models": list(adapters.keys())
    }

@app.get("/api/models")
async def get_models():
    """获取可用模型列表"""
    return {
        "models": [
            {"name": name, "type": type(adapter).__name__}
            for name, adapter in adapters.items()
        ]
    }

@app.post("/api/chat")
async def chat(request: dict):
    """聊天端点"""
    user_input = request.get("message", "")
    
    if not user_input:
        return {"error": "Empty message"}
    
    # 解析意图
    intent = intent_parser.parse(user_input)
    
    # 捕获 planner 的响应（通过事件总线）
    response_queue = asyncio.Queue()
    
    def on_response(data):
        response_queue.put_nowait(data)
    
    bus.subscribe("plan_executed", on_response)
    
    try:
        # 执行规划（同步方法，但我们在异步上下文中调用）
        planner.plan(intent)
        
        # 等待响应（超时 60 秒）
        response = await asyncio.wait_for(response_queue.get(), timeout=60.0)
        return {"response": response, "intent": intent.type}
    
    except asyncio.TimeoutError:
        logger.error("请求超时")
        return {"error": "Timeout"}
    
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        return {"error": str(e)}
    
    finally:
        bus.unsubscribe("plan_executed", on_response)

@app.post("/api/optimize")
async def run_optimize(request: dict):
    """运行贝叶斯优化"""
    n_iterations = request.get("iterations", 20)
    
    try:
        from meta.controller import MetaController
        controller = MetaController()
        result = controller.run_manual_optimization(
            method="bayesian",
            n_iterations=n_iterations
        )
        return {"success": True, "result": str(result)}
    except Exception as e:
        logger.error(f"优化失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/induction")
async def run_induction(request: dict):
    """运行归纳总结"""
    days = request.get("days", 7)
    
    try:
        from meta.induction import induction_scheduler
        result = induction_scheduler.run_induction(days=days)
        return {
            "success": result.get("success", False),
            "patterns": result.get("patterns", 0),
            "rules": result.get("rules", 0),
            "message": result.get("message", "")
        }
    except Exception as e:
        logger.error(f"归纳失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    try:
        import sqlite3
        
        # 经验池统计
        conn_exp = sqlite3.connect('experience_pool.db')
        cur = conn_exp.execute("SELECT COUNT(*) FROM experiences")
        exp_count = cur.fetchone()[0]
        conn_exp.close()
        
        # 学习规则统计
        conn_rules = sqlite3.connect('learning_rules.db')
        cur = conn_rules.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
        active_rules = cur.fetchone()[0]
        cur = conn_rules.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
        pending_rules = cur.fetchone()[0]
        conn_rules.close()
        
        return {
            "experiences": exp_count,
            "active_rules": active_rules,
            "pending_rules": pending_rules,
            "models": len(adapters)
        }
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)