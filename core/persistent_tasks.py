"""
永不放弃的任务系统 - Persistent Task System
所有任务持久化，直到成功或需要人工介入
"""
import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request
from core.ports.adapters import get_storage_port


class PersistentTaskSystem:
    """永不放弃的任务系统 - 所有任务持久化，直到成功"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.tasks: Dict[str, Dict] = {}
        self.queue = asyncio.Queue()
        self.db_path = Path("data/persistent_tasks.db")
        self._init_database()
        self._start_workers()
        
        logger.info("🔥 永不放弃的任务系统已启动")
    
    def _init_database(self):
        """初始化持久化数据库"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        db = get_storage_port(str(self.db_path))
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                question TEXT,
                context TEXT,
                status TEXT,
                attempts INTEGER,
                max_attempts INTEGER,
                created_at TEXT,
                last_attempt TEXT,
                error TEXT,
                result TEXT,
                strategies_tried TEXT,
                partial_results TEXT
            )
        """, commit=True)
    
    def _start_workers(self):
        """启动后台工作者"""
        for i in range(3):  # 3个并行工作者
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
    
    async def submit(self, question: str, context: dict = None) -> str:
        """提交任务 - 立即返回task_id"""
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "question": question,
            "context": context or {},
            "status": "pending",
            "attempts": 0,
            "max_attempts": 100,  # 永不放弃
            "created_at": datetime.now().isoformat(),
            "last_attempt": None,
            "error": None,
            "result": None,
            "strategies_tried": [],
            "partial_results": []
        }
        
        self.tasks[task_id] = task
        await self.queue.put(task_id)
        self._save_task(task)
        
        logger.info(f"📋 任务已提交: {task_id[:8]} - {question[:30]}...")
        
        return task_id
    
    async def _worker(self, worker_name: str):
        """后台工作者 - 永不停止"""
        logger.info(f"🔧 {worker_name} 已启动")
        
        while True:
            try:
                task_id = await self.queue.get()
                task = self.tasks.get(task_id)
                
                if not task:
                    task = self._load_task(task_id)
                    if not task:
                        continue
                    self.tasks[task_id] = task
                
                # 检查是否达到尝试上限
                if task["attempts"] >= task["max_attempts"]:
                    task["status"] = "need_help"
                    task["error"] = f"已尝试{task['attempts']}种方法，需要人工介入"
                    self._save_task(task)
                    logger.warning(f"⚠️ 任务 {task_id[:8]} 需要人工介入")
                    continue
                
                task["attempts"] += 1
                task["last_attempt"] = datetime.now().isoformat()
                task["status"] = "processing"
                
                logger.info(f"🔄 {worker_name} 处理任务 {task_id[:8]} (尝试 {task['attempts']}/{task['max_attempts']})")
                
                # 尝试所有可能的方法
                result = await self._try_all_strategies(task)
                
                if result["success"]:
                    task["status"] = "completed"
                    task["result"] = result["answer"]
                    self._save_task(task)
                    logger.info(f"✅ 任务 {task_id[:8]} 完成！策略: {result['strategy']}")
                    # TODO: 通知用户
                else:
                    task["status"] = "retrying"
                    task["error"] = result["error"]
                    task["strategies_tried"].append(result["strategy"])
                    if "partial" in result:
                        task["partial_results"].append(result["partial"])
                    
                    self._save_task(task)
                    
                    # 继续尝试，不要放弃！
                    await self.queue.put(task_id)
                    
                    # 指数退避
                    delay = min(2 ** min(task["attempts"], 10), 300)
                    logger.info(f"🔄 任务 {task_id[:8]} 将在 {delay}秒后重试")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ {worker_name} 异常: {e}")
                await asyncio.sleep(1)
            
            finally:
                self.queue.task_done()
    
    async def _try_all_strategies(self, task: Dict) -> Dict:
        """尝试所有策略，只要有一个成功就返回"""
        
        strategies = [
            ("直接模型调用", self._try_direct_model),
            ("备选模型", self._try_alternative_model),
            ("工具调用", self._try_tools),
            ("知识检索", self._try_search),
            ("问题分解", self._try_decompose),
            ("RAG检索", self._try_rag),
            ("代码生成", self._try_code_generation),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                result = await strategy_func(task["question"], task["context"])
                
                if result.get("success"):
                    return {
                        "success": True,
                        "answer": result["answer"],
                        "strategy": strategy_name
                    }
                else:
                    logger.warning(f"策略 {strategy_name} 未成功: {result.get('error', 'unknown')}")
                    
            except Exception as e:
                logger.error(f"策略 {strategy_name} 异常: {e}")
                task["partial_results"].append({
                    "strategy": strategy_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return {
            "success": False,
            "error": "所有策略都失败",
            "strategy": "none",
            "partial": task["partial_results"][-1] if task["partial_results"] else None
        }
    
    async def _try_direct_model(self, question: str, context: dict) -> Dict:
        """策略1: 直接调用模型"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ollama_chat_request(
                    base_url="http://localhost:11434",
                    model="qwen2.5:7b",
                    prompt=question,
                    timeout=15
                )
            )
            content = result.get("content", "")
            if content and len(content) > 20:
                return {"success": True, "answer": content}
        except Exception:
            logger.warning("操作降级跳过")
        return {"success": False, "error": "直接模型调用失败"}
    
    async def _try_alternative_model(self, question: str, context: dict) -> Dict:
        """策略2: 尝试其他模型"""
        try:
            import requests
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get("http://localhost:11434/api/tags", timeout=3)
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models[1:3]:
                    try:
                        model_name = model["name"]
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda mn=model_name: ollama_chat_request(
                                base_url="http://localhost:11434",
                                model=mn,
                                prompt=question,
                                timeout=10
                            )
                        )
                        content = result.get("content", "")
                        if content and len(content) > 20:
                            return {"success": True, "answer": content}
                    except Exception:
                        continue
        except Exception:
            logger.warning("操作降级跳过")
        return {"success": False, "error": "备选模型调用失败"}
    
    async def _try_tools(self, question: str, context: dict) -> Dict:
        """策略3: 调用工具"""
        try:
            from core.tool_registry import tool_registry as registry
            tools = registry.list_tools()
            
            # 根据问题选择合适的工具
            question_lower = question.lower()
            
            if any(kw in question_lower for kw in ["计算", "数学", "加减乘除"]):
                result = registry.execute("math_calculator", query=question)
                if hasattr(result, 'output') and result.output:
                    return {"success": True, "answer": str(result.output)}
            
            if any(kw in question_lower for kw in ["搜索", "查找", "查询"]):
                result = registry.execute("web_search", query=question)
                if hasattr(result, 'output') and result.output:
                    return {"success": True, "answer": str(result.output)}
                    
        except Exception as e:
            logger.error(f"工具调用失败: {e}")
        return {"success": False, "error": "工具调用失败"}
    
    async def _try_search(self, question: str, context: dict) -> Dict:
        """策略4: 搜索知识库"""
        try:
            db = get_storage_port("data/knowledge_store.db")
            row = db.query_one(
                "SELECT answer FROM knowledge_items WHERE answer LIKE ? LIMIT 1",
                (f"%{question[:30]}%",)
            )
            if row:
                return {"success": True, "answer": row[0]}
        except Exception:
            logger.warning("操作降级跳过")
        return {"success": False, "error": "知识检索失败"}
    
    async def _try_decompose(self, question: str, context: dict) -> Dict:
        """策略5: 分解问题"""
        # 简单分解：按问号或逗号分割
        sub_questions = question.replace("？", "?").replace("，", ",").split("?")
        sub_questions = [q.strip() for q in sub_questions if q.strip()]
        
        if len(sub_questions) > 1:
            # 递归解决子问题
            answers = []
            for sub_q in sub_questions[:3]:  # 最多处理3个子问题
                result = await self._try_direct_model(sub_q, context)
                if result["success"]:
                    answers.append(f"{sub_q}: {result['answer']}")
            
            if answers:
                return {"success": True, "answer": "\n\n".join(answers)}
        
        return {"success": False, "error": "问题分解失败"}
    
    async def _try_rag(self, question: str, context: dict) -> Dict:
        """策略6: RAG检索"""
        try:
            db = get_storage_port("data/experience_pool.db")
            row = db.query_one(
                "SELECT response FROM experiences WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 1",
                (f"%{question[:20]}%",)
            )
            if row and row['response']:
                return {"success": True, "answer": row['response']}
        except Exception:
            logger.warning("操作降级跳过")
        return {"success": False, "error": "RAG检索失败"}
    
    async def _try_code_generation(self, question: str, context: dict) -> Dict:
        """策略7: 代码生成"""
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ["代码", "编程", "写代码", "函数"]):
            # 生成代码框架
            code_template = f"""# 关于: {question}

# 这是一个代码生成模板，请根据具体需求修改

def solution():
    \"\"\"解决: {question}\"\"\"
    # TODO: 实现具体逻辑
    pass

if __name__ == "__main__":
    result = solution()
    print(result)
"""
            return {"success": True, "answer": code_template}
        
        return {"success": False, "error": "不涉及代码生成"}
    
    def _save_task(self, task: Dict):
        """持久化任务"""
        try:
            db = get_storage_port(str(self.db_path))
            db.execute("""
                INSERT OR REPLACE INTO tasks VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                task["task_id"],
                task["question"],
                json.dumps(task["context"]),
                task["status"],
                task["attempts"],
                task["max_attempts"],
                task["created_at"],
                task["last_attempt"],
                task["error"],
                task["result"],
                json.dumps(task["strategies_tried"]),
                json.dumps(task["partial_results"])
            ), commit=True)
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
    
    def _load_task(self, task_id: str) -> Optional[Dict]:
        """加载任务"""
        try:
            db = get_storage_port(str(self.db_path))
            row = db.query_one("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            
            if row:
                return {
                    "task_id": row['task_id'],
                    "question": row['question'],
                    "context": json.loads(row['context']),
                    "status": row['status'],
                    "attempts": row['attempts'],
                    "max_attempts": row['max_attempts'],
                    "created_at": row['created_at'],
                    "last_attempt": row['last_attempt'],
                    "error": row['error'],
                    "result": row['result'],
                    "strategies_tried": json.loads(row['strategies_tried']),
                    "partial_results": json.loads(row['partial_results'])
                }
        except Exception:
            logger.warning("操作降级跳过")
        return None
    
    async def get_task_status(self, task_id: str) -> Dict:
        """查询任务状态 - 用户随时可查"""
        task = self.tasks.get(task_id) or self._load_task(task_id)
        
        if not task:
            return {"status": "not_found"}
        
        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "attempts": task["attempts"],
            "max_attempts": task["max_attempts"],
            "created_at": task["created_at"],
            "last_attempt": task["last_attempt"],
            "error": task["error"],
            "result": task["result"],
            "partial_results": task["partial_results"][-5:],
            "strategies_tried": task["strategies_tried"][-10:]
        }


# 全局单例
persistent_task_system = PersistentTaskSystem()