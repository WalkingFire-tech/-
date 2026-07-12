"""
持久化任务队列 + 基因参数微调 + 认知时差

核心改进：
1. 任务存入SQLite，服务重启不丢失，失败指数退避重试
2. 基因库=参数微调（不是存文本），每次交互微调系统行为参数
3. 认知时差：后台任务延迟启动，不与主请求抢占资源
4. 空闲检测：CPU/交互空闲时才启动深度任务
"""
import asyncio
import time
import json
import sqlite3
import threading
import os
from datetime import datetime
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request
from infrastructure.database_manager import DatabaseManager

_write_lock = threading.Lock()


# ========== 基因参数定义 ==========
GENE_DEFAULTS = {
    "curiosity_weight": 0.7,
    "caution_threshold": 0.5,
    "learning_rate": 0.1,
    "timeout_tolerance": 1.0,
    "depth_preference": 0.6,
    "confidence_bias": 0.5,
    "retry_aggression": 0.5,
    "knowledge_solidify_threshold": 80.0,
    "model_preference_speed": 0.5,
    "self_doubt_frequency": 0.3,
}

# 基因安全基线：无论怎么突变，都不能超出这个区间
# 防止自我毁灭性突变（如self_doubt_frequency调到1.0导致永久性自我怀疑）
GENE_SAFETY_BOUNDS = {
    "curiosity_weight": (0.2, 0.95),
    "caution_threshold": (0.1, 0.9),
    "learning_rate": (0.01, 0.5),
    "timeout_tolerance": (0.3, 2.0),
    "depth_preference": (0.2, 0.9),
    "confidence_bias": (0.1, 0.9),
    "retry_aggression": (0.1, 0.9),
    "knowledge_solidify_threshold": (50.0, 100.0),
    "model_preference_speed": (0.1, 0.9),
    "self_doubt_frequency": (0.1, 0.8),
}


class GenePool:
    """基因池 - 系统行为参数的微调演化"""

    def __init__(self, db_path: str = "data/gene_pool.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._genes = self._load_genes()
        self._safety_violations = 0

    def _connect(self):
        return DatabaseManager.get(self.db_path)

    def _write_op(self, func, *args, **kwargs):
        with self._lock:
            db = self._connect()
            return func(db, *args, **kwargs)

    def _init_db(self):
        def _do(db):
            db.executescript('''
                CREATE TABLE IF NOT EXISTS genes (
                    key TEXT PRIMARY KEY,
                    value REAL NOT NULL,
                    mutation_count INTEGER DEFAULT 0,
                    last_mutated TEXT
                );
                CREATE TABLE IF NOT EXISTS mutations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gene_key TEXT,
                    old_value REAL,
                    new_value REAL,
                    delta REAL,
                    trigger TEXT,
                    context TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS safety_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gene_key TEXT,
                    attempted_value REAL,
                    bound_type TEXT,
                    bound_value REAL,
                    trigger TEXT,
                    timestamp TEXT
                )
            ''')
        self._write_op(_do)

    def _load_genes(self) -> dict:
        try:
            db = self._connect()
            rows = db.query("SELECT key, value FROM genes")
            genes = {row[0]: row[1] for row in rows}
            for k, v in GENE_DEFAULTS.items():
                if k not in genes:
                    genes[k] = v
            return genes
        except Exception:
            return dict(GENE_DEFAULTS)

    def get(self, key: str) -> float:
        return self._genes.get(key, GENE_DEFAULTS.get(key, 0.5))

    # 【R2渐进注入】待分步生效的基因变更队列
    # 格式: {key: {"remaining_delta": float, "step": int, "trigger": str}}
    _gradual_injection_queue = {}

    GRADUAL_INJECTION_THRESHOLD = 0.1
    GRADUAL_STEPS = [0.01, 0.20, 1.0]

    def mutate(self, key: str, delta: float, trigger: str = "", context: str = ""):
        """微调基因参数（小量增量，强制安全基线，R2渐进注入门控）"""
        old = self._genes.get(key, GENE_DEFAULTS.get(key, 0.5))

        # R2渐进注入：|delta|超过阈值时，分步生效而非立即
        actual_delta = delta
        if abs(delta) >= self.GRADUAL_INJECTION_THRESHOLD and trigger != "gradual_injection":
            if key not in self._gradual_injection_queue:
                self._gradual_injection_queue[key] = {
                    "remaining_delta": delta,
                    "step": 0,
                    "trigger": trigger,
                }
                step_ratio = self.GRADUAL_STEPS[0]
                actual_delta = delta * step_ratio
                logger.info(f"🧬 R2渐进注入: {key} Δ{delta:+.3f} 超阈值，第1步注入{step_ratio:.0%}(Δ{actual_delta:+.4f})")
            else:
                actual_delta = delta
        elif key in self._gradual_injection_queue:
            _gi = self._gradual_injection_queue[key]
            _gi["step"] += 1
            if _gi["step"] < len(self.GRADUAL_STEPS):
                step_ratio = self.GRADUAL_STEPS[_gi["step"]]
                actual_delta = _gi["remaining_delta"] * step_ratio
                logger.info(f"🧬 R2渐进注入: {key} 第{_gi['step']+1}步注入{step_ratio:.0%}(Δ{actual_delta:+.4f})")
            else:
                actual_delta = _gi["remaining_delta"]
                del self._gradual_injection_queue[key]
                logger.info(f"🧬 R2渐进注入: {key} 全量注入完成")

        new = old + actual_delta

        bounds = GENE_SAFETY_BOUNDS.get(key)
        if bounds:
            min_val, max_val = bounds
            if new < min_val:
                new = min_val
                if old > min_val:
                    self._record_safety_violation(key, old + delta, "lower_bound", min_val, trigger)
                    logger.debug(f"🧬 基因安全基线触发: {key} 降至下限 {min_val}")
            elif new > max_val:
                new = max_val
                if old < max_val:
                    self._record_safety_violation(key, old + delta, "upper_bound", max_val, trigger)
                    logger.debug(f"🧬 基因安全基线触发: {key} 升至上限 {max_val}")

        self._genes[key] = new

        def _do(db):
            db.execute("INSERT OR REPLACE INTO genes (key, value, mutation_count, last_mutated) VALUES (?, ?, COALESCE((SELECT mutation_count FROM genes WHERE key=?), 0) + 1, ?)",
                      (key, new, key, datetime.now().isoformat()), commit=True)
            db.execute("INSERT INTO mutations (gene_key, old_value, new_value, delta, trigger, context, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (key, old, new, delta, trigger, context[:200], datetime.now().isoformat()), commit=True)

        try:
            self._write_op(_do)
        except Exception as e:
            logger.debug(f"基因突变记录失败: {e}")

        logger.info(f"🧬 基因突变: {key} {old:.3f}→{new:.3f} (Δ{delta:+.3f}, 触发={trigger})")

    def learn_from_interaction(self, elapsed: float, success: bool, user_feedback: int = 0, model_used: str = ""):
        """从交互中学习，微调基因（含拮抗平衡）"""
        if elapsed > 30:
            self.mutate("timeout_tolerance", 0.05, "slow_response")
            self.mutate("depth_preference", -0.02, "slow_response")
            # 拮抗平衡：耐心增加时，自我怀疑也必须微增，防止固执等待
            self.mutate("self_doubt_frequency", 0.02, "antagonistic_timeout")
        if elapsed < 3 and success:
            self.mutate("confidence_bias", 0.02, "fast_success")

        if not success:
            self.mutate("self_doubt_frequency", 0.05, "failure")
            self.mutate("retry_aggression", 0.03, "failure")
        else:
            self.mutate("self_doubt_frequency", -0.01, "success")

        if user_feedback > 0:
            self.mutate("curiosity_weight", 0.05, "positive_feedback")
            self.mutate("confidence_bias", 0.03, "positive_feedback")
        elif user_feedback < 0:
            self.mutate("caution_threshold", 0.05, "negative_feedback")
            self.mutate("self_doubt_frequency", 0.05, "negative_feedback")

        if "coder" in model_used.lower():
            self.mutate("model_preference_speed", 0.02, "fast_model_used")

    def get_all(self) -> dict:
        return dict(self._genes)

    def _record_safety_violation(self, gene_key: str, attempted_value: float, bound_type: str, bound_value: float, trigger: str):
        self._safety_violations += 1
        def _do(db):
            db.execute("INSERT INTO safety_violations (gene_key, attempted_value, bound_type, bound_value, trigger, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                         (gene_key, attempted_value, bound_type, bound_value, trigger, datetime.now().isoformat()), commit=True)
        try:
            self._write_op(_do)
        except Exception:
            pass
        logger.warning(f"🧬 基因安全违规 #{self._safety_violations}: {gene_key} 尝试={attempted_value:.3f} {bound_type}={bound_value:.3f}")

    def get_safety_violations(self) -> dict:
        try:
            db = self._connect()
            row = db.query_one("SELECT COUNT(*) FROM safety_violations")
            total = row[0]
            rows = db.query("SELECT gene_key, COUNT(*) FROM safety_violations GROUP BY gene_key ORDER BY COUNT(*) DESC")
            by_gene = {r[0]: r[1] for r in rows}
            return {"total": total, "by_gene": by_gene}
        except Exception:
            return {"total": self._safety_violations, "by_gene": {}}

    def get_expression_profile(self) -> dict:
        """基因表达谱：雷达图数据，展示系统当前性格"""
        g = self._genes
        aggressive = (g.get("curiosity_weight", 0.5) + g.get("retry_aggression", 0.5) + g.get("depth_preference", 0.5)) / 3
        cautious = (g.get("caution_threshold", 0.5) + g.get("self_doubt_frequency", 0.5)) / 2
        patient = g.get("timeout_tolerance", 0.5)
        confident = g.get("confidence_bias", 0.5)
        fast = g.get("model_preference_speed", 0.5)
        personality = "激进型" if aggressive > 0.6 else ("稳健型" if cautious > 0.6 else "均衡型")
        return {
            "radar": {"aggressive": round(aggressive, 3), "cautious": round(cautious, 3),
                      "patient": round(patient, 3), "confident": round(confident, 3), "fast": round(fast, 3)},
            "personality": personality,
            "genes": dict(self._genes)
        }

    def get_mutation_history(self, limit: int = 20) -> list:
        try:
            db = self._connect()
            rows = db.query("SELECT gene_key, old_value, new_value, delta, trigger, timestamp FROM mutations ORDER BY id DESC LIMIT ?", (limit,))
            return [{"key": r[0], "old": r[1], "new": r[2], "delta": r[3], "trigger": r[4], "time": r[5]} for r in rows]
        except Exception:
            return []


gene_pool = GenePool()


class PersistentTaskQueue:
    def __init__(self, db_path: str = "data/task_queue.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._running = False
        self._last_user_interaction = time.time()
        self._idle_threshold = 10.0

    def _connect(self):
        return DatabaseManager.get(self.db_path)

    def _write_op(self, func, *args, **kwargs):
        with self._lock:
            db = self._connect()
            return func(db, *args, **kwargs)

    def _init_db(self):
        def _do(db):
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 5,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    next_retry_at TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS failed_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_task_id INTEGER,
                    task_type TEXT,
                    payload TEXT,
                    failure_reason TEXT,
                    created_at TEXT,
                    recovered_at TEXT,
                    recovered INTEGER DEFAULT 0
                )
            ''')
            try:
                db.query_one("SELECT priority FROM tasks LIMIT 1")
            except sqlite3.OperationalError:
                db.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 5", commit=True)
                logger.info("✅ 已迁移tasks表：添加priority列")
        self._write_op(_do)

    def notify_user_interaction(self):
        """用户交互通知——更新空闲时间戳"""
        self._last_user_interaction = time.time()

    def _is_idle(self) -> bool:
        """检测系统是否空闲（用户无交互超过阈值）"""
        return (time.time() - self._last_user_interaction) > self._idle_threshold

    def enqueue(self, task_type: str, payload: dict, max_retries: int = 3, priority: int = 5, delay_seconds: float = 0) -> int:
        next_retry = None
        if delay_seconds > 0:
            next_retry = datetime.fromtimestamp(time.time() + delay_seconds).isoformat()

        def _do(db):
            cur = db.execute(
                "INSERT INTO tasks (task_type, payload, status, priority, max_retries, next_retry_at, created_at) VALUES (?, ?, 'pending', ?, ?, ?, ?)",
                (task_type, json.dumps(payload, ensure_ascii=False), priority, max_retries, next_retry, datetime.now().isoformat()),
                commit=True
            )
            return cur.lastrowid

        task_id = self._write_op(_do)
        logger.info(f"📋 任务入队: #{task_id} type={task_type} priority={priority}" + (f" 延迟{delay_seconds:.0f}秒" if delay_seconds > 0 else ""))
        return task_id

    def _get_pending_tasks(self, limit: int = 3) -> list:
        db = self._connect()
        now = datetime.now().isoformat()
        rows = db.query(
            "SELECT id, task_type, payload, retry_count, priority FROM tasks WHERE status='pending' AND (next_retry_at IS NULL OR next_retry_at <= ?) ORDER BY priority DESC, created_at ASC LIMIT ?",
            (now, limit)
        )
        return [{"id": r[0], "task_type": r[1], "payload": json.loads(r[2]), "retry_count": r[3], "priority": r[4]} for r in rows]

    def _mark_running(self, task_id: int):
        def _do(db):
            db.execute("UPDATE tasks SET status='running', started_at=? WHERE id=?", (datetime.now().isoformat(), task_id), commit=True)
        self._write_op(_do)

    def _mark_completed(self, task_id: int, result: str = ""):
        def _do(db):
            db.execute("UPDATE tasks SET status='completed', completed_at=?, result=? WHERE id=?",
                       (datetime.now().isoformat(), result[:500], task_id), commit=True)
        self._write_op(_do)

    def _mark_failed(self, task_id: int, error: str, retry_count: int, max_retries: int):
        def _do(db):
            if retry_count < max_retries:
                delay = min(5 * (2 ** retry_count), 120)
                next_retry = datetime.fromtimestamp(time.time() + delay).isoformat()
                db.execute("UPDATE tasks SET status='pending', retry_count=?, next_retry_at=?, error=? WHERE id=?",
                           (retry_count + 1, next_retry, error[:200], task_id), commit=True)
                logger.info(f"🔄 任务#{task_id}将在{delay}秒后重试(第{retry_count+1}次)")
            else:
                db.execute("UPDATE tasks SET status='failed', error=? WHERE id=?", (error[:200], task_id), commit=True)
                db.execute(
                    "INSERT INTO failed_buffer (original_task_id, task_type, payload, failure_reason, created_at) "
                    "SELECT id, task_type, payload, error, datetime('now') FROM tasks WHERE id=?",
                    (task_id,), commit=True
                )
                logger.warning(f"❌ 任务#{task_id}最终失败，已转入暂存区")
        self._write_op(_do)

    HARD_TIMEOUT = 180  # 壮士断腕：后台任务硬上限180秒

    async def _execute_task(self, task: dict):
        task_id = task["id"]
        task_type = task["task_type"]
        payload = task["payload"]
        retry_count = task["retry_count"]

        self._mark_running(task_id)

        try:
            # 壮士断腕：硬上限保护，防止死锁堆积
            result = await asyncio.wait_for(
                self._dispatch_task(task_type, payload),
                timeout=self.HARD_TIMEOUT
            )
            self._mark_completed(task_id, result)
            logger.info(f"✅ 任务#{task_id}完成: {task_type}")

        except asyncio.TimeoutError:
            # 放弃式智慧：超时不是失败，是学习机会
            logger.warning(f"⏱️ 任务#{task_id}触达硬上限({self.HARD_TIMEOUT}s)，壮士断腕")
            gene_pool.mutate("timeout_tolerance", -0.005, "hard_timeout_surrender")
            gene_pool.mutate("self_doubt_frequency", 0.02, "hard_timeout_surrender")
            # 记录超时经验：此类问题需要前置简化
            self._save_timeout_experience(payload, task_type)
            self._mark_failed(task_id, f"硬上限超时({self.HARD_TIMEOUT}s)", retry_count, 3)

        except Exception as e:
            error = str(e)
            logger.error(f"❌ 任务#{task_id}执行失败: {error[:100]}")
            self._mark_failed(task_id, error, retry_count, 3)

    async def _dispatch_task(self, task_type: str, payload: dict) -> str:
        if task_type == "deep_thinking":
            return await self._do_deep_thinking(payload)
        elif task_type == "ollama_thinking":
            return await self._do_ollama_thinking(payload)
        elif task_type == "gene_solidification":
            return await self._do_gene_solidification(payload)
        elif task_type == "model_review":
            return await self._do_model_review(payload)
        elif task_type == "gene_learning":
            return await self._do_gene_learning(payload)
        elif task_type == "cognitive_metabolism":
            return await self._do_cognitive_metabolism(payload)
        elif task_type == "stress_test":
            return await self._do_stress_test(payload)
        else:
            return f"未知任务类型: {task_type}"

    def _save_timeout_experience(self, payload: dict, task_type: str):
        try:
            query = payload.get("query", "")
            db2 = DatabaseManager.get("data/experience_pool.db")
            db2.execute(
                "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score) VALUES (?, ?, ?, ?, ?)",
                (query, f"[超时经验] {task_type}任务在{self.HARD_TIMEOUT}s内未完成，建议简化prompt", datetime.now().isoformat(), "timeout_wisdom", 30),
                commit=True
            )
        except Exception:
            pass

    async def _do_deep_thinking(self, payload: dict) -> str:
        query = payload.get("query", "")
        context = payload.get("context", {})
        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            throttle = get_gpu_throttle()
            if throttle["delay_seconds"] > 0:
                logger.info(f"深度思考节流: {throttle['message']}，等待{throttle['delay_seconds']}秒")
                await asyncio.sleep(throttle["delay_seconds"])
        except Exception:
            pass
        try:
            from core.metacognitive_executor import MetacognitiveExecutor
            executor = MetacognitiveExecutor()
            exec_result = await executor.execute_with_full_metacognition(user_query=query, context=context)
            result = exec_result.get("final_result", "")
            if result and len(result) > 20 and "我已穷尽" not in result and "🎯 关于" not in result:
                self._save_experience(query, result)
                return f"深度思考完成: {len(result)}字"
            return "深度思考未获得满意结果"
        except Exception as e:
            return f"深度思考失败: {e}"

    async def _do_ollama_thinking(self, payload: dict) -> str:
        query = payload.get("query", "")
        model = payload.get("model", "")
        if not model:
            return "无指定模型"
        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            throttle = get_gpu_throttle()
            if throttle["delay_seconds"] > 0:
                logger.info(f"后台Ollama节流: {throttle['message']}，等待{throttle['delay_seconds']}秒")
                await asyncio.sleep(throttle["delay_seconds"])
        except Exception:
            pass
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: ollama_chat_request(
                        base_url="http://localhost:11434",
                        model=model,
                        prompt=query,
                        timeout=30
                    )
                ),
                timeout=35
            )
            content = result.get("content", "")
            if content and len(content) > 10 and "我已穷尽" not in content:
                self._save_experience(query, content)
                return f"Ollama思考完成: {len(content)}字"
            return "Ollama思考未返回有效结果"
        except Exception as e:
            return f"Ollama思考失败: {e}"

    async def _do_gene_solidification(self, payload: dict) -> str:
        query = payload.get("query", "")
        response_text = payload.get("response", "")
        score = payload.get("score", 0)
        try:
            db2 = DatabaseManager.get("data/knowledge_store.db")
            db2.execute(
                "INSERT INTO knowledge (content, source, type, quality, created_at) VALUES (?, ?, ?, ?, ?)",
                (response_text, "gene_pool", "solidified", int(score), datetime.now().isoformat()),
                commit=True
            )
            db2 = DatabaseManager.get("data/experience_pool.db")
            db2.execute("UPDATE experiences SET quality_score = ? WHERE raw_input LIKE ? AND quality_score < ?", (95, f"%{query[:20]}%", 95), commit=True)
            return f"知识固化完成(评分{score:.0f})"
        except Exception as e:
            return f"知识固化失败: {e}"

    async def _do_model_review(self, payload: dict) -> str:
        """模型评估：用快模型评估回复质量，触发基因微调"""
        query = payload.get("query", "")
        response_text = payload.get("response", "")
        fast_model = self._get_fast_model()
        if not fast_model:
            return "无快模型可用"
        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            throttle = get_gpu_throttle()
            if throttle["delay_seconds"] > 0:
                logger.info(f"模型评估节流: {throttle['message']}，等待{throttle['delay_seconds']}秒")
                await asyncio.sleep(throttle["delay_seconds"])
        except Exception:
            pass
        try:
            review_prompt = f"评估以下问答质量(1-10分)，只输出数字:\n问题:{query}\n回答:{response_text[:300]}"
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: ollama_chat_request(
                    base_url="http://localhost:11434",
                    model=fast_model,
                    prompt=review_prompt,
                    system_prompt="你是质量评估助手，只输出1-10的数字评分。",
                    timeout=60
                )
            )
            content = result.get("content", "")
            if content:
                import re
                match = re.search(r'(\d+)', content)
                if match:
                    score = int(match.group(1))
                    if score >= 8:
                        gene_pool.mutate("confidence_bias", 0.02, "high_review_score")
                        gene_pool.mutate("knowledge_solidify_threshold", -0.5, "high_review_score")
                        self.enqueue("gene_solidification", {"query": query, "response": response_text, "score": score * 12})
                    elif score <= 4:
                        gene_pool.mutate("self_doubt_frequency", 0.03, "low_review_score")
                        gene_pool.mutate("caution_threshold", 0.02, "low_review_score")
                    return f"模型评估: {score}/10"
            return "模型评估未返回有效结果"
        except Exception as e:
            return f"模型评估失败: {e}"

    async def _do_gene_learning(self, payload: dict) -> str:
        """基因学习：从交互结果中微调基因参数"""
        try:
            gene_pool.learn_from_interaction(
                elapsed=payload.get("elapsed", 0),
                success=payload.get("success", True),
                user_feedback=payload.get("user_feedback", 0),
                model_used=payload.get("model_used", "")
            )
            return "基因学习完成"
        except Exception as e:
            return f"基因学习失败: {e}"

    def _get_fast_model(self) -> str:
        try:
            import requests
            tags = requests.get("http://localhost:11434/api/tags", timeout=2)
            models = [m["name"] for m in tags.json().get("models", [])]
            fast_priority = ["qwen2.5-coder:7b", "deepcoder:latest", "qwen2.5:7b", "gemma-4-12B:latest"]
            for m in fast_priority:
                for a in models:
                    if m in a or a.startswith(m.split(":")[0]):
                        return a
            return models[0] if models else ""
        except Exception:
            return ""

    def _save_experience(self, query: str, response: str):
        try:
            db2 = DatabaseManager.get("data/experience_pool.db")
            db2.execute(
                "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score) VALUES (?, ?, ?, ?, ?)",
                (query, response, datetime.now().isoformat(), "background_task", 80),
                commit=True
            )
        except Exception as e:
            logger.debug(f"经验存储失败: {e}")

    async def start_worker(self, interval: float = 5.0):
        if self._running:
            return
        self._running = True
        self._last_idle_check = time.time()
        logger.info("🔄 持久化任务队列worker已启动（认知时差模式）")

        while self._running:
            try:
                tasks = self._get_pending_tasks(limit=3)
                for task in tasks:
                    if task.get("priority", 5) < 5 and not self._is_idle():
                        logger.debug(f"⏳ 任务#{task['id']}等待空闲...")
                        continue
                    await self._execute_task(task)

                # 累积空闲信用：长时间空闲触发碎片整理
                idle_seconds = time.time() - self._last_user_interaction
                if idle_seconds > 300 and (time.time() - self._last_idle_check) > 300:
                    self._last_idle_check = time.time()
                    logger.info("💤 累积空闲>5分钟，触发碎片整理...")
                    self._do_idle_consolidation()

                if not tasks:
                    await asyncio.sleep(interval)
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"任务队列worker异常: {e}")
                await asyncio.sleep(5)

    def _do_idle_consolidation(self):
        try:
            db2 = DatabaseManager.get("data/experience_pool.db")
            row = db2.query_one("SELECT COUNT(*) FROM experiences WHERE quality_score >= 80")
            high_quality = row[0]
            row = db2.query_one("SELECT COUNT(*) FROM experiences WHERE intent_type = 'timeout_wisdom'")
            timeout_wisdom = row[0]
            logger.info(f"💤 碎片整理: 高质量经验{high_quality}条, 超时经验{timeout_wisdom}条")
            if timeout_wisdom > 3:
                gene_pool.mutate("depth_preference", -0.01, "idle_consolidation_too_many_timeouts")
        except Exception:
            pass

    def stop_worker(self):
        self._running = False
        logger.info("⏹️ 持久化任务队列worker已停止")

    def get_stats(self) -> dict:
        try:
            db = self._connect()
            rows = db.query("SELECT status, COUNT(*) FROM tasks GROUP BY status")
            status_counts = {r[0]: r[1] for r in rows}
            row = db.query_one("SELECT COUNT(*) FROM failed_buffer WHERE recovered=0")
            failed_buffer_count = row[0]
            return {
                "pending": status_counts.get("pending", 0),
                "running": status_counts.get("running", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "failed_buffer": failed_buffer_count,
                "is_idle": self._is_idle(),
                "idle_seconds": round(time.time() - self._last_user_interaction, 1)
            }
        except Exception:
            return {"error": "无法获取统计"}

    async def _do_cognitive_metabolism(self, payload: dict) -> str:
        """
        认知代谢：定期清理低价值缓存、压缩陈旧经验，释放存储资源

        就像生物的代谢：只同化不异化，最终会中毒（内存溢出、知识陈旧）
        - 同化：吸收新知识
        - 异化：清理低价值碎片，提升高频经验
        """
        stats = {"exp_purged": 0, "exp_promoted": 0, "know_purged": 0}

        try:
            db2 = DatabaseManager.get("data/experience_pool.db")
            row = db2.query_one("SELECT COUNT(*) FROM experiences WHERE quality_score < 50 AND timestamp < datetime('now', '-30 days')")
            purge_count = row[0]
            if purge_count > 0:
                db2.execute("DELETE FROM experiences WHERE quality_score < 50 AND timestamp < datetime('now', '-30 days')", commit=True)
                stats["exp_purged"] = purge_count
            cur = db2.execute("UPDATE experiences SET quality_score = MIN(quality_score + 5, 95) WHERE quality_score >= 70 AND quality_score < 95", commit=True)
            stats["exp_promoted"] = cur.rowcount
        except Exception as e:
            logger.debug(f"经验池代谢失败: {e}")

        try:
            db2 = DatabaseManager.get("data/knowledge_store.db")
            row = db2.query_one("SELECT COUNT(*) FROM knowledge WHERE quality < 30 AND created_at < datetime('now', '-30 days')")
            purge_count = row[0]
            if purge_count > 0:
                db2.execute("DELETE FROM knowledge WHERE quality < 30 AND created_at < datetime('now', '-30 days')", commit=True)
                stats["know_purged"] = purge_count
        except Exception as e:
            logger.debug(f"知识库代谢失败: {e}")

        result = f"认知代谢完成: 经验池清除{stats['exp_purged']}条/提升{stats['exp_promoted']}条, 知识库清除{stats['know_purged']}条"
        logger.info(f"🧹 {result}")
        return result

    async def _do_stress_test(self, payload: dict) -> str:
        """
        进化压力测试：随机环境扰动注入器

        定期制造小故障（模拟Ollama超时、网络中断），观察系统恢复能力
        就像自然界的"火生态"——定期的轻微火灾反而促进森林更新
        """
        import random
        tests = []
        gene_snapshot = gene_pool.get_all()

        # 测试1：模拟Ollama不可用
        try:
            import requests
            start = time.time()
            try:
                requests.get("http://localhost:11434/api/tags", timeout=2)
                tests.append(("Ollama可用性", True, f"{time.time()-start:.1f}s"))
            except Exception:
                tests.append(("Ollama可用性", False, "不可用"))
        except Exception:
            tests.append(("Ollama可用性", False, "测试失败"))

        # 测试2：模拟外部API不可用
        try:
            from pathlib import Path
            config_file = Path("config/external_api.json")
            if config_file.exists():
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                has_key = bool(config.get("deepseek_api_key") or config.get("openai_api_key"))
                tests.append(("外部API配置", has_key, "已配置" if has_key else "未配置"))
            else:
                tests.append(("外部API配置", False, "无配置文件"))
        except Exception:
            tests.append(("外部API配置", False, "检测失败"))

        # 测试3：基因安全基线检查
        violations = []
        for key, (min_val, max_val) in GENE_SAFETY_BOUNDS.items():
            current = gene_pool.get(key)
            if current < min_val or current > max_val:
                violations.append(f"{key}={current:.3f} 超出[{min_val},{max_val}]")
        tests.append(("基因安全基线", len(violations) == 0, f"{len(violations)}个违规" if violations else "全部合规"))

        # 测试4：数据库完整性
        db_ok = True
        for db_name in ["experience_pool.db", "knowledge_store.db", "gene_pool.db", "task_queue.db"]:
            try:
                db2 = DatabaseManager.get(f"data/{db_name}")
                db2.query_one("SELECT COUNT(*) FROM sqlite_master")
            except Exception:
                db_ok = False
                tests.append(("数据库完整性", False, f"{db_name}损坏"))
                break
        if db_ok:
            tests.append(("数据库完整性", True, "全部正常"))

        passed = sum(1 for t in tests if t[1])
        total = len(tests)
        result = f"压力测试: {passed}/{total}通过; " + "; ".join([f"{t[0]}={'✅' if t[1] else '❌'}{t[2]}" for t in tests])
        logger.info(f"🔥 {result}")
        return result


task_queue = PersistentTaskQueue()
