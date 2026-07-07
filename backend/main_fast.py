"""
简化版后端 - 快速启动
"""
import sys
import os

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
import time
import json
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from loguru import logger

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

_log_dir = ROOT_DIR / "logs"
_log_dir.mkdir(exist_ok=True)
logger.add(
    str(_log_dir / "server_{time:YYYY-MM-DD}.log"),
    rotation="00:00",
    retention="7 days",
    compression="gz",
    encoding="utf-8",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
)

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

import concurrent.futures
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="pioneer")

from backend.lifespan import lifespan, _proactivity_subscribers, _enqueue_proactivity
from backend.routers.health import router as health_router
from backend.routers.system import router as system_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.chat import router as chat_router
from backend.routers.evolution import router as evolution_router

app = FastAPI(
    title="联盟拓荒者 API",
    description="生产级自我进化智能体系统 API",
    version="3.7.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(evolution_router, prefix="/api")

FRONTEND_DIR = ROOT_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


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


@app.get("/")
async def root():
    frontend_index = FRONTEND_DIR / "index.html"
    if frontend_index.exists():
        with open(frontend_index, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"message": "联盟拓荒者 API", "docs": "/docs"}


@app.get("/api/proactivity/stream")
async def proactivity_stream():
    import asyncio as _asyncio
    q = _asyncio.Queue(maxsize=20)
    _proactivity_subscribers.append(q)
    logger.info(f"🔌 SSE subscriber added (total: {len(_proactivity_subscribers)})")

    async def _generator():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'content': 'SSE连接已建立'}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    msg = await _asyncio.wait_for(q.get(), timeout=30.0)
                    data = json.dumps(msg, ensure_ascii=False)
                    logger.info(f"📨 SSE sending: type={msg.get('type') if isinstance(msg, dict) else '?'}")
                    yield f"data: {data}\n\n"
                except _asyncio.TimeoutError:
                    yield f": keepalive\n\n"
                except Exception as e:
                    logger.warning(f"SSE generator error: {e}")
                    await _asyncio.sleep(5)
        finally:
            if q in _proactivity_subscribers:
                _proactivity_subscribers.remove(q)
            logger.info(f"🔌 SSE subscriber removed (remaining: {len(_proactivity_subscribers)})")

    return StreamingResponse(_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.post("/api/proactivity/test")
async def proactivity_test():
    _enqueue_proactivity({
        "type": "greeting",
        "content": "主动性SSE推送测试成功！如果你在前端看到这条消息，说明SSE端到端链路完整。",
        "recommendations": ["继续使用系统", "查看全景面板"]
    })
    return {"status": "ok", "message": "测试消息已广播到SSE订阅者", "subscribers": len(_proactivity_subscribers)}


async def solve_history_query(query: str) -> str:
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
    except Exception:
        return "历史记录功能正在初始化，请稍后再试。"


async def query_knowledge_base(query: str) -> str:
    try:
        import sqlite3
        conn = sqlite3.connect("data/knowledge_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query}%",))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


async def query_experience_pool(query: str) -> str:
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM experiences WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{query[:20]}%",))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def generate_rule_based_response(query: str, intent_type: str) -> str:
    query_lower = query.lower()

    if any(kw in query_lower for kw in ["代码", "编程", "写代码", "函数", "程序"]):
        return f"""我理解你需要代码方面的帮助。关于"{query}"，我可以：

1. **代码生成** - 请告诉我具体需求，如"写一个Python函数计算斐波那契数列"
2. **代码解释** - 请提供代码，我会解释其工作原理
3. **代码优化** - 请提供代码，我会给出优化建议
4. **Bug修复** - 请描述问题和代码，我会帮你分析

请告诉我更具体的需求，我会尽力帮助你。"""

    if any(kw in query_lower for kw in ["什么是", "是什么", "介绍", "解释"]):
        topic = query.replace("什么是", "").replace("是什么", "").replace("介绍一下", "").strip()
        return f"""关于"{topic}"，我正在学习相关知识。

目前我可以通过以下方式帮助你：
1. **基础解释** - 提供概念定义和基本原理
2. **实例说明** - 通过具体例子帮助理解
3. **应用场景** - 说明实际应用和案例

请稍后重试，或尝试更具体的问题，如"{topic}的定义是什么"或"{topic}的应用有哪些"。"""

    if any(kw in query_lower for kw in ["如何", "怎么", "怎样"]):
        return f"""关于"{query}"，这是一个很好的问题。

我建议：
1. **分解问题** - 将复杂问题拆分为小步骤
2. **查阅文档** - 参考相关技术文档
3. **实践尝试** - 动手实践是最好的学习方式

请告诉我更具体的场景，我会给出更详细的指导。"""

    return f"""我收到了你的问题："{query}"

虽然我暂时无法给出完整答案，但我会记住这个问题并继续学习。

你可以：
1. **换个方式提问** - 尝试更具体或更简单的表述
2. **提供更多上下文** - 帮助我更好地理解你的需求
3. **稍后重试** - 我会不断学习和改进

我会持续进化，下次遇到这个问题时，我会做得更好。"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload_dirs=["backend", "core", "config"])
