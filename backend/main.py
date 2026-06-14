import sys
import os
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
from loguru import logger

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

planner = None
intent_parser = None
campfire = None
adapters = {}
adapters_lock = threading.Lock()

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
    
    planner = Planner(adapters, adapters_lock=adapters_lock)
    
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
        import schedule
        from infrastructure.charter_executor import charter_executor
        from infrastructure.health_dashboard import health_dashboard
        from infrastructure.counterfactual_simulator import counterfactual_simulator
        
        def health_check():
            """健康度检查"""
            try:
                health_metrics = health_dashboard.calculate_aphi()
                logger.info(f"健康度检查: APHI={health_metrics['aphi']}, 模式={health_metrics['mode']}")
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
        
        def review_failures():
            """失败案例回顾"""
            try:
                charter_executor.review_failures()
            except Exception as e:
                logger.error(f"失败回顾失败: {e}")
        
        def monitor_usage():
            """功能使用监控"""
            try:
                charter_executor.monitor_feature_usage()
            except Exception as e:
                logger.error(f"使用监控失败: {e}")
        
        def apply_insights():
            """应用反事实洞察"""
            try:
                applied = counterfactual_simulator.apply_insights()
                if applied > 0:
                    logger.info(f"应用了 {applied} 条反事实洞察")
            except Exception as e:
                logger.error(f"应用洞察失败: {e}")
        
        def archive_experiences():
            """归档旧经验"""
            try:
                charter_executor.archive_old_experiences(days=90, min_importance=0.3)
            except Exception as e:
                logger.error(f"归档失败: {e}")
        
        def check_resources():
            """资源限制检查"""
            try:
                resource_check = charter_executor.check_resource_limits()
                if not resource_check['within_limits']:
                    charter_executor.enforce_resource_limits()
            except Exception as e:
                logger.error(f"资源检查失败: {e}")
        
        # 配置调度任务
        schedule.every(6).hours.do(health_check)
        schedule.every().day.at("02:00").do(review_failures)
        schedule.every().day.at("03:00").do(monitor_usage)
        schedule.every().day.at("04:00").do(apply_insights)
        schedule.every().monday.at("05:00").do(archive_experiences)
        schedule.every().hour.do(check_resources)
        
        def run_scheduler():
            """运行调度器"""
            while True:
                try:
                    schedule.run_pending()
                except Exception as e:
                    logger.error(f"调度执行失败: {e}")
                time.sleep(60)  # 每分钟检查一次
        
        threading.Thread(target=run_scheduler, daemon=True).start()
        logger.info("章程守护线程已启动（使用schedule库精确调度）")
        
    except Exception as e:
        logger.warning(f"章程执行器启动失败: {e}")
    
    logger.info("后端服务初始化完成")
    
    # 启动学习系统
    try:
        from core.learning_engine import learning_engine
        from core.file_monitor import file_monitor
        from core.folder_learner import folder_learner
        from core.active_scheduler import active_scheduler
        
        def learning_callback(file_path: str, event_type: str):
            """文件变化时的学习回调"""
            from core.learning_engine import learning_engine
            learning_engine.add_task(file_path, event_type=event_type)
        
        file_monitor.set_learning_callback(learning_callback)
        learning_engine.start()
        active_scheduler.start()
        
        logger.info("学习系统已启动（引擎+监听+调度器）")
    except Exception as e:
        logger.warning(f"学习系统启动失败: {e}")
    
    yield
    
    # 关闭时清理
    try:
        from core.active_scheduler import active_scheduler
        from core.file_monitor import file_monitor
        from core.learning_engine import learning_engine
        
        active_scheduler.stop()
        file_monitor.stop_all()
        learning_engine.stop()
        
        logger.info("学习系统已关闭")
    except:
        pass
    
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

@app.get("/learning")
async def learning_dashboard():
    """学习仪表盘页面"""
    dashboard_file = FRONTEND_DIR / "learning_dashboard.html"
    if dashboard_file.exists():
        from fastapi.responses import HTMLResponse
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"error": "Learning dashboard not found"}

@app.get("/api/health")
async def health():
    """健康检查端点"""
    with adapters_lock:
        models = list(adapters.keys())
    return {
        "status": "ok",
        "version": "3.1.1",
        "models": models
    }

@app.get("/api/models")
async def get_models():
    """获取可用模型列表"""
    with adapters_lock:
        models_list = [
            {"name": name, "type": type(adapter).__name__}
            for name, adapter in adapters.items()
        ]
    return {"models": models_list}

@app.post("/api/chat")
async def chat(request: dict):
    """聊天端点"""
    user_input = request.get("message", "")
    current_file = request.get("current_file", None)
    current_topic = request.get("current_topic", None)
    
    if not user_input:
        return {"error": "Empty message"}
    
    try:
        intent = intent_parser.parse(user_input)
        
        if campfire:
            campfire.log_user(user_input)
        
        # 环境触发器匹配
        env_hint = None
        try:
            from core.learning import enhanced_learner
            env_matches = enhanced_learner.match_environmental_triggers(current_file, current_topic)
            if env_matches:
                env_hint = f"💡 看到你在{current_file or '这个话题'}，我突然想起：{env_matches[0][0][:100]}... 需要我详细说说吗？"
                logger.info(f"环境触发器命中: {current_file or current_topic}")
        except Exception as e:
            logger.error(f"环境触发器匹配失败: {e}")
        
        response_queue = asyncio.Queue()
        
        def on_response(data):
            response_queue.put_nowait(data)
        
        bus.subscribe("plan_executed", on_response)
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, planner.plan, intent)
            
            try:
                response = await asyncio.wait_for(response_queue.get(), timeout=60.0)
                
                if campfire and response:
                    campfire.log_assistant(str(response)[:1000])
                
                response_text = str(response) if response else ""
                
                # 检索知识（支持回忆语气）
                knowledge_result = None
                try:
                    from core.learning import enhanced_learner
                    knowledge_result = enhanced_learner.retrieve_knowledge(user_input)
                    
                    if knowledge_result and knowledge_result.get('confidence', 0) > 0.6:
                        answer = knowledge_result['answer']
                        
                        # 回忆语气
                        if knowledge_result.get('reconstructed'):
                            answer = "🤔 让我努力回想一下……（记忆有些模糊）\n\n" + answer
                        
                        # 环境提示
                        if env_hint:
                            answer = env_hint + "\n\n" + answer
                        
                        logger.info(f"知识检索命中: {knowledge_result['source']} ({knowledge_result['confidence']:.2f})")
                except Exception as e:
                    logger.error(f"知识检索失败: {e}")
                
                try:
                    from core.vector_retriever import vector_retriever
                    
                    vector_results = vector_retriever.hybrid_search(
                        query=user_input,
                        top_k=3
                    )
                    
                    if vector_results:
                        best_match = vector_results[0]
                        if best_match.get('final_score', 0) > 0.6:
                            logger.info(f"向量检索命中: {best_match['final_score']:.2f}")
                except Exception as e:
                    logger.error(f"向量检索失败: {e}")
                
                try:
                    from core.learning import enhanced_learner
                    external_result = enhanced_learner.learn_with_external(
                        user_input=user_input,
                        context=json.dumps({"intent": intent.type}),
                        response_text=response_text,
                        confidence=0.8,
                        auto_trigger=True
                    )
                    
                    if external_result.get("external_triggered"):
                        logger.info(f"外部学习触发: {external_result.get('reason')}")
                        
                        if external_result.get("new_knowledge_count") > 0:
                            external_knowledge = external_result.get("items", [])
                            for item in external_knowledge:
                                if item.get("knowledge_type") == "meta":
                                    response_text += f"\n\n[外部学习] {item.get('question', '')}"
                except Exception as e:
                    logger.error(f"外部学习失败: {e}")
                
                try:
                    from core.folder_learner import folder_learner
                    
                    user_lower = user_input.lower()
                    
                    if any(phrase in user_lower for phrase in ["学习进度", "文件夹学习", "学了多少", "学习状态"]):
                        summary = folder_learner.get_summary()
                        status = folder_learner.get_status()
                        
                        folder_response = f"""📚 文件夹学习进度报告：
- 学习根目录: {summary.get('root_path', '未设置')}
- 已扫描文件: {summary.get('total_files', 0)} 个
- 成功学习: {summary.get('successful', 0)} 个
- 学习失败: {summary.get('failed', 0)} 个
- 提取知识: {summary.get('total_knowledge', 0)} 条
- 最后扫描: {summary.get('last_scan', '从未')}
- 后台监控: {'运行中' if status.get('running') else '已停止'}"""
                        
                        return {"response": folder_response, "intent": "folder_learning_status"}
                    
                    elif "显示失败" in user_lower or "失败文件" in user_lower:
                        failed_files = folder_learner.get_failed_files()
                        
                        if not failed_files:
                            return {"response": "✅ 没有学习失败的文件", "intent": "folder_learning_failed"}
                        
                        failed_response = "❌ 学习失败的文件：\n"
                        for f in failed_files[:10]:
                            failed_response += f"- {f['relative_path']}: {f['error_msg']}\n"
                        
                        return {"response": failed_response, "intent": "folder_learning_failed"}
                    
                    elif "最近学习" in user_lower or "学习历史" in user_lower:
                        recent_files = folder_learner.get_recent_learned()
                        
                        if not recent_files:
                            return {"response": "暂无学习记录", "intent": "folder_learning_recent"}
                        
                        recent_response = "📖 最近学习的文件：\n"
                        for f in recent_files:
                            status_icon = "✅" if f['status'] == 'success' else "❌"
                            recent_response += f"{status_icon} {f['relative_path']} ({f['knowledge_count']}条知识)\n"
                        
                        return {"response": recent_response, "intent": "folder_learning_recent"}
                    
                    notifications = folder_learner.pop_notifications()
                    if notifications:
                        notif = notifications[-1]
                        notification_msg = f"\n\n✨ [自动学习通知] 我刚学习了 {notif['new']} 个新文件，更新了 {notif['updated']} 个文件"
                        if notif['failed'] > 0:
                            notification_msg += f"，{notif['failed']} 个失败"
                        
                        if isinstance(response, str):
                            response = response + notification_msg
                        else:
                            response = str(response) + notification_msg
                except Exception as e:
                    logger.error(f"文件夹学习对话处理失败: {e}")
                
                # 如果有高质量检索结果，优先使用
                if knowledge_result and knowledge_result.get('confidence', 0) > 0.7:
                    return {
                        "response": knowledge_result['answer'],
                        "intent": intent.type,
                        "source": knowledge_result['source'],
                        "reconstructed": knowledge_result.get('reconstructed', False)
                    }
                
                return {"response": response, "intent": intent.type}
            except asyncio.TimeoutError:
                logger.error("请求超时")
                return {"error": "Timeout", "intent": intent.type}
        finally:
            try:
                bus.unsubscribe("plan_executed", on_response)
            except:
                pass
        
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        return {"error": str(e)}

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
        
        if result.get("success"):
            return {
                "success": True,
                "patterns": result.get("patterns", 0),
                "rules": result.get("rules", 0),
                "message": result.get("message", "")
            }
        else:
            return {
                "success": False,
                "error": result.get("error") or result.get("message") or "归纳失败",
                "patterns": 0,
                "rules": 0
            }
    except Exception as e:
        logger.error(f"归纳失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    try:
        import sqlite3
        
        with sqlite3.connect('data/experience_pool.db') as conn_exp:
            cur = conn_exp.execute("SELECT COUNT(*) FROM experiences")
            exp_count = cur.fetchone()[0]
        
        with sqlite3.connect('data/learning_rules.db') as conn_rules:
            cur = conn_rules.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = cur.fetchone()[0]
            cur = conn_rules.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
            pending_rules = cur.fetchone()[0]
        
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
    """接收用户反馈并自动学习"""
    score = request.get("score", 0)
    
    try:
        import sqlite3
        
        with sqlite3.connect('data/experience_pool.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取最近一条经验
            cursor.execute("""
                SELECT id, raw_input, response, intent_type, quality_score
                FROM experiences
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            last_exp = cursor.fetchone()
            
            if last_exp:
                # 更新反馈
                cursor.execute("""
                    UPDATE experiences
                    SET user_feedback = ?
                    WHERE id = ?
                """, (score, last_exp['id']))
                
                conn.commit()
                
                # 如果用户点赞（正面反馈），自动学习保存到知识库
                if score > 0 and last_exp['response']:
                    try:
                        from infrastructure.knowledge_injector import KnowledgeInjector
                        
                        knowledge_injector = KnowledgeInjector()
                        
                        # 保存为知识点
                        knowledge_injector.inject_knowledge(
                            question=last_exp['raw_input'],
                            answer=last_exp['response'][:1000],  # 限制长度
                            source="user_feedback_positive",
                            intent_type=last_exp['intent_type'],
                            metadata={
                                'quality_score': last_exp['quality_score'],
                                'type': 'conversation_learning'
                            }
                        )
                        
                        logger.info(f"从用户反馈学习: {last_exp['raw_input'][:50]}...")
                    except Exception as e:
                        logger.warning(f"自动学习失败: {e}")
        
        if score < 0:
            from infrastructure.event_bus import bus
            bus.publish("learning_opportunity", {
                'type': 'explicit_negative_feedback',
                'action': 'trigger_induction'
            })
            
            _handle_negative_feedback_for_rules()
        
        logger.info(f"收到用户反馈: {score}")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"反馈处理失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/folder/set_root")
async def set_folder_root(request: dict):
    """设置学习根目录"""
    root_path = request.get("path", "")
    
    try:
        from core.folder_learner import folder_learner
        
        result = folder_learner.set_root_path(root_path)
        
        if result.get("success"):
            return {
                "success": True,
                "root_path": result["root_path"],
                "message": f"已设置学习根目录: {result['root_path']}"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "未知错误")
            }
    except Exception as e:
        logger.error(f"设置根目录失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/folder/scan")
async def scan_folder(request: dict):
    """扫描并学习文件夹"""
    start_monitor = request.get("start_monitor", False)
    interval = request.get("interval", 300)
    
    try:
        from core.folder_learner import folder_learner
        
        if not folder_learner.root_path:
            return {
                "success": False,
                "error": "请先设置学习根目录"
            }
        
        result = folder_learner.scan_and_learn()
        
        if start_monitor:
            folder_learner.start_background_monitor(interval_seconds=interval)
        
        return {
            "success": True,
            "result": result,
            "summary": folder_learner.get_summary()
        }
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/folder/status")
async def get_folder_status():
    """获取文件夹学习状态"""
    try:
        from core.folder_learner import folder_learner
        
        return {
            "success": True,
            "status": folder_learner.get_status(),
            "summary": folder_learner.get_summary(),
            "notifications": folder_learner.pop_notifications()
        }
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/folder/failed")
async def get_failed_files():
    """获取学习失败的文件"""
    try:
        from core.folder_learner import folder_learner
        
        return {
            "success": True,
            "failed_files": folder_learner.get_failed_files()
        }
    except Exception as e:
        logger.error(f"获取失败文件失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/folder/recent")
async def get_recent_learned():
    """获取最近学习的文件"""
    try:
        from core.folder_learner import folder_learner
        
        return {
            "success": True,
            "recent_files": folder_learner.get_recent_learned()
        }
    except Exception as e:
        logger.error(f"获取最近学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/folder/relearn")
async def relearn_file(request: dict):
    """重新学习指定文件"""
    file_pattern = request.get("pattern", "")
    
    try:
        from core.folder_learner import folder_learner
        
        if not folder_learner.root_path:
            return {
                "success": False,
                "error": "请先设置学习根目录"
            }
        
        found = False
        for file_path in folder_learner.root_path.rglob("*"):
            if file_path.is_file() and file_pattern in str(file_path):
                result = folder_learner.learn_single_file(file_path, force=True)
                found = True
                
                return {
                    "success": True,
                    "result": result,
                    "file": str(file_path)
                }
        
        if not found:
            return {
                "success": False,
                "error": f"未找到匹配 '{file_pattern}' 的文件"
            }
    except Exception as e:
        logger.error(f"重新学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/folder/monitor/start")
async def start_monitor(request: dict):
    """启动后台监控"""
    interval = request.get("interval", 300)
    
    try:
        from core.folder_learner import folder_learner
        
        folder_learner.start_background_monitor(interval_seconds=interval)
        
        return {
            "success": True,
            "message": f"已启动后台监控，间隔{interval}秒"
        }
    except Exception as e:
        logger.error(f"启动监控失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/folder/monitor/stop")
async def stop_monitor():
    """停止后台监控"""
    try:
        from core.folder_learner import folder_learner
        
        folder_learner.stop_monitor()
        
        return {
            "success": True,
            "message": "已停止后台监控"
        }
    except Exception as e:
        logger.error(f"停止监控失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/learning/status")
async def get_learning_status():
    """获取学习系统状态"""
    try:
        from core.learning_engine import learning_engine
        from core.file_monitor import file_monitor
        
        return {
            "success": True,
            "engine": learning_engine.get_stats(),
            "monitor": file_monitor.get_status()
        }
    except Exception as e:
        logger.error(f"获取学习状态失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/mode")
async def set_learning_mode(request: dict):
    """设置学习模式"""
    mode = request.get("mode", "smart")
    
    try:
        from core.learning_engine import learning_engine
        
        result = learning_engine.set_mode(mode)
        
        return result
    except Exception as e:
        logger.error(f"设置学习模式失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/add")
async def add_learning_path(request: dict):
    """添加学习路径"""
    path = request.get("path", "")
    priority = request.get("priority", "normal")
    
    try:
        from core.file_monitor import file_monitor
        from core.learning_engine import learning_engine
        from pathlib import Path
        
        monitor_result = file_monitor.add_watch_path(path, priority=priority)
        
        if not monitor_result['success']:
            return monitor_result
        
        watch_path = Path(path).resolve()
        
        supported_extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml',
            '.csv', '.rst', '.js', '.ts', '.html', '.css'
        }
        
        added_count = 0
        for file_path in watch_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                result = learning_engine.add_task(str(file_path), event_type="scan")
                if result['success']:
                    added_count += 1
        
        return {
            "success": True,
            "path": monitor_result['path'],
            "files_count": monitor_result['files_count'],
            "tasks_added": added_count
        }
    except Exception as e:
        logger.error(f"添加学习路径失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/remove")
async def remove_learning_path(request: dict):
    """移除学习路径"""
    path = request.get("path", "")
    
    try:
        from core.file_monitor import file_monitor
        
        result = file_monitor.remove_watch_path(path)
        
        return result
    except Exception as e:
        logger.error(f"移除学习路径失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/force")
async def force_learn_file(request: dict):
    """强制学习文件"""
    file_path = request.get("path", "")
    
    try:
        from core.learning_engine import learning_engine
        
        result = learning_engine.force_learn(file_path)
        
        return result
    except Exception as e:
        logger.error(f"强制学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/pause")
async def pause_learning():
    """暂停学习"""
    try:
        from core.learning_engine import learning_engine
        from core.file_monitor import file_monitor
        
        learning_engine.stop()
        file_monitor.pause()
        
        return {
            "success": True,
            "message": "学习系统已暂停"
        }
    except Exception as e:
        logger.error(f"暂停学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/resume")
async def resume_learning():
    """恢复学习"""
    try:
        from core.learning_engine import learning_engine
        from core.file_monitor import file_monitor
        
        learning_engine.start()
        file_monitor.resume()
        
        return {
            "success": True,
            "message": "学习系统已恢复"
        }
    except Exception as e:
        logger.error(f"恢复学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/learning/tasks")
async def get_learning_tasks(limit: int = 20):
    """获取学习任务列表"""
    try:
        from core.learning_engine import learning_engine
        
        tasks = learning_engine.get_recent_tasks(limit)
        
        return {
            "success": True,
            "tasks": tasks
        }
    except Exception as e:
        logger.error(f"获取学习任务失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/learning/knowledge")
async def get_learning_knowledge(limit: int = 50):
    """获取知识库列表"""
    try:
        import sqlite3
        
        with sqlite3.connect('data/knowledge_store.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT question, answer, source, knowledge_type, created_at
                FROM knowledge_items
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            items = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "knowledge": items
        }
    except Exception as e:
        logger.error(f"获取知识库失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/learning/tools")
async def get_learning_tools():
    """获取自动生成的工具列表"""
    try:
        import sqlite3
        
        with sqlite3.connect('data/knowledge_store.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT name, description, usage_count, created_at
                FROM tools
                ORDER BY usage_count DESC
            ''')
            
            tools = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "tools": tools
        }
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """获取主动调度器状态"""
    try:
        from core.active_scheduler import active_scheduler
        
        return {
            "success": True,
            "status": active_scheduler.get_status()
        }
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/scheduler/run")
async def run_scheduler_once():
    """手动执行一次优化任务"""
    try:
        from core.active_scheduler import active_scheduler
        
        active_scheduler.run_once()
        
        return {
            "success": True,
            "message": "优化任务已执行"
        }
    except Exception as e:
        logger.error(f"执行优化任务失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/knowledge/stats")
async def get_knowledge_stats():
    """获取知识库统计"""
    try:
        import sqlite3
        
        with sqlite3.connect('data/knowledge_store.db') as conn:
            conn.row_factory = sqlite3.Row
            
            stats = {}
            
            cursor = conn.execute('SELECT COUNT(*) FROM knowledge_items')
            stats['total'] = cursor.fetchone()[0]
            
            cursor = conn.execute('''
                SELECT knowledge_type, COUNT(*) as count
                FROM knowledge_items
                GROUP BY knowledge_type
            ''')
            stats['by_type'] = {row['knowledge_type']: row['count'] for row in cursor.fetchall()}
            
            cursor = conn.execute('SELECT COUNT(*) FROM tools')
            stats['tools'] = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM learning_rules WHERE status = "active"')
            stats['rules'] = cursor.fetchone()[0]
            
            cursor = conn.execute('''
                SELECT AVG(quality_score) as avg_quality
                FROM knowledge_items
            ''')
            stats['avg_quality'] = cursor.fetchone()[0] or 0
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取知识统计失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/tools/list")
async def list_tools():
    """列出所有工具"""
    try:
        from core.tool_manager import tool_manager
        
        tools = tool_manager.list_tools()
        
        return {
            "success": True,
            "tools": tools
        }
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/tools/execute")
async def execute_tool(request: dict):
    """执行工具"""
    name = request.get("name", "")
    args = request.get("args", [])
    kwargs = request.get("kwargs", {})
    
    try:
        from core.tool_manager import tool_manager
        
        result = tool_manager.execute_tool(name, *args, **kwargs)
        
        return {
            "success": True,
            "result": str(result)
        }
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/tools/test")
async def test_tool(request: dict):
    """测试工具"""
    name = request.get("name", "")
    test_input = request.get("test_input")
    
    try:
        from core.tool_manager import tool_manager
        
        result = tool_manager.test_tool(name, test_input)
        
        return result
    except Exception as e:
        logger.error(f"工具测试失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/vector/sync")
async def sync_vectors():
    """同步知识库到向量索引"""
    try:
        from core.vector_retriever import vector_retriever
        
        vector_retriever.sync_from_knowledge_base()
        
        return {
            "success": True,
            "message": "向量索引同步完成"
        }
    except Exception as e:
        logger.error(f"向量同步失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/vector/search")
async def vector_search(request: dict):
    """向量搜索"""
    query = request.get("query", "")
    top_k = request.get("top_k", 5)
    
    try:
        from core.vector_retriever import vector_retriever
        
        results = vector_retriever.hybrid_search(query, top_k=top_k)
        
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        logger.error(f"向量搜索失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/memory/important")
async def mark_important(request: dict):
    """刻骨铭心 - 标记为永久记忆"""
    question = request.get("question", "")
    
    try:
        from core.learning import enhanced_learner
        
        result = enhanced_learner.mark_as_important(question)
        
        if result:
            return {
                "success": True,
                "message": "✨ 已标记为刻骨铭心的记忆，永不遗忘"
            }
        else:
            return {
                "success": False,
                "error": "未找到该知识"
            }
    except Exception as e:
        logger.error(f"标记失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/memory/review")
async def get_memory_review():
    """获取记忆回顾报告"""
    try:
        from core.learning import enhanced_learner
        
        review = enhanced_learner.get_memory_review()
        
        return {
            "success": True,
            "review": review
        }
    except Exception as e:
        logger.error(f"获取记忆回顾失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/memory/forgotten")
async def get_forgotten_memories():
    """获取最近遗忘的记忆"""
    try:
        from core.learning import enhanced_learner
        
        forgotten = enhanced_learner.get_recently_forgotten(days=7)
        
        return {
            "success": True,
            "forgotten": forgotten
        }
    except Exception as e:
        logger.error(f"获取遗忘记忆失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/memory/last_qa")
async def get_last_qa(limit: int = 1):
    """获取最近问答（用于 CLI :important 命令）"""
    try:
        from core.learning import enhanced_learner
        
        last_qa = enhanced_learner.get_last_qa(limit=limit)
        
        return {
            "success": True,
            "qa_list": last_qa
        }
    except Exception as e:
        logger.error(f"获取最近问答失败: {e}")
        return {"success": False, "error": str(e)}

def _is_path_allowed(folder: Path) -> bool:
    """检查路径是否在允许范围内（防路径遍历）"""
    try:
        resolved = folder.resolve()
        allowed_bases = [
            Path.cwd().resolve(),
            Path.home().resolve(),
            Path("E:/LMTHZlearn").resolve() if Path("E:/LMTHZlearn").exists() else None,
        ]
        # 过滤掉None
        allowed_bases = [b for b in allowed_bases if b is not None]
        
        return any(
            resolved.is_relative_to(base)
            for base in allowed_bases
        )
    except (OSError, RuntimeError):
        return False

@app.post("/api/folder/preview")
async def preview_folder(request: dict):
    """预览文件夹内容"""
    folder_path = request.get("path", "")
    file_types = request.get("file_types", "all")
    
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    
    try:
        from pathlib import Path
        import os
        
        folder = Path(folder_path).resolve()
        
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        
        if not folder.exists():
            return {"success": False, "error": "文件夹不存在"}
        
        if not folder.is_dir():
            return {"success": False, "error": "路径不是文件夹"}
        
        extensions = {
            "code": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs", ".ts", ".jsx", ".tsx"],
            "doc": [".md", ".txt", ".rst", ".doc", ".docx", ".pdf"],
            "config": [".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"],
            "all": []
        }
        
        target_extensions = extensions.get(file_types, [])
        
        files = []
        for ext in target_extensions if target_extensions else ["*"]:
            for f in folder.rglob(f"*{ext}"):
                if f.is_symlink():
                    continue
                if not _is_path_allowed(f):
                    continue
                files.append(str(f.relative_to(folder)))
        
        if not target_extensions:
            for f in folder.rglob("*"):
                if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                    files.append(str(f.relative_to(folder)))
        
        files = files[:100]
        
        return {"success": True, "files": files, "total": len(files)}
    except Exception as e:
        logger.error(f"预览文件夹失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/folder/browse")
async def browse_folder(request: dict):
    """浏览文件夹内容"""
    folder_path = request.get("path", "")
    
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    
    try:
        from pathlib import Path
        
        folder = Path(folder_path).resolve()
        
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        
        if not folder.exists():
            return {"success": False, "error": "路径不存在"}
        
        if not folder.is_dir():
            return {"success": False, "error": "路径不是文件夹"}
        
        items = []
        for item in folder.iterdir():
            if item.is_symlink():
                continue
            
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": stat.st_mtime
                })
            except:
                continue
        
        # 排序：文件夹优先，然后按名称
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        
        return {"success": True, "items": items, "path": str(folder)}
    except Exception as e:
        logger.error(f"浏览文件夹失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/file/preview")
async def preview_file(request: dict):
    """预览文件内容"""
    file_path = request.get("path", "")
    
    if not file_path:
        return {"success": False, "error": "请提供文件路径"}
    
    try:
        from pathlib import Path
        
        file = Path(file_path).resolve()
        
        if not _is_path_allowed(file):
            return {"success": False, "error": "路径不在允许范围内"}
        
        if not file.exists():
            return {"success": False, "error": "文件不存在"}
        
        if not file.is_file():
            return {"success": False, "error": "路径不是文件"}
        
        file_size = file.stat().st_size
        if file_size > 1024 * 1024:  # 1MB
            return {"success": False, "error": "文件过大，请选择小于1MB的文件"}
        
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return {"success": True, "content": content, "size": file_size}
    except Exception as e:
        logger.error(f"预览文件失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/files/analyze")
async def analyze_files(request: dict):
    """分析选中的文件"""
    files = request.get("files", [])
    
    if not files:
        return {"success": False, "error": "请选择要分析的文件"}
    
    try:
        from pathlib import Path
        
        results = []
        total_size = 0
        
        for file_path in files:
            file = Path(file_path).resolve()
            
            if not _is_path_allowed(file):
                continue
            
            if not file.exists() or not file.is_file():
                continue
            
            try:
                stat = file.stat()
                total_size += stat.st_size
                
                results.append({
                    "name": file.name,
                    "size": stat.st_size,
                    "ext": file.suffix,
                    "path": str(file)
                })
            except:
                continue
        
        summary = f"""分析结果：
- 文件数量: {len(results)}
- 总大小: {total_size / 1024:.1f} KB
- 文件类型: {', '.join(set(r['ext'] for r in results if r['ext']))}

文件列表:
{chr(10).join(f"• {r['name']} ({r['size'] / 1024:.1f} KB)" for r in results[:10])}
{"..." if len(results) > 10 else ""}"""
        
        return {"success": True, "summary": summary, "files": results}
    except Exception as e:
        logger.error(f"分析文件失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/files/learn")
async def learn_from_files(request: dict):
    """从文件中学习，提取知识点保存到知识库"""
    files = request.get("files", [])
    
    if not files:
        return {"success": False, "error": "请选择要学习的文件"}
    
    try:
        from pathlib import Path
        from core.learning import enhanced_learner
        
        results = []
        total_knowledge = 0
        
        for file_path in files:
            file = Path(file_path).resolve()
            
            if not _is_path_allowed(file):
                continue
            
            if not file.exists() or not file.is_file():
                continue
            
            try:
                file_size = file.stat().st_size
                if file_size > 1024 * 1024:  # 限制1MB
                    continue
                
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if len(content) < 50:
                    continue
                
                # 使用增强学习器
                knowledge_count = enhanced_learner.learn_from_file(file.name, content)
                total_knowledge += knowledge_count
                
                results.append({
                    "file": file.name,
                    "knowledge_count": knowledge_count,
                    "size": file_size
                })
                
            except Exception as e:
                logger.warning(f"学习文件失败 {file}: {e}")
                continue
        
        # 检测模式并生成规则
        enhanced_learner.detect_and_create_rules()
        
        # 自动生成工具
        enhanced_learner.auto_generate_tools()
        
        summary = f"""学习完成！

📊 学习统计：
- 处理文件: {len(results)}个
- 提取知识点: {total_knowledge}条
- 总大小: {sum(r['size'] for r in results) / 1024:.1f} KB

📚 知识点来源:
{chr(10).join(f"• {r['file']}: {r['knowledge_count']}条" for r in results[:10])}

💡 系统已自动：
- 提取函数、类、代码片段
- 检测重复模式生成规则
- 自动生成可复用工具

以后可以通过对话查询这些知识，例如：
- "函数xxx的作用是什么？"
- "如何统计模型参数量？" """
        
        logger.info(f"文件学习完成: {total_knowledge}条知识点")
        return {"success": True, "summary": summary, "total_knowledge": total_knowledge}
    except Exception as e:
        logger.error(f"从文件学习失败: {e}")
        return {"success": False, "error": str(e)}

def _extract_knowledge_from_file(filename: str, content: str) -> list:
    """从文件内容中提取知识点"""
    import re
    
    knowledge_items = []
    
    # 根据文件类型提取不同知识点
    if filename.endswith('.py'):
        # 提取函数定义
        functions = re.findall(r'def\s+(\w+)\s*\([^)]*\):\s*"""([^"]+)"""', content, re.DOTALL)
        for func_name, docstring in functions:
            if len(docstring) > 20:
                knowledge_items.append({
                    'question': f"函数 {func_name} 的作用是什么？",
                    'answer': f"{func_name}: {docstring.strip()}"
                })
        
        # 提取类定义
        classes = re.findall(r'class\s+(\w+).*?:\s*"""([^"]+)"""', content, re.DOTALL)
        for class_name, docstring in classes:
            if len(docstring) > 20:
                knowledge_items.append({
                    'question': f"类 {class_name} 的作用是什么？",
                    'answer': f"{class_name}: {docstring.strip()}"
                })
    
    elif filename.endswith(('.md', '.txt')):
        # 提取标题和段落
        sections = re.split(r'\n#{1,3}\s+', content)
        for section in sections[1:6]:  # 最多5个章节
            lines = section.strip().split('\n')
            if len(lines) > 1:
                title = lines[0].strip()
                body = '\n'.join(lines[1:5]).strip()  # 取前4行
                if len(body) > 30:
                    knowledge_items.append({
                        'question': f"{title}",
                        'answer': body[:500]
                    })
    
    elif filename.endswith(('.yaml', '.yml', '.json')):
        # 配置文件：提取关键配置项
        knowledge_items.append({
            'question': f"{filename} 配置说明",
            'answer': f"配置文件 {filename} 的内容:\n{content[:500]}"
        })
    
    # 如果没有提取到特定知识点，保存整体摘要
    if not knowledge_items and len(content) > 100:
        knowledge_items.append({
            'question': f"{filename} 的主要内容",
            'answer': content[:500]
        })
    
    return knowledge_items

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/api/folder/learn")
async def learn_from_folder(request: dict):
    """从文件夹学习"""
    folder_path = request.get("path", "")
    file_types = request.get("file_types", "all")
    learn_mode = request.get("mode", "analyze")
    
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    
    try:
        from pathlib import Path
        import os
        
        folder = Path(folder_path).resolve()
        
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        
        if not folder.exists():
            return {"success": False, "error": "文件夹不存在"}
        
        extensions = {
            "code": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs", ".ts"],
            "doc": [".md", ".txt", ".rst"],
            "config": [".yaml", ".yml", ".json", ".toml"],
            "all": []
        }
        
        target_extensions = extensions.get(file_types, [])
        
        files = []
        for ext in target_extensions if target_extensions else ["*"]:
            for f in folder.rglob(f"*{ext}"):
                if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                    files.append(f)
        
        if not target_extensions:
            for f in folder.rglob("*"):
                if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                    files.append(f)
        
        files = files[:50]
        
        processed = 0
        knowledge_count = 0
        summaries = []
        
        for file_path in files:
            try:
                file_size = file_path.stat().st_size
                if file_size > MAX_FILE_SIZE:
                    logger.warning(f"跳过大文件 {file_path}: {file_size} bytes")
                    continue
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if len(content) < 10:
                    continue
                
                # 根据学习模式处理
                if learn_mode == "analyze":
                    # 分析代码结构
                    if file_path.suffix in [".py", ".js", ".java"]:
                        lines = content.count('\n')
                        functions = content.count('def ') + content.count('function ')
                        classes = content.count('class ')
                        summaries.append(f"{file_path.name}: {lines}行, {functions}函数, {classes}类")
                        knowledge_count += 1
                
                elif learn_mode == "extract":
                    # 提取知识点（简单实现）
                    if 'TODO' in content or 'FIXME' in content:
                        knowledge_count += 1
                    summaries.append(f"{file_path.name}: 已提取")
                
                elif learn_mode == "summarize":
                    # 生成摘要
                    first_lines = '\n'.join(content.split('\n')[:5])
                    summaries.append(f"{file_path.name}:\n{first_lines}")
                    knowledge_count += 1
                
                processed += 1
                
            except Exception as e:
                logger.warning(f"处理文件失败 {file_path}: {e}")
                continue
        
        summary_text = '\n'.join(summaries[:10])
        
        try:
            import sqlite3
            from datetime import datetime
            
            with sqlite3.connect('data/knowledge_store.db') as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS folder_knowledge (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        folder_path TEXT,
                        mode TEXT,
                        processed INTEGER,
                        knowledge INTEGER,
                        summary TEXT,
                        timestamp TEXT
                    )
                ''')
                conn.execute('''
                    INSERT INTO folder_knowledge (folder_path, mode, processed, knowledge, summary, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (folder_path, learn_mode, processed, knowledge_count, summary_text, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            logger.warning(f"存储知识失败: {e}")
        
        return {
            "success": True,
            "processed": processed,
            "knowledge": knowledge_count,
            "summary": summary_text
        }
    except Exception as e:
        logger.error(f"文件夹学习失败: {e}")
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
        logger.error(f"测试模型失败: 连接错误")
        return {"success": False, "message": "连接失败，请检查配置"}

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
        
        with adapters_lock:
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

# ========== 规则管理API ==========

@app.get("/api/rules")
async def list_rules(status: str = None, limit: int = 20):
    """列出学习规则
    
    Args:
        status: 过滤状态 (trial/active/expired)
        limit: 返回数量限制
    """
    try:
        import sqlite3
        
        with sqlite3.connect("learning_rules.db") as conn:
            if status:
                cur = conn.execute('''
                    SELECT id, condition, action, confidence, status, source, 
                           trial_count, trial_success, created_at
                    FROM learning_rules
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (status, limit))
            else:
                cur = conn.execute('''
                    SELECT id, condition, action, confidence, status, source,
                           trial_count, trial_success, created_at
                    FROM learning_rules
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            rules = []
            for row in cur.fetchall():
                rules.append({
                    "id": row[0],
                    "condition": row[1],
                    "action": row[2],
                    "confidence": row[3],
                    "status": row[4],
                    "source": row[5],
                    "trial_count": row[6],
                    "trial_success": row[7],
                    "created_at": row[8]
                })
            
            return {"rules": rules, "count": len(rules)}
            
    except Exception as e:
        logger.error(f"列出规则失败: {e}")
        return {"rules": [], "error": str(e)}

@app.post("/api/rules/{rule_id}/approve")
async def approve_rule(rule_id: int):
    """批准规则（用户干预）"""
    try:
        import sqlite3
        
        with sqlite3.connect("learning_rules.db") as conn:
            conn.execute('''
                UPDATE learning_rules
                SET status = 'active', confidence = 0.9
                WHERE id = ?
            ''', (rule_id,))
            conn.commit()
            
            logger.info(f"用户批准规则 #{rule_id}")
            
            return {"success": True, "rule_id": rule_id, "action": "approved"}
            
    except Exception as e:
        logger.error(f"批准规则失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/rules/{rule_id}/reject")
async def reject_rule(rule_id: int):
    """拒绝规则（用户干预）"""
    try:
        import sqlite3
        
        with sqlite3.connect("learning_rules.db") as conn:
            conn.execute('''
                UPDATE learning_rules
                SET status = 'expired'
                WHERE id = ?
            ''', (rule_id,))
            conn.commit()
            
            logger.info(f"用户拒绝规则 #{rule_id}")
            
            return {"success": True, "rule_id": rule_id, "action": "rejected"}
            
    except Exception as e:
        logger.error(f"拒绝规则失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/decision/why")
async def explain_last_decision():
    """解释最近一次决策原因"""
    try:
        import sqlite3
        
        # 获取最近的决策日志
        with sqlite3.connect("data/decision_log.db") as conn:
            cur = conn.execute('''
                SELECT decision_type, choice, reason, alternatives, score, timestamp
                FROM decisions
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            
            row = cur.fetchone()
            
            if not row:
                return {"message": "暂无决策记录"}
            
            return {
                "decision_type": row[0],
                "choice": row[1],
                "reason": row[2],
                "alternatives": row[3].split(",") if row[3] else [],
                "score": row[4],
                "timestamp": row[5]
            }
            
    except Exception as e:
        logger.error(f"获取决策原因失败: {e}")
        return {"error": str(e)}

@app.get("/api/trial_stats")
async def get_trial_stats():
    """获取试用期统计"""
    try:
        from infrastructure.rule_trial_manager import rule_trial_manager
        stats = rule_trial_manager.get_trial_stats()
        return stats
    except Exception as e:
        logger.error(f"获取试用期统计失败: {e}")
        return {"error": str(e)}

# ========== 模型热加载API ==========

@app.post("/api/models/add")
async def add_model(request: dict):
    """动态添加模型"""
    global adapters
    
    model_name = request.get("name")
    model_type = request.get("type", "ollama")
    
    if not model_name:
        return {"success": False, "error": "模型名称不能为空"}
    
    with adapters_lock:
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
    
    with adapters_lock:
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
    with adapters_lock:
        if model_name not in adapters:
            return {"success": False, "error": f"模型 {model_name} 不存在"}
        adapter = adapters[model_name]
    
    try:
        test_prompt = "Hello, this is a test."
        
        import asyncio
        if asyncio.iscoroutinefunction(adapter.generate):
            response = await asyncio.wait_for(
                adapter.generate(test_prompt),
                timeout=10.0
            )
        else:
            response = await asyncio.to_thread(adapter.generate, test_prompt)
        
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

# ========== 主动学习API ==========

@app.get("/api/learning/log")
async def get_learning_log(limit: int = 20):
    """查看学习活动日志"""
    try:
        from infrastructure.active_learner import active_learner
        
        activities = active_learner.get_activities(limit=limit)
        
        return {
            "success": True,
            "activities": activities,
            "total": len(activities)
        }
        
    except Exception as e:
        logger.error(f"获取学习日志失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/learning/knowledge")
async def get_learning_knowledge(topic: str = None, limit: int = 20):
    """查看已学习的知识"""
    try:
        from infrastructure.active_learner import active_learner
        
        knowledge = active_learner.get_knowledge(topic=topic, limit=limit)
        
        return {
            "success": True,
            "knowledge": knowledge,
            "total": len(knowledge)
        }
        
    except Exception as e:
        logger.error(f"获取知识失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/trigger")
async def trigger_learning(query: str, trigger_type: str = "manual"):
    """手动触发学习"""
    try:
        from infrastructure.active_learner import active_learner, LearningTrigger
        
        trigger_map = {
            "manual": LearningTrigger.MANUAL,
            "user_question": LearningTrigger.USER_QUESTION,
            "intent_failure": LearningTrigger.INTENT_FAILURE,
            "capability_low": LearningTrigger.CAPABILITY_LOW,
            "aphi_decline": LearningTrigger.APHI_DECLINE
        }
        
        trigger = trigger_map.get(trigger_type, LearningTrigger.MANUAL)
        
        activity = await active_learner.trigger_learning(trigger, query)
        
        return {
            "success": True,
            "activity": {
                "id": activity.id,
                "trigger": activity.trigger.value,
                "query": activity.query,
                "status": activity.status.value,
                "impact_score": activity.impact_score
            }
        }
        
    except Exception as e:
        logger.error(f"触发学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/pause")
async def pause_learning():
    """暂停学习"""
    try:
        from infrastructure.active_learner import active_learner
        
        active_learner.pause()
        
        return {"success": True, "message": "学习器已暂停"}
        
    except Exception as e:
        logger.error(f"暂停学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/resume")
async def resume_learning():
    """恢复学习"""
    try:
        from infrastructure.active_learner import active_learner
        
        active_learner.resume()
        
        return {"success": True, "message": "学习器已恢复"}
        
    except Exception as e:
        logger.error(f"恢复学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/learning/rollback/{activity_id}")
async def rollback_learning(activity_id: int):
    """回滚学习"""
    try:
        from infrastructure.active_learner import active_learner
        
        success = active_learner.rollback_learning(activity_id)
        
        return {"success": success, "message": f"已回滚学习活动 {activity_id}"}
        
    except Exception as e:
        logger.error(f"回滚学习失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/learning/stats")
async def get_learning_stats():
    """获取学习统计"""
    try:
        from infrastructure.active_learner import active_learner
        
        stats = active_learner.get_statistics()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取学习统计失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/cognitive/analyze")
async def cognitive_analyze(request: dict):
    """认知层分析"""
    text = request.get("text", "")
    intent_type = request.get("intent_type", None)
    
    if not text:
        return {"error": "请提供要分析的文本"}
    
    try:
        from infrastructure.cognitive_layer import cognitive_layer
        
        result = cognitive_layer.analyze(text, intent_type, "")
        report = cognitive_layer.generate_report(result)
        subtasks = cognitive_layer.plan_from_analysis(result.get("analysis", {}))
        
        return {
            "success": True,
            "analysis": result,
            "report": report,
            "subtasks": subtasks
        }
    except Exception as e:
        logger.error(f"认知分析失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/recurrent/reason")
async def recurrent_reason(request: dict):
    """循环推理"""
    prompt = request.get("prompt", "")
    intent_type = request.get("intent_type", "question")
    model_name = request.get("model", "mindchat")
    max_iterations = request.get("max_iterations", 3)
    
    if not prompt:
        return {"error": "请提供提示词"}
    
    try:
        from infrastructure.recurrent_reasoner import recurrent_reasoner
        
        with adapters_lock:
            model = adapters.get(model_name)
        
        if not model:
            return {"error": f"模型 {model_name} 不存在"}
        
        enhanced, trajectory = recurrent_reasoner.reason_with_loops(
            model=model,
            prompt=prompt,
            intent_type=intent_type,
            context="",
            max_iterations=max_iterations
        )
        
        return {
            "success": True,
            "response": enhanced,
            "iterations": len(trajectory),
            "trajectory": trajectory
        }
    except Exception as e:
        logger.error(f"循环推理失败: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)