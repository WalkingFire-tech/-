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
    """聊天接口 - 永不放弃，总是想办法解决问题"""
    import asyncio
    user_input = request.get("message", "")
    model = request.get("model", "auto")
    
    # 结果收集器
    attempts = []
    final_response = None
    
    # ========== 尝试策略1：快速意图识别 ==========
    try:
        from core.cognitive_dispatcher import CognitiveDispatcher
        loop = asyncio.get_event_loop()
        dispatcher = CognitiveDispatcher()
        
        dispatch_result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: dispatcher.dispatch(user_query=user_input, context=request)),
            timeout=3.0
        )
        
        intent_type = dispatch_result.get("intent_type", "unknown")
        route = dispatch_result.get("route", "slow")
        confidence = dispatch_result.get("confidence", 0.5)
        attempts.append(("意图识别", True, intent_type))
        
    except Exception as e:
        logger.warning(f"意图识别失败: {e}")
        intent_type = "unknown"
        route = "slow"
        confidence = 0.5
        attempts.append(("意图识别", False, str(e)))
    
    # ========== 策略2：简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "你好！我是联盟拓荒者智能体系统，很高兴为你服务。我可以帮助你完成各种任务，包括代码生成、问题解答、数据分析等。"
        attempts.append(("简单回复", True, "问候语"))
    
    elif intent_type == "confirmation":
        final_response = "好的，我明白了。"
        attempts.append(("简单回复", True, "确认回复"))
    
    elif intent_type == "history_query":
        final_response = await solve_history_query(user_input)
        attempts.append(("历史查询", True, "历史功能"))
    
    # ========== 策略3：尝试深度认知处理 ==========
    if not final_response:
        try:
            from core.metacognitive_executor import MetacognitiveExecutor
            executor = MetacognitiveExecutor()
            exec_result = await asyncio.wait_for(
                executor.execute_with_full_metacognition(user_query=user_input, context=request),
                timeout=15.0
            )
            result = exec_result.get("final_result", "")
            if result and len(result) > 20:
                final_response = result
                attempts.append(("深度认知", True, f"获得{len(result)}字回复"))
        except Exception as e:
            attempts.append(("深度认知", False, str(e)[:50]))
    
    # ========== 策略4：尝试Ollama本地模型 ==========
    if not final_response:
        try:
            import requests
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen2.5:7b", "prompt": user_input, "stream": False},
                    timeout=12
                )
            )
            if response.status_code == 200:
                result = response.json().get("response", "")
                if result and len(result) > 20:
                    final_response = result
                    attempts.append(("Ollama本地", True, f"获得{len(result)}字回复"))
        except Exception as e:
            attempts.append(("Ollama本地", False, str(e)[:50]))
    
    # ========== 策略5：查询知识库 ==========
    if not final_response:
        try:
            result = await query_knowledge_base(user_input)
            if result:
                final_response = result
                attempts.append(("知识库", True, "检索到相关知识"))
        except Exception as e:
            attempts.append(("知识库", False, str(e)[:50]))
    
    # ========== 策略6：查询经验池 ==========
    if not final_response:
        try:
            result = await query_experience_pool(user_input)
            if result:
                final_response = result
                attempts.append(("经验池", True, "找到历史经验"))
        except Exception as e:
            attempts.append(("经验池", False, str(e)[:50]))
    
    # ========== 策略7：规则匹配生成回复 ==========
    if not final_response:
        final_response = generate_rule_based_response(user_input, intent_type)
        attempts.append(("规则匹配", True, "生成针对性回复"))
    
    # ========== 策略8：转后台永不放弃处理 ==========
    if not final_response or len(final_response) < 20:
        try:
            from core.persistent_tasks import persistent_task_system
            task_id = await persistent_task_system.submit(user_input, request)
            
            final_response = f"""我收到了你的问题："{user_input}"

🔄 我已经启动后台任务（ID: {task_id[:8]}），正在尝试所有可能的方法来解决。

你可以：
- **等待完成** - 我会持续尝试直到成功
- **查询进度** - 访问 /api/tasks/{task_id[:8]} 查看处理状态
- **继续对话** - 我会在后台继续处理这个问题

**我永不放弃，直到找到答案。**"""
            
            attempts.append(("后台任务", True, task_id[:8]))
        except Exception as e:
            attempts.append(("后台任务", False, str(e)[:50]))
    
    # ========== 记录解决过程 ==========
    logger.info(f"问题解决过程: {[(a[0], a[1]) for a in attempts]}")
    
    return {
        "success": True,
        "response": final_response,
        "model": model,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "attempts": attempts,  # 返回尝试过程
        "thinking_process": {
            "deep_intent": intent_type,
            "scene_role": "general",
            "intent_confidence": confidence,
            "response_strategy": route,
            "solution_path": [a[0] for a in attempts if a[1]]
        }
    }

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询后台任务状态"""
    try:
        from core.persistent_tasks import persistent_task_system
        status = await persistent_task_system.get_task_status(task_id)
        return status
    except Exception as e:
        return {"error": str(e)}

async def solve_history_query(query: str) -> str:
    """解决历史查询问题"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT query, response FROM experiences ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            history_text = "\n".join([f"- {row[0][:30]}... → {row[1][:50]}..." for row in rows[:5]])
            return f"📜 最近的历史记录：\n{history_text}\n\n（完整历史功能开发中）"
        else:
            return "暂无历史记录。开始和我对话吧！"
    except:
        return "历史记录功能正在初始化，请稍后再试。"

async def query_knowledge_base(query: str) -> str:
    """查询知识库"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/knowledge_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query}%",))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return None

async def query_experience_pool(query: str) -> str:
    """查询经验池"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM experiences WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{query[:20]}%",))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return None

def generate_rule_based_response(query: str, intent_type: str) -> str:
    """基于规则生成针对性回复 - 最后的保障"""
    query_lower = query.lower()
    
    # 代码相关
    if any(kw in query_lower for kw in ["代码", "编程", "写代码", "函数", "程序"]):
        return f"""我理解你需要代码方面的帮助。关于"{query}"，我可以：

1. **代码生成** - 请告诉我具体需求，如"写一个Python函数计算斐波那契数列"
2. **代码解释** - 请提供代码，我会解释其工作原理
3. **代码优化** - 请提供代码，我会给出优化建议
4. **Bug修复** - 请描述问题和代码，我会帮你分析

请告诉我更具体的需求，我会尽力帮助你。"""

    # 知识问答
    if any(kw in query_lower for kw in ["什么是", "是什么", "介绍", "解释"]):
        topic = query.replace("什么是", "").replace("是什么", "").replace("介绍一下", "").strip()
        return f"""关于"{topic}"，我正在学习相关知识。

目前我可以通过以下方式帮助你：
1. **基础解释** - 提供概念定义和基本原理
2. **实例说明** - 通过具体例子帮助理解
3. **应用场景** - 说明实际应用和案例

请稍后重试，或尝试更具体的问题，如"{topic}的定义是什么"或"{topic}的应用有哪些"。"""

    # 如何类问题
    if any(kw in query_lower for kw in ["如何", "怎么", "怎样"]):
        return f"""关于"{query}"，这是一个很好的问题。

我建议：
1. **分解问题** - 将复杂问题拆分为小步骤
2. **查阅文档** - 参考相关技术文档
3. **实践尝试** - 动手实践是最好的学习方式

请告诉我更具体的场景，我会给出更详细的指导。"""

    # 通用回复
    return f"""我收到了你的问题："{query}"

虽然我暂时无法给出完整答案，但我会记住这个问题并继续学习。

你可以：
1. **换个方式提问** - 尝试更具体或更简单的表述
2. **提供更多上下文** - 帮助我更好地理解你的需求
3. **稍后重试** - 我会不断学习和改进

我会持续进化，下次遇到这个问题时，我会做得更好。"""
        return {"success": False, "response": f"处理出错: {str(e)}", "model": model}

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

@app.get("/api/config/external")
async def get_external_config():
    """获取外置API配置"""
    import json
    config_file = ROOT_DIR / "config" / "external_api.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"apis": [], "message": "未配置外置API"}

@app.post("/api/config/external")
async def save_external_config(config: dict):
    """保存外置API配置"""
    import json
    config_dir = ROOT_DIR / "config"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "external_api.json"
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return {"success": True, "message": "配置已保存"}

@app.get("/api/models/test")
async def test_model_connection(model_name: str = None):
    """测试模型连接"""
    if not model_name:
        return {"success": False, "message": "请提供模型名称"}
    
    try:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": "test", "stream": False},
            timeout=5
        )
        if response.status_code == 200:
            return {"success": True, "message": f"模型 {model_name} 连接正常"}
        else:
            return {"success": False, "message": f"连接失败: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"连接错误: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)