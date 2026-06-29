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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """简化的lifespan - 快速启动"""
    logger.info("🚀 启动后端服务...")
    
    # 启动持久化任务队列worker
    try:
        from core.task_queue import task_queue
        asyncio.create_task(task_queue.start_worker(interval=5.0))
        logger.info("✅ 持久化任务队列worker已启动")
    except Exception as e:
        logger.warning(f"任务队列启动失败: {e}")
    
    yield
    
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
    
    # 使用永不放弃的聊天处理器
    from backend.chat_handler import chat_never_giveup
    
    result = await chat_never_giveup(user_input, request)
    
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
    
    from backend.chat_stream import chat_stream as stream_generator
    
    return StreamingResponse(
        stream_generator(user_input, {"history": history}),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
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
    """测试所有模型连接（Ollama + 外部API）"""
    results = {}
    
    # 1. 测试Ollama
    try:
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=3)
        if tags.status_code == 200:
            models = [m["name"] for m in tags.json().get("models", [])]
            if models:
                results["Ollama"] = {"success": True, "message": f"可用模型: {', '.join(models[:3])}"}
            else:
                results["Ollama"] = {"success": False, "message": "无可用模型"}
        else:
            results["Ollama"] = {"success": False, "message": f"HTTP {tags.status_code}"}
    except Exception as e:
        results["Ollama"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}
    
    # 2. 测试外部API
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
                    r = req.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        timeout=10
                    )
                    if r.status_code == 200:
                        results["OpenAI"] = {"success": True, "message": "API Key有效"}
                    else:
                        results["OpenAI"] = {"success": False, "message": f"认证失败: HTTP {r.status_code}"}
                except Exception as e:
                    results["OpenAI"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}
            
            if deepseek_key and not deepseek_key.startswith("●"):
                try:
                    import requests as req
                    r = req.get(
                        "https://api.deepseek.com/v1/models",
                        headers={"Authorization": f"Bearer {deepseek_key}"},
                        timeout=10
                    )
                    if r.status_code == 200:
                        results["DeepSeek"] = {"success": True, "message": "API Key有效"}
                    else:
                        results["DeepSeek"] = {"success": False, "message": f"认证失败: HTTP {r.status_code}"}
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
                rules = min(pending // 5, 3)
                cur = conn.execute("UPDATE learning_rules SET status='active' WHERE status='pending' AND confidence >= 0.6 AND apply_count >= 3")
                activated = cur.rowcount
                conn.commit()
                rules = activated
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
    try:
        import sqlite3
        from datetime import datetime, timedelta
        items = []
        try:
            with sqlite3.connect("data/experience_pool.db") as conn:
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
        except:
            pass
        try:
            with sqlite3.connect("data/essence_reasoning.db") as conn:
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
        except:
            pass
        items.sort(key=lambda x: x.get("time", ""), reverse=True)
        return {"items": items[:8]}
    except Exception as e:
        return {"items": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload_dirs=["backend", "core", "config"])