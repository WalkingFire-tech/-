import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    
    # 加载模型适配器
    adapters = {}
    
    # 尝试加载Ollama模型
    try:
        adapters["mindchat"] = OllamaAdapter(model_name="mindchat")
        logger.info("Loaded MindChat")
    except Exception as e:
        logger.warning(f"MindChat unavailable: {e}")
    
    try:
        adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
        logger.info("Loaded code_light (qwen2.5-coder:1.5b)")
    except Exception as e:
        logger.warning(f"Code light model unavailable: {e}")
    
    try:
        adapters["deepcoder"] = OllamaAdapter(model_name="deepcoder")
        logger.info("Loaded DeepCoder")
    except Exception as e:
        logger.warning(f"DeepCoder unavailable: {e}")
    
    # 尝试加载远程模型
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
    
    # 确保至少有一个适配器（降级方案）
    if not adapters:
        from adapters.llm.mock_adapter import MockAdapter
        adapters["mock"] = MockAdapter()
        logger.warning("所有模型不可用，使用Mock适配器作为降级方案")
    else:
        logger.info(f"已加载 {len(adapters)} 个模型适配器: {list(adapters.keys())}")
    
    planner = Planner(adapters)
    
    # 确保能力矩阵已初始化
    try:
        from infrastructure.model_capability import model_capability
        for name in adapters:
            model_capability.ensure_model_registered(name)
        logger.info("能力矩阵已就绪")
    except Exception as e:
        logger.warning(f"能力矩阵初始化失败: {e}")
    
    # 启动章程执行器后台任务
    try:
        import threading
        import time
        from datetime import datetime
        from infrastructure.charter_executor import charter_executor
        from infrastructure.health_dashboard import health_dashboard
        from infrastructure.counterfactual_simulator import counterfactual_simulator
        
        def charter_background_tasks():
            """章程后台任务：健康监控、失败回顾、反事实模拟、资源管理"""
            while True:
                try:
                    # 每6小时检查健康度
                    health_metrics = health_dashboard.calculate_aphi()
                    logger.info(f"健康度检查: APHI={health_metrics['aphi']}, 模式={health_metrics['mode']}")
                    
                    # 每日回顾失败案例
                    charter_executor.review_failures()
                    
                    # 每日监控功能使用
                    charter_executor.monitor_feature_usage()
                    
                    # 每日应用反事实洞察
                    applied = counterfactual_simulator.apply_insights()
                    if applied > 0:
                        logger.info(f"应用了 {applied} 条反事实洞察")
                    
                    # 每周归档旧经验（周一执行）
                    if datetime.now().weekday() == 0:
                        charter_executor.archive_old_experiences(days=90, min_importance=0.3)
                        
                    # 检查资源限制
                    resource_check = charter_executor.check_resource_limits()
                    if not resource_check['within_limits']:
                        charter_executor.enforce_resource_limits()
                        
                except Exception as e:
                    logger.error(f"章程后台任务失败: {e}")
                
                time.sleep(21600)  # 每6小时执行一次
        
        threading.Thread(target=charter_background_tasks, daemon=True).start()
        logger.info("章程守护线程已启动（健康监控+反事实模拟+资源管理）")
        
    except Exception as e:
        logger.warning(f"章程执行器启动失败: {e}")
    
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

# 挂载前端静态文件
FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/")
async def root():
    """根路径返回前端页面"""
    frontend_index = FRONTEND_DIR / "index.html"
    if frontend_index.exists():
        from fastapi.responses import HTMLResponse
        with open(frontend_index, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"message": "联盟拓荒者 API", "docs": "/docs"}

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
    
    try:
        # 解析意图
        intent = intent_parser.parse(user_input)
        
        # 捕获 planner 的响应（通过事件总线）
        response_queue = asyncio.Queue()
        
        def on_response(data):
            response_queue.put_nowait(data)
        
        bus.subscribe("plan_executed", on_response)
        
        # 执行规划（同步方法，但我们在异步上下文中调用）
        planner.plan(intent)
        
        # 等待响应（超时 60 秒）
        try:
            response = await asyncio.wait_for(response_queue.get(), timeout=60.0)
            return {"response": response, "intent": intent.type}
        except asyncio.TimeoutError:
            logger.error("请求超时")
            return {"error": "Timeout", "intent": intent.type}
        
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        return {"error": str(e)}
    
    finally:
        try:
            bus.unsubscribe("plan_executed", on_response)
        except:
            pass

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

@app.post("/api/feedback")
async def send_feedback(request: dict):
    """接收用户反馈"""
    score = request.get("score", 0)
    
    try:
        import sqlite3
        
        # 更新最近一条经验的反馈
        conn = sqlite3.connect('experience_pool.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE experiences
            SET user_feedback = ?
            WHERE id = (
                SELECT id FROM experiences
                ORDER BY timestamp DESC
                LIMIT 1
            )
        """, (score,))
        
        conn.commit()
        conn.close()
        
        # 触发学习机会
        if score < 0:
            from infrastructure.event_bus import bus
            bus.publish("learning_opportunity", {
                'type': 'explicit_negative_feedback',
                'action': 'trigger_induction'
            })
            
            # 新增：规则降级机制
            _handle_negative_feedback_for_rules()
        
        logger.info(f"收到用户反馈: {score}")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"反馈处理失败: {e}")
        return {"success": False, "error": str(e)}

def _handle_negative_feedback_for_rules():
    """处理负面反馈对规则的影响"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        # 查找最近应用的规则（5分钟内）
        cutoff_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        with sqlite3.connect("learning_rules.db") as conn:
            # 增加拒绝计数
            cursor = conn.execute('''
                UPDATE learning_rules
                SET user_rejection_count = user_rejection_count + 1
                WHERE status = 'active'
                  AND last_applied >= ?
            ''', (cutoff_time,))
            
            affected = cursor.rowcount
            
            # 标记连续两次负面反馈的规则为expired
            cursor = conn.execute('''
                UPDATE learning_rules
                SET status = 'expired'
                WHERE status = 'active'
                  AND user_rejection_count >= 2
            ''')
            
            expired = cursor.rowcount
            conn.commit()
            
            if expired > 0:
                logger.warning(f"已标记 {expired} 条规则为过期（用户连续负面反馈）")
                
                # 触发重新学习
                from infrastructure.event_bus import bus
                bus.publish("rule_expired", {
                    'count': expired,
                    'action': 're_induction_needed'
                })
                
    except Exception as e:
        logger.warning(f"规则降级处理失败: {e}")

# ========== 外部模型配置API ==========

@app.get("/api/external_models")
async def list_external_models():
    """列出所有外部模型配置"""
    try:
        from infrastructure.external_model_config import external_model_config
        models = external_model_config.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"列出模型失败: {e}")
        return {"models": [], "error": str(e)}

@app.post("/api/external_models")
async def add_external_model(request: Request):
    """添加外部模型配置"""
    try:
        from infrastructure.external_model_config import external_model_config
        data = await request.json()
        
        success = external_model_config.add_model(
            name=data["name"],
            api_url=data["api_url"],
            api_key=data["api_key"],
            daily_limit=data.get("daily_limit", 1000)
        )
        
        if success:
            return {"success": True, "message": "模型已添加"}
        else:
            return {"success": False, "error": "添加失败"}
            
    except Exception as e:
        logger.error(f"添加模型失败: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/external_models/{name}")
async def delete_external_model(name: str):
    """删除外部模型配置"""
    try:
        from infrastructure.external_model_config import external_model_config
        success = external_model_config.delete_model(name)
        
        if success:
            return {"success": True, "message": "模型已删除"}
        else:
            return {"success": False, "error": "删除失败"}
            
    except Exception as e:
        logger.error(f"删除模型失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/external_models/test")
async def test_external_model(request: Request):
    """测试外部模型连接"""
    try:
        import requests
        from infrastructure.external_model_config import external_model_config
        
        data = await request.json()
        name = data.get("name")
        
        # 获取模型配置
        model = external_model_config.get_model(name)
        if not model:
            return {"success": False, "message": "模型不存在"}
        
        # 检查配额
        if not external_model_config.check_quota(name):
            return {"success": False, "message": "已超出每日配额"}
        
        # 发送测试请求
        try:
            # 根据API类型调整测试方式
            if "openai" in model['api_url'].lower():
                # OpenAI风格API
                response = requests.post(
                    f"{model['api_url']}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {model['api_key']}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    },
                    timeout=10
                )
            else:
                # 通用测试
                response = requests.get(
                    f"{model['api_url']}/v1/models",
                    headers={"Authorization": f"Bearer {model['api_key']}"},
                    timeout=10
                )
            
            if response.status_code == 200:
                external_model_config.record_usage(name, tokens=1, success=True)
                return {"success": True, "message": "连接成功"}
            else:
                external_model_config.record_usage(name, tokens=0, success=False, error=f"HTTP {response.status_code}")
                return {"success": False, "message": f"HTTP {response.status_code}: {response.text[:100]}"}
                
        except requests.Timeout:
            external_model_config.record_usage(name, tokens=0, success=False, error="Timeout")
            return {"success": False, "message": "连接超时"}
        except Exception as e:
            external_model_config.record_usage(name, tokens=0, success=False, error=str(e))
            return {"success": False, "message": f"连接失败: {str(e)}"}
            
    except Exception as e:
        logger.error(f"测试模型失败: {e}")
        return {"success": False, "message": str(e)}

@app.get("/api/external_models/{name}/stats")
async def get_external_model_stats(name: str):
    """获取外部模型使用统计"""
    try:
        from infrastructure.external_model_config import external_model_config
        stats = external_model_config.get_usage_stats(name)
        model = external_model_config.get_model(name)
        
        if model:
            return {
                "name": name,
                "used_today": model['used_today'],
                "daily_limit": model['daily_limit'],
                "remaining": model['daily_limit'] - model['used_today'],
                **stats
            }
        else:
            return {"error": "模型不存在"}
            
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return {"error": str(e)}

# ========== 联邦调度API ==========

@app.get("/api/capability_matrix")
async def get_capability_matrix():
    """获取能力矩阵"""
    try:
        from infrastructure.model_capability import model_capability
        matrix = model_capability.get_capability_matrix()
        stats = model_capability.export_stats()
        
        return {
            "matrix": matrix,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取能力矩阵失败: {e}")
        return {"error": str(e)}

@app.post("/api/capability_matrix/register")
async def register_model_capability(request: dict):
    """注册模型能力"""
    try:
        from infrastructure.model_capability import model_capability
        
        model_name = request.get("model_name")
        capabilities = request.get("capabilities")
        
        if not model_name:
            return {"success": False, "error": "缺少模型名称"}
        
        model_capability.register_model(model_name, capabilities)
        
        return {"success": True, "message": f"已注册模型: {model_name}"}
        
    except Exception as e:
        logger.error(f"注册模型能力失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/capability_matrix/rank/{task_type}")
async def rank_models_for_task(task_type: str):
    """为任务排序模型"""
    try:
        from infrastructure.model_capability import model_capability
        
        models = list(adapters.keys())
        ranked = model_capability.rank_models_for_task(task_type, models)
        
        return {
            "task_type": task_type,
            "ranking": [
                {"model": model, "score": score}
                for model, score in ranked
            ]
        }
        
    except Exception as e:
        logger.error(f"排序模型失败: {e}")
        return {"error": str(e)}

@app.post("/api/discover_models")
async def discover_models():
    """发现可用模型"""
    try:
        from infrastructure.model_discovery import model_discovery
        
        result = await model_discovery.refresh()
        
        return {
            "success": True,
            "discovered": result['discovered'],
            "sources": result['sources'],
            "timestamp": result['timestamp']
        }
        
    except Exception as e:
        logger.error(f"模型发现失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/discovered_models")
async def get_discovered_models():
    """获取已发现的模型"""
    try:
        from infrastructure.model_discovery import model_discovery
        models = model_discovery.get_discovered_models()
        
        return {"models": models}
        
    except Exception as e:
        logger.error(f"获取发现模型失败: {e}")
        return {"models": [], "error": str(e)}

@app.get("/api/parallel_stats")
async def get_parallel_stats():
    """获取并行调度统计"""
    try:
        from infrastructure.parallel_scheduler import parallel_scheduler
        stats = parallel_scheduler.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"获取并行统计失败: {e}")
        return {"error": str(e)}

# ========== 模型热加载API ==========

@app.post("/api/models/add")
async def add_model(request: dict):
    """动态添加模型"""
    global adapters
    
    model_name = request.get("name")
    model_type = request.get("type", "ollama")  # ollama, remote, mock
    
    if not model_name:
        return {"success": False, "error": "模型名称不能为空"}
    
    if model_name in adapters:
        return {"success": False, "error": f"模型 {model_name} 已存在"}
    
    try:
        if model_type == "ollama":
            from adapters.llm.ollama_adapter import OllamaAdapter
            adapters[model_name] = OllamaAdapter(model_name=model_name)
            
        elif model_type == "remote":
            api_url = request.get("api_url")
            api_key = request.get("api_key")
            if not api_url or not api_key:
                return {"success": False, "error": "远程模型需要api_url和api_key"}
            
            from adapters.llm.remote_adapter import RemoteAdapter
            adapters[model_name] = RemoteAdapter(model_name=model_name)
            
        elif model_type == "mock":
            from adapters.llm.mock_adapter import MockAdapter
            adapters[model_name] = MockAdapter()
        else:
            return {"success": False, "error": f"不支持的模型类型: {model_type}"}
        
        # 注册到能力矩阵
        from infrastructure.model_capability import model_capability
        model_capability.ensure_model_registered(model_name)
        
        logger.info(f"成功添加模型: {model_name} (类型: {model_type})")
        return {"success": True, "model": model_name, "type": model_type}
        
    except Exception as e:
        logger.error(f"添加模型失败: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/models/{model_name}")
async def remove_model(model_name: str):
    """移除模型"""
    global adapters
    
    if model_name not in adapters:
        return {"success": False, "error": f"模型 {model_name} 不存在"}
    
    if len(adapters) <= 1:
        return {"success": False, "error": "至少需要保留一个模型"}
    
    try:
        del adapters[model_name]
        logger.info(f"已移除模型: {model_name}")
        return {"success": True, "model": model_name}
        
    except Exception as e:
        logger.error(f"移除模型失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/models/{model_name}/test")
async def test_model(model_name: str):
    """测试模型连接"""
    if model_name not in adapters:
        return {"success": False, "error": f"模型 {model_name} 不存在"}
    
    try:
        adapter = adapters[model_name]
        
        # 测试简单生成
        test_prompt = "Hello, this is a test."
        
        import asyncio
        if asyncio.iscoroutinefunction(adapter.generate):
            response = await asyncio.wait_for(
                adapter.generate(test_prompt),
                timeout=10.0
            )
        else:
            response = await asyncio.to_thread(adapter.generate, test_prompt)
        
        # 记录成功
        from infrastructure.model_health_checker import model_health_checker
        model_health_checker.record_success(model_name, 1.0)
        
        return {
            "success": True,
            "model": model_name,
            "response_preview": response[:100] if response else None
        }
        
    except asyncio.TimeoutError:
        from infrastructure.model_health_checker import model_health_checker
        model_health_checker.record_failure(model_name, "timeout", "Test timeout")
        return {"success": False, "error": "连接超时"}
        
    except Exception as e:
        from infrastructure.model_health_checker import model_health_checker
        model_health_checker.record_failure(model_name, "test_failed", str(e))
        logger.error(f"测试模型失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/models/{model_name}/health")
async def get_model_health(model_name: str):
    """获取模型健康状态"""
    try:
        from infrastructure.model_health_checker import model_health_checker
        
        health = model_health_checker.get_model_health(model_name)
        
        return {
            "model": model_name,
            "health": health
        }
        
    except Exception as e:
        logger.error(f"获取健康状态失败: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)