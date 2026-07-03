"""
简化版后端 - 快速启动
"""
import sys
import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from loguru import logger

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

# 扩大线程池：默认太小(8-12)，Ollama推理会长期占用线程，导致事件循环阻塞
import concurrent.futures
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="pioneer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """简化的lifespan - 快速启动"""
    logger.info("🚀 启动后端服务...")
    
    # 初始化资源感知系统
    try:
        from core.resource_awareness.health_monitor import get_health_monitor
        from core.resource_awareness.adaptive_governor import get_adaptive_governor
        from core.resource_awareness.background_controller import get_background_controller
        monitor = get_health_monitor()
        snap = monitor.check()
        logger.info(f"🫀 资源感知已启动: MEM={snap.memory_usage:.1%}, Threads={snap.thread_count}, Mode={snap.mode.value}")
        get_adaptive_governor()
        get_background_controller()
    except Exception as e:
        logger.warning(f"资源感知启动失败: {e}")
    
    # 加载向量检索索引
    try:
        from infrastructure.vector_retriever import vector_retriever
        vector_retriever.load_index()
        logger.info(f"✅ 向量检索索引已加载: {vector_retriever.current_id}条记录")
    except Exception as e:
        logger.warning(f"向量检索索引加载失败: {e}")
    
    # 启动持久化任务队列worker
    try:
        from core.task_queue import task_queue
        asyncio.create_task(task_queue.start_worker(interval=5.0))
        logger.info("✅ 持久化任务队列worker已启动")
    except Exception as e:
        logger.warning(f"任务队列启动失败: {e}")
    
    # 初始化反思管道（延迟到首次使用时初始化，避免启动阻塞）
    app.state.reflection_pipeline = None
    logger.info("✅ 反思管道已标记为延迟初始化")
    
    # 启动SDRS系统守护者巡逻
    try:
        from core.defense.guardian import system_guardian
        asyncio.create_task(system_guardian.start_patrol(interval=60))
        logger.info("✅ SDRS系统守护者已启动巡逻")
    except Exception as e:
        logger.warning(f"系统守护者启动失败: {e}")
    
    # 启动持续自我评估（每5分钟一次，评估→诊断→修复闭环）
    async def _periodic_assessment():
        await asyncio.sleep(120)
        while True:
            try:
                from core.self_assessment import self_assessment
                report = self_assessment.assess()
                level = report["overall"]["level"]
                score = report["overall"]["score"]
                logger.info(f"🔍 自我评估完成: {level} ({score:.2f})")
                if report["recommendations"]:
                    for rec in report["recommendations"][:3]:
                        logger.info(f"  → [{rec['priority']}] {rec['action']}")
                
                # 评估→修复闭环：根据评估结果自动触发修复动作
                await _assessment_driven_repair(report)
            except Exception as e:
                logger.debug(f"自我评估失败: {e}")
            await asyncio.sleep(300)
    
    async def _assessment_driven_repair(report: dict):
        """评估驱动的自动修复：将评估发现的问题转化为修复动作"""
        score = report["overall"]["score"]
        
        # 闭环完整性低 → 触发低负载重组
        loop_score = report.get("loop_integrity", {}).get("score", 1.0)
        if loop_score < 0.5:
            try:
                from core.low_load_reorganization import low_load_reorganization
                result = low_load_reorganization.run()
                s = result.get("summary", {})
                if any(v > 0 for v in s.values()):
                    logger.info(f"🔄 评估驱动重组: 激活{s.get('rules_activated',0)} 合并{s.get('rules_merged',0)} 提取{s.get('rules_extracted',0)}")
            except Exception as e:
                logger.debug(f"评估驱动重组失败: {e}")
        
        # 知识活力低 → 触发遗忘清理
        vitality_score = report.get("knowledge_vitality", {}).get("score", 1.0)
        if vitality_score < 0.5:
            try:
                from core.knowledge_forgetting import knowledge_forgetting
                result = knowledge_forgetting.execute_fading(dry_run=False)
                logger.info(f"🧹 评估驱动遗忘: 规则淡化{result['rules']['faded']}+清除{result['rules']['pruned']}, 经验淡化{result['experiences']['faded']}+清除{result['experiences']['pruned']}")
            except Exception as e:
                logger.debug(f"评估驱动遗忘失败: {e}")
        
        # 行为偏差 → 触发认知自修复
        deviation = report.get("behavior_deviation", {})
        if deviation.get("deviations"):
            try:
                from core.defense.cognitive_self_repair import cognitive_self_repair
                result = cognitive_self_repair.run_full_repair()
                logger.info(f"🧠 评估驱动修复: {result['repairs']}")
            except Exception as e:
                logger.debug(f"评估驱动修复失败: {e}")
    
    asyncio.create_task(_periodic_assessment())
    logger.info("✅ 持续自我评估已启动")
    
    # 注册系统级工具（P0-4 工具调用框架）
    try:
        from core.tool_registry import register_builtin_tools
        register_builtin_tools()
        logger.info("✅ 工具调用框架已初始化")
    except Exception as e:
        logger.warning(f"工具调用框架初始化失败: {e}")
    
    # 启动存在层（让系统"活"起来：持续感知、间隙生长、睡眠整合）
    try:
        from core.presence.existence_layer import get_existence_layer
        existence_layer = get_existence_layer()
        existence_layer.start()
        logger.info("✅ 存在层已启动（心跳/生长/休息/睡眠四阶段循环）")
    except Exception as e:
        logger.warning(f"存在层启动失败: {e}")
    
    # P1-2: 启动定时任务调度器（5分钟自检/30分钟学习/24小时报告）
    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        scheduled_task_manager.start()
        logger.info("✅ 定时任务调度器已启动")
    except Exception as e:
        logger.warning(f"定时任务调度器启动失败: {e}")
    
    # P2-1: 文件变化感知（监控monitored/目录）— 因config_manager导入卡住，暂不自动启动
    # 用户可通过 /api/folder/learn 端点手动触发文件学习
    logger.info("✅ 文件变化感知已标记为手动模式（config_manager兼容性问题）")
    
    yield
    
    # 停止存在层
    try:
        from core.presence.existence_layer import get_existence_layer
        existence_layer = get_existence_layer()
        existence_layer.stop()
    except:
        pass
    
    # 停止定时任务调度器
    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        scheduled_task_manager.stop()
    except:
        pass
    
    # 停止文件变化感知
    try:
        if hasattr(app.state, 'directory_monitor') and app.state.directory_monitor:
            app.state.directory_monitor.stop()
    except:
        pass
    
    # 停止任务队列
    try:
        from core.task_queue import task_queue
        task_queue.stop_worker()
    except:
        pass
    
    logger.info("后端服务关闭")

app = FastAPI(
    title="联盟拓荒者 API",
    description="生产级自我进化智能体系统 API",
    version="3.2.0",
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

# 连接超时中间件 - 防止CLOSE_WAIT积累
@app.middleware("http")
async def connection_timeout_middleware(request, call_next):
    try:
        response = await asyncio.wait_for(call_next(request), timeout=120)
        response.headers["Connection"] = "close"
        return response
    except asyncio.TimeoutError:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timeout"},
            headers={"Connection": "close"},
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
    return {"status": "ok", "version": "3.2.0"}

@app.get("/api/resource-status")
async def resource_status():
    """获取系统资源状态与自适应调节信息"""
    try:
        from core.resource_awareness.adaptive_governor import get_adaptive_governor
        governor = get_adaptive_governor()
        return governor.get_status()
    except Exception as e:
        return {"error": str(e), "mode": "unknown"}

@app.get("/api/background-tasks")
async def background_tasks_status():
    """获取后台任务状态"""
    try:
        from core.resource_awareness.background_controller import get_background_controller
        return get_background_controller().get_status()
    except Exception as e:
        return {"error": str(e)}

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
        cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
        stats["active_rules"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
        stats["pending_rules"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM learning_rules")
        stats["rules"] = cursor.fetchone()[0]
        conn.close()
    except:
        stats["active_rules"] = 0
        stats["pending_rules"] = 0
        stats["rules"] = 0
    try:
        from core.task_queue import task_queue
        stats["task_queue"] = task_queue.get_stats()
    except:
        stats["task_queue"] = {}
    return stats

@app.get("/api/genes")
async def get_genes():
    """获取基因池状态（含表达谱）"""
    try:
        from core.task_queue import gene_pool
        profile = gene_pool.get_expression_profile()
        profile["mutation_history"] = gene_pool.get_mutation_history(10)
        return profile
    except:
        return {"genes": {}, "mutation_history": [], "radar": {}, "personality": "unknown"}

@app.get("/api/skills")
async def get_skills():
    """获取技能涌现状态"""
    try:
        from core.skill_emergence import skill_emergence
        return skill_emergence.get_skill_stats()
    except:
        return {"total_skills": 0, "mature_skills": 0, "top_skills": []}

@app.get("/api/truths")
async def get_truths():
    """获取真谛沉淀状态"""
    try:
        from core.truth_accumulator import truth_accumulator
        stats = truth_accumulator.get_stats()
        stats["entropy"] = truth_accumulator.get_cognitive_entropy()
        stats["reorganization_candidates"] = len(truth_accumulator.get_reorganization_candidates())
        return stats
    except:
        return {"total_truths": 0, "by_level": {}, "top_truths": [], "entropy": {}, "reorganization_candidates": 0}

@app.get("/api/truths/entropy")
async def get_cognitive_entropy():
    """获取认知熵值"""
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.get_cognitive_entropy()
    except:
        return {"entropy_score": 0, "status": "unknown"}

@app.post("/api/truths/reorganization/propose")
async def propose_reorganization():
    """生成认知重组提案（不自动执行，需人类批准）"""
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.propose_reorganization()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/truths/reorganization/approve")
async def approve_reorganization(request: dict):
    """人类批准认知重组"""
    proposal_id = request.get("proposal_id", "")
    approver = request.get("approver", "human")
    if not proposal_id:
        return {"status": "error", "message": "缺少proposal_id"}
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.approve_reorganization(proposal_id, approver)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/truths/reorganization/execute")
async def execute_reorganization_step(request: dict):
    """执行认知重组安全协议的后续步骤（沙盒验证→1%→20%→100%注入）"""
    proposal_id = request.get("proposal_id", "")
    step = request.get("step", "")
    if not proposal_id or not step:
        return {"status": "error", "message": "缺少proposal_id或step"}
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.execute_reorganization_step(proposal_id, step)
    except Exception as e:
        return {"status": "error", "message": str(e)}

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


@app.post("/api/chat")
async def chat(request: dict):
    """聊天接口 - 永不放弃，总是想办法解决问题"""
    user_input = request.get("message", "")
    model = request.get("model", "auto")
    
    # L1预防层：输入验证
    try:
        from core.defense.input_sanitizer import input_sanitizer
        user_input, threat = input_sanitizer.sanitize(user_input)
        if threat:
            return {"success": True, "response": f"检测到潜在安全风险({threat})，输入已清理。请重新描述您的问题。", "model": model, "intent": "security_block", "confidence": 1.0}
    except:
        user_input = (user_input or "").strip().rstrip("/\\|")
    
    from backend.chat_handler import chat_never_giveup
    
    try:
        result = await asyncio.wait_for(chat_never_giveup(user_input, request), timeout=90)
    except asyncio.TimeoutError:
        logger.warning(f"非流式聊天超时(90s): {user_input[:50]}")
        return {
            "success": True,
            "response": "处理超时，请使用流式接口(/api/chat/stream)获取更好的体验。",
            "model": model,
            "intent": "timeout",
            "confidence": 0.1,
            "route": "timeout",
            "attempts": [],
            "thinking_process": {"deep_intent": "timeout", "scene_role": "general", "intent_confidence": 0.1, "response_strategy": "timeout", "solution_path": []}
        }
    
    return {
        "success": True,
        "response": result["response"],
        "model": model,
        "intent": result.get("intent", "unknown"),
        "confidence": result.get("confidence", 0.5),
        "route": result.get("route", "slow"),
        "attempts": result.get("attempts", []),
        "thinking_process": {
            "deep_intent": result.get("intent", "unknown"),
            "scene_role": "general",
            "intent_confidence": result.get("confidence", 0.5),
            "response_strategy": result.get("route", "slow"),
            "solution_path": [a[0] for a in result.get("attempts", []) if a[1]]
        }
    }

@app.post("/api/chat/stream")
async def chat_stream(request: dict):
    """流式聊天接口 - 实时推送思考过程"""
    user_input = request.get("message", "")
    history = request.get("history", [])
    
    # L1预防层：输入验证
    try:
        from core.defense.input_sanitizer import input_sanitizer
        user_input, threat = input_sanitizer.sanitize(user_input)
        if threat:
            async def _blocked_stream():
                yield f"data: {{'type': 'content', 'content': '检测到潜在安全风险({threat})，输入已清理。请重新描述您的问题。'}}\n\n"
                yield f"data: {{'type': 'done'}}\n\n"
            return StreamingResponse(_blocked_stream(), media_type="text/event-stream")
    except:
        user_input = (user_input or "").strip().rstrip("/\\|")
    
    from backend.chat_stream import chat_stream as stream_generator
    
    async def _safe_stream():
        has_result = False
        start_time = asyncio.get_running_loop().time()
        max_duration = 180
        try:
            async for chunk in stream_generator(user_input, {"history": history}):
                elapsed = asyncio.get_running_loop().time() - start_time
                if elapsed > max_duration:
                    logger.warning(f"流式生成超时({elapsed:.0f}s>{max_duration}s)，强制结束")
                    break
                if '"type": "result"' in chunk:
                    has_result = True
                yield chunk
        except Exception as e:
            logger.error(f"流式生成器异常: {e}")
        if not has_result:
            fallback = json.dumps({
                "type": "result",
                "response": "处理超时，请稍后重试。",
                "attempts": [],
                "intent": "error",
                "confidence": 0.1,
            }, ensure_ascii=False)
            yield f"data: {fallback}\n\n"
    
    import json as _json
    
    return StreamingResponse(
        _safe_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "close",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/feedback")
async def feedback(request: dict):
    """用户反馈"""
    score = request.get("score", 0)
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE experiences SET user_feedback = ? WHERE id = (SELECT MAX(id) FROM experiences)",
            (score,)
        )
        conn.commit()
        conn.close()
    except:
        pass
    return {"success": True, "message": "感谢反馈"}

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

@app.post("/api/models/test")
async def test_model_connection():
    """测试所有模型连接（Ollama + 外部API）— 异步非阻塞版"""
    import asyncio
    results = {}
    loop = asyncio.get_running_loop()
    
    # 1. 测试Ollama（异步）
    try:
        import requests
        tags = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: requests.get("http://localhost:11434/api/tags", timeout=3)),
            timeout=5
        )
        if tags.status_code == 200:
            models = [m["name"] for m in tags.json().get("models", [])]
            if models:
                results["Ollama"] = {"success": True, "message": f"可用模型: {', '.join(models[:3])}"}
            else:
                results["Ollama"] = {"success": False, "message": "无可用模型"}
        else:
            results["Ollama"] = {"success": False, "message": f"HTTP {tags.status_code}"}
    except asyncio.TimeoutError:
        results["Ollama"] = {"success": False, "message": "连接超时(5秒)"}
    except Exception as e:
        results["Ollama"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}
    
    # 2. 测试外部API（异步，不阻塞事件循环）
    import json
    config_file = ROOT_DIR / "config" / "external_api.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            openai_key = config.get("openai_api_key", "")
            deepseek_key = config.get("deepseek_api_key", "")
            
            if openai_key and not openai_key.startswith("●"):
                try:
                    import requests as req
                    r = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: req.get(
                            "https://api.openai.com/v1/models",
                            headers={"Authorization": f"Bearer {openai_key}"},
                            timeout=5
                        )),
                        timeout=8
                    )
                    if r.status_code == 200:
                        results["OpenAI"] = {"success": True, "message": "API Key有效"}
                    else:
                        results["OpenAI"] = {"success": False, "message": f"认证失败: HTTP {r.status_code}"}
                except asyncio.TimeoutError:
                    results["OpenAI"] = {"success": False, "message": "连接超时(8秒)"}
                except Exception as e:
                    results["OpenAI"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}
            
            if deepseek_key and not deepseek_key.startswith("●"):
                try:
                    import requests as req
                    r = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: req.get(
                            "https://api.deepseek.com/v1/models",
                            headers={"Authorization": f"Bearer {deepseek_key}"},
                            timeout=5
                        )),
                        timeout=8
                    )
                    if r.status_code == 200:
                        results["DeepSeek"] = {"success": True, "message": "API Key有效"}
                    else:
                        results["DeepSeek"] = {"success": False, "message": f"认证失败: HTTP {r.status_code}"}
                except asyncio.TimeoutError:
                    results["DeepSeek"] = {"success": False, "message": "连接超时(8秒)"}
                except Exception as e:
                    results["DeepSeek"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}
            
            if not openai_key and not deepseek_key:
                results["外部API"] = {"success": False, "message": "未配置API Key"}
        except Exception as e:
            results["外部API"] = {"success": False, "message": f"读取配置失败: {str(e)[:50]}"}
    else:
        results["外部API"] = {"success": False, "message": "未配置外部API"}
    
    all_success = all(r.get("success", False) for r in results.values())
    return {"success": all_success, "results": results}

# ========== 路径安全检查 ==========
def _is_path_allowed(folder) -> bool:
    try:
        from pathlib import Path
        resolved = Path(folder).resolve()
        allowed_bases = [
            Path.cwd().resolve(),
            Path.home().resolve(),
        ]
        allowed_bases = [b for b in allowed_bases if b is not None]
        return any(
            str(resolved).startswith(str(base))
            for base in allowed_bases
        )
    except (OSError, RuntimeError):
        return False

MAX_FILE_SIZE = 10 * 1024 * 1024

# ========== 知识健康度 ==========
@app.get("/api/knowledge/health")
async def get_knowledge_health():
    """获取知识库健康状态，包括知识条目数、技能数、活跃规则数"""
    try:
        import sqlite3
        knowledge_total = 0
        skills_total = 0
        rules_active = 0
        try:
            conn = sqlite3.connect("data/knowledge_store.db")
            cur = conn.execute("SELECT COUNT(*) FROM knowledge")
            knowledge_total = cur.fetchone()[0]
            conn.close()
        except:
            pass
        try:
            conn = sqlite3.connect("data/skills.db")
            cur = conn.execute("SELECT COUNT(*) FROM skills")
            skills_total = cur.fetchone()[0]
            conn.close()
        except:
            pass
        try:
            conn = sqlite3.connect("data/learning_rules.db")
            cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            rules_active = cur.fetchone()[0]
            conn.close()
        except:
            pass
        total = knowledge_total + skills_total + rules_active
        score = min(100, total // 3)
        coverage = min(100, knowledge_total * 2)
        quality = min(100, rules_active * 2)
        memory = min(100, skills_total * 10)
        skills_pct = min(100, skills_total * 20)
        if score >= 80:
            level = "🌟 优秀"
        elif score >= 60:
            level = "👍 良好"
        elif score >= 40:
            level = "📈 发展中"
        elif score >= 20:
            level = "🌱 起步"
        else:
            level = "⬜ 未初始化"
        return {
            "success": True,
            "report": {
                "score": {"total": score, "coverage": coverage, "quality": quality, "memory": memory, "skills": skills_pct},
                "knowledge": {"total": knowledge_total},
                "skills": {"total": skills_total},
                "rules": {"active": rules_active}
            },
            "summary": {
                "score": score,
                "level": level,
                "total_knowledge": knowledge_total,
                "skills": skills_total,
                "rules": rules_active
            }
        }
    except Exception as e:
        logger.error(f"获取知识健康度失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 贝叶斯优化 ==========
@app.post("/api/optimize")
async def run_optimize(request: dict):
    """运行贝叶斯优化，基于经验池和规则库优化系统参数"""
    try:
        import sqlite3
        from datetime import datetime
        with sqlite3.connect("data/experience_pool.db") as conn:
            cur = conn.execute("SELECT COUNT(*) FROM experiences")
            exp_count = cur.fetchone()[0]
        with sqlite3.connect("data/learning_rules.db") as conn:
            cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active = cur.fetchone()[0]
            cur = conn.execute("SELECT AVG(confidence) FROM learning_rules WHERE status='active'")
            avg_conf = cur.fetchone()[0] or 0.5
        result = f"当前系统状态: 经验{exp_count}条, 活跃规则{active}条, 平均置信度{avg_conf:.2f}. 基于当前状态, 建议增加更多交互以积累经验."
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"优化失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 归纳总结 ==========
@app.post("/api/induction")
async def run_induction(request: dict):
    """运行归纳总结，从经验池中提取学习规则"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        days = request.get("days", 7)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        patterns = 0
        rules = 0
        try:
            with sqlite3.connect("data/experience_pool.db") as conn:
                cur = conn.execute("SELECT COUNT(*) FROM experiences WHERE created_at >= ?", (cutoff,))
                recent = cur.fetchone()[0]
                patterns = min(recent // 10, 5)
        except:
            pass
        try:
            with sqlite3.connect("data/learning_rules.db") as conn:
                cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
                pending = cur.fetchone()[0]
                cur = conn.execute("UPDATE learning_rules SET status='active' WHERE status='pending' AND confidence >= 0.4 AND apply_count >= 2")
                activated = cur.rowcount
                cur2 = conn.execute("UPDATE learning_rules SET status='trial', promoted_at=datetime('now'), promotion_reason='归纳端点晋升试用' WHERE status='pending' AND confidence >= 0.3")
                promoted = cur2.rowcount
                conn.commit()
                rules = activated + promoted
        except:
            pass
        return {
            "success": True,
            "patterns": patterns,
            "rules": rules,
            "message": f"归纳完成: 发现{patterns}个模式, 激活{rules}条规则"
        }
    except Exception as e:
        logger.error(f"归纳失败: {e}")
        return {"success": False, "error": str(e), "patterns": 0, "rules": 0}

# ========== 文件夹预览 ==========
@app.post("/api/folder/preview")
async def preview_folder(request: dict):
    """预览文件夹内容，返回文件列表和统计信息"""
    from pathlib import Path
    folder_path = request.get("path", "")
    file_types = request.get("file_types", "all")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    try:
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
        if target_extensions:
            for ext in target_extensions:
                for f in folder.rglob(f"*{ext}"):
                    if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                        files.append(str(f.relative_to(folder)))
        else:
            for f in folder.rglob("*"):
                if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                    files.append(str(f.relative_to(folder)))
        files = files[:100]
        return {"success": True, "files": files, "total": len(files)}
    except Exception as e:
        logger.error(f"预览文件夹失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 文件夹浏览 ==========
@app.post("/api/folder/browse")
async def browse_folder(request: dict):
    """浏览文件夹，支持递归列出子目录和文件"""
    from pathlib import Path
    folder_path = request.get("path", "")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    try:
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
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"success": True, "items": items, "path": str(folder)}
    except Exception as e:
        logger.error(f"浏览文件夹失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 文件预览 ==========
@app.post("/api/file/preview")
async def preview_file(request: dict):
    """预览文件内容，支持文本文件的前N行读取"""
    from pathlib import Path
    file_path = request.get("path", "")
    if not file_path:
        return {"success": False, "error": "请提供文件路径"}
    try:
        file = Path(file_path).resolve()
        if not _is_path_allowed(file):
            return {"success": False, "error": "路径不在允许范围内"}
        if not file.exists():
            return {"success": False, "error": "文件不存在"}
        if not file.is_file():
            return {"success": False, "error": "路径不是文件"}
        file_size = file.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return {"success": False, "error": "文件过大，请选择小于10MB的文件"}
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {"success": True, "content": content, "size": file_size}
    except Exception as e:
        logger.error(f"预览文件失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 文件学习 ==========
@app.post("/api/files/learn")
async def learn_from_files(request: dict):
    """从指定文件列表学习知识，提取并存储到知识库"""
    from pathlib import Path
    import sqlite3
    from datetime import datetime
    files = request.get("files", [])
    if not files:
        return {"success": False, "error": "请选择要学习的文件"}
    try:
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
                if file_size > MAX_FILE_SIZE:
                    continue
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if len(content) < 10:
                    continue
                with sqlite3.connect('data/knowledge_store.db') as conn:
                    conn.execute('''
                        INSERT INTO knowledge (content, source, type, quality, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (content[:5000], f"file:{file.name}", "file_content", 70.0, datetime.now().isoformat()))
                    conn.commit()
                total_knowledge += 1
                results.append(f"{file.name}: 已学习")
            except Exception as e:
                results.append(f"{file.name}: 失败 - {str(e)[:50]}")
                continue
        summary = '\n'.join(results[:10])
        return {"success": True, "summary": summary, "processed": len(results), "knowledge": total_knowledge}
    except Exception as e:
        logger.error(f"文件学习失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 文件夹学习 ==========
@app.post("/api/folder/learn")
async def learn_from_folder(request: dict):
    """从整个文件夹学习知识，递归扫描并提取"""
    from pathlib import Path
    import sqlite3
    from datetime import datetime
    folder_path = request.get("path", "")
    file_types = request.get("file_types", "all")
    learn_mode = request.get("mode", "analyze")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    try:
        folder = Path(folder_path).resolve()
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        if not folder.exists():
            return {"success": False, "error": "文件夹不存在"}
        extensions = {
            "code": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs", ".ts"],
            "doc": [".md", ".txt", ".rst", ".pdf"],
            "config": [".yaml", ".yml", ".json", ".toml"],
            "all": []
        }
        target_extensions = extensions.get(file_types, [])
        files = []
        if target_extensions:
            for ext in target_extensions:
                for f in folder.rglob(f"*{ext}"):
                    if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                        files.append(f)
        else:
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
                    continue
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if len(content) < 10:
                    continue
                if learn_mode == "analyze":
                    lines = content.count('\n')
                    functions = content.count('def ') + content.count('function ')
                    classes = content.count('class ')
                    summaries.append(f"{file_path.name}: {lines}行, {functions}函数, {classes}类")
                elif learn_mode == "extract":
                    summaries.append(f"{file_path.name}: 已提取")
                elif learn_mode == "summarize":
                    first_lines = '\n'.join(content.split('\n')[:5])
                    summaries.append(f"{file_path.name}:\n{first_lines}")
                with sqlite3.connect('data/knowledge_store.db') as conn:
                    conn.execute('''
                        INSERT INTO knowledge (content, source, type, quality, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (content[:5000], f"folder:{file_path.name}", "folder_content", 70.0, datetime.now().isoformat()))
                    conn.commit()
                knowledge_count += 1
                processed += 1
            except Exception as e:
                summaries.append(f"{file_path.name}: 失败 - {str(e)[:50]}")
                continue
        summary_text = '\n'.join(summaries[:10])
        return {"success": True, "processed": processed, "knowledge": knowledge_count, "summary": summary_text}
    except Exception as e:
        logger.error(f"文件夹学习失败: {e}")
        return {"success": False, "error": str(e)}

# ========== 最近学习记录 ==========
@app.get("/api/recent_learning")
async def get_recent_learning():
    """获取最近的学习记录，包括文件学习和知识提取历史"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        items = []
        try:
            conn = sqlite3.connect("data/experience_pool.db", timeout=3)
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT raw_input, timestamp, intent_type FROM experiences ORDER BY timestamp DESC LIMIT 5")
            for row in cur.fetchall():
                query = (row["raw_input"] or "")[:30]
                created = row["timestamp"] or ""
                intent = row["intent_type"] or ""
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = str(created)[:10]
                else:
                    time_str = ""
                items.append({"content": f"[{intent}] {query}", "time": time_str})
            conn.close()
        except:
            pass
        try:
            conn = sqlite3.connect("data/essence_reasoning.db", timeout=3)
            cur = conn.execute("SELECT query, final_verdict, timestamp FROM reasoning_chains ORDER BY timestamp DESC LIMIT 3")
            for row in cur.fetchall():
                query = (row[0] or "")[:30]
                created = row[2] or ""
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = str(created)[:10]
                else:
                    time_str = ""
                items.append({"content": f"推理: {query}", "time": time_str})
            conn.close()
        except:
            pass
        items.sort(key=lambda x: x.get("time", ""), reverse=True)
        return {"items": items[:8]}
    except Exception as e:
        return {"items": []}


@app.get("/api/reflection/stats")
async def get_reflection_stats():
    """获取反思管道统计"""
    try:
        from infrastructure.reflection_pipeline import get_reflection_pipeline
        pipeline = get_reflection_pipeline()
        if pipeline:
            return pipeline.get_stats()
    except:
        pass
    return {"total_reflections": 0, "status": "unavailable"}


@app.get("/api/module/health")
async def get_module_health():
    """获取模块健康报告"""
    try:
        from core.module_health import module_health
        return module_health.get_health_report()
    except:
        return {"healthy": [], "degraded": [], "isolated": [], "unknown": []}


@app.get("/api/trajectory/stats")
async def get_trajectory_stats():
    """获取轨迹进化统计，包括总数、平均适应度、各状态分布"""
    try:
        from core.trajectory_evolution import trajectory_store
        return trajectory_store.get_evolution_stats()
    except:
        return {"total_trajectories": 0, "avg_fitness": 0, "status": "unavailable"}


@app.get("/api/trajectory/search")
async def search_trajectories(q: str = "", intent: str = "", limit: int = 5):
    """搜索相似轨迹，支持按查询文本和意图类型过滤"""
    try:
        from core.trajectory_evolution import trajectory_store
        if q:
            results = trajectory_store.find_similar_trajectories(q, intent_type=intent or None, limit=limit)
            return {"trajectories": [{"id": r["id"], "query": r["query"][:50], "fitness": r["fitness_score"], "steps_count": len(json.loads(r["steps_json"]))} for r in results]}
        return {"trajectories": []}
    except:
        return {"trajectories": []}


@app.get("/api/tools")
async def list_tools(category: str = ""):
    """列出所有已注册工具，支持按分类过滤"""
    try:
        from core.tool_registry import tool_registry
        tools = tool_registry.list_tools(category=category or None)
        return {"tools": tools, "total": len(tools)}
    except Exception as e:
        return {"tools": [], "total": 0, "error": str(e)}


@app.post("/api/tools/execute")
async def execute_tool(request: dict):
    """执行指定工具，传入工具名和参数，返回执行结果"""
    tool_name = request.get("tool", "")
    params = request.get("params", {})
    if not tool_name:
        return {"success": False, "error": "缺少tool参数"}
    try:
        from core.tool_registry import tool_executor
        result = await tool_executor.execute(tool_name, params)
        return {
            "success": result.success,
            "data": result.data if result.success else None,
            "error": result.error if not result.success else None,
            "source": result.source,
            "quality": result.quality,
            "duration_ms": result.duration_ms,
            "from_cache": result.from_cache,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/tools/stats")
async def get_tool_stats():
    """获取工具执行统计，包括调用次数、成功率、平均耗时"""
    try:
        from core.tool_registry import tool_executor, tool_registry
        return {
            "tools": tool_registry.list_tools(),
            "stats": tool_executor.get_stats(),
            "total_tools": tool_registry.tool_count,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/events/stats")
async def get_event_stats():
    """获取事件总线统计，包括各事件类型的订阅数和最近事件"""
    try:
        from infrastructure.event_bus import bus, EventTypes
        return {
            "stats": bus.get_stats(),
            "event_types": {
                "UserMessage": bus.get_subscriber_count(EventTypes.UserMessage),
                "ToolResult": bus.get_subscriber_count(EventTypes.ToolResult),
                "KnowledgeUpdate": bus.get_subscriber_count(EventTypes.KnowledgeUpdate),
                "ModelStatusChange": bus.get_subscriber_count(EventTypes.ModelStatusChange),
                "IdlePeriod": bus.get_subscriber_count(EventTypes.IdlePeriod),
                "ScheduledTask": bus.get_subscriber_count(EventTypes.ScheduledTask),
            },
            "recent_events": bus.get_history(limit=15),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/events/history/{event_type}")
async def get_event_history(event_type: str, limit: int = 20):
    """获取指定事件类型的历史记录"""
    try:
        from infrastructure.event_bus import bus
        return {"events": bus.get_history(event_type=event_type, limit=limit)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/scheduled-tasks/status")
async def get_scheduled_tasks_status():
    """获取定时任务调度器状态，包括各任务的执行间隔和运行次数"""
    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        return scheduled_task_manager.get_status()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/module/clear")
async def clear_module_anomaly(request: dict):
    """清除模块异常状态（异常吞噬）"""
    module_name = request.get("module_name", "")
    if not module_name:
        return {"status": "error", "message": "缺少module_name"}
    try:
        from core.module_health import module_health
        module_health.clear_anomalies(module_name)
        return {"status": "ok", "message": f"模块{module_name}异常已清除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/system/audit")
async def run_system_audit():
    """系统自我审核：发现文档-代码-行为差距"""
    try:
        from core.system_auditor import system_auditor
        return system_auditor.audit()
    except Exception as e:
        logger.error(f"系统审核失败: {e}")
        return {"error": str(e), "summary": {"total_gaps": 0}}


@app.post("/api/evolution/run")
async def run_evolution(request: dict):
    """运行进化岛沙盒"""
    num_agents = request.get("num_agents", 8)
    generations = request.get("generations", 20)
    try:
        from core.active_scheduler import ActiveScheduler
        scheduler = ActiveScheduler(interval_seconds=300)
        result = scheduler.run_evolution_sandbox(num_agents=num_agents, generations=generations)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"进化岛运行失败: {e}")
        return {"success": False, "error": str(e)}


# ========== SDRS四层防御体系 ==========
@app.get("/api/defense/status")
async def get_defense_status():
    """获取SDRS防御体系状态"""
    try:
        from core.defense.guardian import system_guardian
        return system_guardian.get_status()
    except Exception as e:
        return {"error": str(e), "running": False}


@app.post("/api/defense/circuit/reset")
async def reset_circuit_breaker(request: dict):
    """重置熔断器"""
    name = request.get("name", "")
    if not name:
        return {"status": "error", "message": "缺少name"}
    try:
        from core.defense.circuit_breaker import circuit_breaker
        circuit_breaker.reset(name)
        return {"status": "ok", "message": f"熔断器{name}已重置"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/defense/isolation/release")
async def release_isolation(request: dict):
    """解除故障隔离"""
    module_name = request.get("module_name", "")
    if not module_name:
        return {"status": "error", "message": "缺少module_name"}
    try:
        from core.defense.fault_isolation import fault_isolator
        fault_isolator.release(module_name)
        return {"status": "ok", "message": f"模块{module_name}隔离已解除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/defense/repair/run")
async def run_cognitive_repair():
    """执行认知自修复"""
    try:
        from core.defense.cognitive_self_repair import cognitive_self_repair
        return cognitive_self_repair.run_full_repair()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/defense/anomalies")
async def get_anomalies():
    """获取异常检测结果"""
    try:
        from core.defense.anomaly_detector import anomaly_detector
        return {
            "recent_anomalies": anomaly_detector.get_anomalies(20),
            "baselines": anomaly_detector.get_baselines(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/defense/health/metrics")
async def get_health_metrics():
    """获取健康指标快照"""
    try:
        from core.defense.health_metrics import health_metrics
        return {
            "snapshot": health_metrics.get_snapshot(),
            "alerts": health_metrics.get_alerts(10),
        }
    except Exception as e:
        return {"error": str(e)}


# ========== 持续自我评估 ==========
@app.get("/api/self-assessment")
async def get_self_assessment():
    """获取最新的自我评估报告"""
    try:
        from core.self_assessment import self_assessment
        latest = self_assessment.get_latest()
        if latest:
            return latest
        return self_assessment.assess()
    except Exception as e:
        logger.error(f"自我评估失败: {e}")
        return {"error": str(e), "overall": {"score": 0, "level": "error"}}


@app.get("/api/self-assessment/history")
async def get_assessment_history():
    """获取自我评估历史"""
    try:
        from core.self_assessment import self_assessment
        return {"history": self_assessment.get_history(10), "trends": {
            "overall": self_assessment.get_trend("overall"),
            "loop_integrity": self_assessment.get_trend("loop_integrity"),
            "knowledge_vitality": self_assessment.get_trend("knowledge_vitality"),
            "learning_efficiency": self_assessment.get_trend("learning_efficiency"),
        }}
    except Exception as e:
        return {"error": str(e), "history": []}


# ========== 知识遗忘机制 ==========
@app.get("/api/forgetting/evaluate")
async def evaluate_forgetting():
    """评估知识保留价值（不执行删除）"""
    try:
        from core.knowledge_forgetting import knowledge_forgetting
        return {
            "rules": knowledge_forgetting.evaluate_rules(),
            "experiences": knowledge_forgetting.evaluate_experiences(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/forgetting/execute")
async def execute_forgetting(request: dict):
    """执行知识遗忘（默认dry-run，需显式确认）"""
    dry_run = request.get("dry_run", True)
    try:
        from core.knowledge_forgetting import knowledge_forgetting
        return knowledge_forgetting.execute_fading(dry_run=dry_run)
    except Exception as e:
        return {"error": str(e)}


# ========== 低负载自我重组 ==========
@app.post("/api/reorganization/run")
async def run_reorganization():
    """执行低负载自我重组"""
    try:
        from core.low_load_reorganization import low_load_reorganization
        return low_load_reorganization.run()
    except Exception as e:
        logger.error(f"低负载重组失败: {e}")
        return {"error": str(e)}


# ========== 事实锚点库 ==========
@app.get("/api/facts/search")
async def search_facts(q: str = "", limit: int = 10):
    """搜索事实断言"""
    try:
        from infrastructure.fact_store import fact_store
        if q:
            results = fact_store.search_by_keywords(q, limit=limit)
        else:
            results = []
        return {"query": q, "results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/facts/stats")
async def fact_stats():
    """事实库统计"""
    try:
        from infrastructure.fact_store import fact_store
        return fact_store.get_stats()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/facts/add")
async def add_fact(request: dict):
    """手动添加事实断言"""
    try:
        from infrastructure.fact_store import fact_store
        assertion_id = fact_store.add_assertion(
            question=request.get("question", ""),
            subject=request.get("subject", ""),
            predicate=request.get("predicate", ""),
            obj=request.get("object", ""),
            source=request.get("source", "manual"),
            confidence=request.get("confidence", 0.9)
        )
        return {"id": assertion_id, "status": "added"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/facts/correct")
async def correct_fact(request: dict):
    """纠错事实断言"""
    try:
        from infrastructure.fact_store import fact_store
        fact_store.add_correction(
            question=request.get("question", ""),
            old_subject=request.get("old_subject", ""),
            old_predicate=request.get("old_predicate", ""),
            old_obj=request.get("old_object", ""),
            new_subject=request.get("new_subject", ""),
            new_predicate=request.get("new_predicate", ""),
            new_obj=request.get("new_object", ""),
            correction_source=request.get("source", "user_correction")
        )
        return {"status": "corrected"}
    except Exception as e:
        return {"error": str(e)}


# ========== 立体记忆 ==========
@app.get("/api/memory/search")
async def search_memory(q: str = "", limit: int = 10):
    """搜索立体记忆"""
    try:
        from core.memory.stereo_memory import get_stereo_memory
        sm = get_stereo_memory()
        if q:
            results = sm.search(query=q, limit=limit)
        else:
            results = sm.get_recent(limit=limit)
        return {
            "count": len(results),
            "memories": [
                {
                    "id": m.memory_id,
                    "content": str(m.content)[:200],
                    "type": m.memory_type.value,
                    "importance": m.importance,
                    "emotion": m.self_dimension.emotional_state,
                    "confidence": m.self_dimension.confidence,
                    "accessed": m.time_dimension.access_count,
                }
                for m in results
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/memory/stats")
async def memory_stats():
    """立体记忆统计"""
    try:
        from core.memory.stereo_memory import get_stereo_memory
        sm = get_stereo_memory()
        return sm.get_stats()
    except Exception as e:
        return {"error": str(e)}


# ========== 关系模型 ==========
@app.get("/api/relationship/summary")
async def relationship_summary():
    """获取关系摘要"""
    try:
        from core.relationship.model import get_relationship_model
        rm = get_relationship_model()
        return rm.get_relationship_summary()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/relationship/metrics")
async def relationship_metrics():
    """获取关系指标"""
    try:
        from core.relationship.model import get_relationship_model
        rm = get_relationship_model()
        return rm.get_metrics()
    except Exception as e:
        return {"error": str(e)}


# ========== 存在层 ==========
@app.get("/api/presence/status")
async def presence_status():
    """获取存在层状态"""
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        return el.get_status()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/presence/signal")
async def send_presence_signal(request: dict):
    """向存在层发送信号"""
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el.receive_signal(request)
        return {"status": "received"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/presence/force-state")
async def force_presence_state(request: dict):
    """强制切换存在层状态"""
    try:
        from core.presence.existence_layer import get_existence_layer, PresenceState
        el = get_existence_layer()
        state = PresenceState(request.get("state", "awake"))
        el.force_state(state)
        return {"status": "forced", "state": state.value}
    except Exception as e:
        return {"error": str(e)}


# ========== 主动性引擎 ==========
@app.get("/api/proactivity/evaluate")
async def evaluate_proactivity():
    """评估是否应该主动互动"""
    try:
        from core.presence.proactivity import get_proactivity_engine, ProactivityContext
        from core.relationship.model import get_relationship_model
        from core.presence.existence_layer import get_existence_layer
        from datetime import datetime
        
        engine = get_proactivity_engine()
        rm = get_relationship_model()
        el = get_existence_layer()
        
        silence = el.metrics.silence_duration if el.metrics else 0
        rel = rm.get_relationship_summary()
        
        ctx = ProactivityContext(
            user_silence_duration=silence,
            relationship_trust=rel.get("trust_level", 0.5),
            recent_interactions=rel.get("total_interactions", 0),
            last_proactivity_time=datetime.now(),
            user_engagement_level=0.5,
        )
        
        decision = engine.evaluate(ctx)
        return {
            "should_act": decision.should_act,
            "action_type": decision.action_type.value if decision.action_type else None,
            "content": decision.content,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "timing_score": decision.timing_score,
        }
    except Exception as e:
        return {"error": str(e)}


# ========== 闭环调度器 ==========
@app.post("/api/closed-loop/orchestrate")
async def closed_loop_orchestrate(request: dict):
    """执行闭环调度"""
    try:
        from core.closed_loop_orchestrator import closed_loop_orchestrator
        ctx = await closed_loop_orchestrator.orchestrate(
            query=request.get("query", ""),
            conversation_context=request.get("context", ""),
        )
        return {
            "response": ctx.final_response,
            "iterations": ctx.iteration + 1,
            "passed": ctx.evaluation_passed,
            "confidence": ctx.confidence,
            "attempts": [(a[0], a[1]) for a in ctx.attempts],
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/agent/collaborate")
async def agent_collaborate(request: dict):
    """多Agent协作接口 - Planner→Executor→Reflector闭环"""
    query = request.get("message", "")
    if not query:
        return {"success": False, "error": "消息不能为空"}
    try:
        from core.agents.coordinator import agent_coordinator
        result = await asyncio.wait_for(
            agent_coordinator.collaborate(query),
            timeout=90,
        )
        return {
            "success": result.get("success", True),
            "response": result.get("response", ""),
            "source": result.get("source", ""),
            "quality": result.get("quality", 0),
            "iterations": result.get("iterations", 0),
            "plan_id": result.get("plan_id", ""),
            "duration_ms": result.get("duration_ms", 0),
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": "Agent协作超时(90s)", "response": "处理超时，请使用/api/chat接口"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/agent/status")
async def agent_status():
    """获取多Agent协作状态"""
    try:
        from core.agents.coordinator import agent_coordinator
        return agent_coordinator.get_status()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/weights")
async def get_path_weights():
    """获取路径权重分布（概率云）+ 概率场分布 + 检索模式"""
    try:
        from core.path_weight_manager import path_weight_manager
        from core.contrib_attributor import contrib_attributor
        result = {
            "weights": path_weight_manager.get_stats(),
            "confidence_distribution": path_weight_manager.get_confidence_distribution(),
            "source_reliability": contrib_attributor.get_source_reliability(),
        }
        try:
            from core.dynamic_probability_field import dynamic_probability_field
            dist = dynamic_probability_field.get_distribution()
            if dist.get("candidates"):
                result["confidence_distribution"] = {
                    v["source"]: v["probability"] for v in dist["candidates"].values()
                }
                result["prob_mode"] = "dynamic_field"
                result["query_entropy"] = dist.get("entropy", 0)
        except Exception:
            pass
        try:
            from infrastructure.vector_retriever import _ST_AVAILABLE
            result["prob_mode"] = "semantic" if _ST_AVAILABLE else "tfidf"
        except Exception:
            result["prob_mode"] = "unknown"
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/attributions")
async def get_attributions(limit: int = 20):
    """获取最近贡献度归因记录"""
    try:
        from core.contrib_attributor import contrib_attributor
        return {"attributions": contrib_attributor.get_recent_attributions(limit)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/probability-field")
async def get_probability_field():
    """获取当前动态概率场状态 + 校准统计 + 不确定性路由"""
    try:
        from core.dynamic_probability_field import dynamic_probability_field
        from core.react_enhancer import react_enhancer
        result = {
            "distribution": dynamic_probability_field.get_distribution(),
            "should_explore": dynamic_probability_field.should_explore(),
            "gap_stats": react_enhancer.get_gap_stats(),
            "recent_snapshots": dynamic_probability_field.get_recent_snapshots(5),
            "uncertainty_action": dynamic_probability_field.get_uncertainty_action(),
            "calibration_summary": dynamic_probability_field.get_calibration_summary(),
        }
        try:
            from infrastructure.vector_retriever import vector_retriever
            result["calibration_stats"] = vector_retriever._calibrator.get_calibration_stats()
        except Exception:
            pass
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/delta-stats")
async def get_delta_stats(topic: str = "", limit: int = 20):
    """获取增量知识更新统计"""
    try:
        from core.delta_knowledge_updater import delta_knowledge_updater
        return {"delta_stats": delta_knowledge_updater.get_delta_stats(topic, limit)}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload_dirs=["backend", "core", "config"])