"""
反思管道（ReflectionPipeline）- 系统闭环的关键传动轴

跨学科理论基础：
- 认知科学：经验回放（Experience Replay）
- 控制论：负反馈回路（Negative Feedback Loop）
- 系统论：信息流闭环（Information Flow Closure）

职责：
1. 结构化存储到 Campfire 日志
2. 异步触发元归纳
3. 生成微调样本（JSONL）
"""
import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid
from infrastructure.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ReflectionPipeline:
    """
    反思管道：将每次对话执行转化为学习信号
    
    架构：
    [Chat API 出口] → ReflectionPipeline.process()
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
         [Campfire Log]  [Meta Induction]  [JSONL微调队列]
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        config 示例:
        {
            "log_db_path": "logs/campfire_log.db",
            "jsonl_output_dir": "data/finetune/queue",
            "enable_induction": True,
            "enable_jsonl": True,
            "induction_timeout_seconds": 10,
            "min_confidence_threshold": 0.6,
        }
        """
        config = config or {}
        self.log_db_path = config.get("log_db_path", "logs/campfire_log.db")
        self.jsonl_dir = Path(config.get("jsonl_output_dir", "data/finetune/queue"))
        self.jsonl_dir.mkdir(parents=True, exist_ok=True)
        self.enable_induction = config.get("enable_induction", True)
        self.enable_jsonl = config.get("enable_jsonl", True)
        self.induction_timeout = config.get("induction_timeout_seconds", 10)
        self.min_confidence = config.get("min_confidence_threshold", 0.6)
        
        self.success_threshold = config.get("success_threshold", 0.6)
        self.weights = config.get("success_weights", {
            "confidence": 0.5,
            "tool_execution": 0.3,
            "plan_execution": 0.2
        })
        self.jsonl_sample_strategy = config.get("jsonl_sample_strategy", "low_confidence")
        
        # 初始化日志数据库
        self._init_log_db()
        
        logger.info("🔄 反思管道已初始化")
        logger.info(f"  - 日志库: {self.log_db_path}")
        logger.info(f"  - 微调队列: {self.jsonl_dir}")
        logger.info(f"  - 归纳超时: {self.induction_timeout}秒")
        
    def _init_log_db(self):
        """初始化日志数据库（含字段迁移）"""
        Path(self.log_db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager.get(self.log_db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS reflection_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                query TEXT,
                plan TEXT,
                tool_calls TEXT,
                final_answer TEXT,
                confidence REAL,
                model_used TEXT,
                user_id TEXT,
                session_id TEXT,
                duration_ms INTEGER,
                extra_metadata TEXT
            )
        ''')
        
        columns = [row[1] for row in db.query("PRAGMA table_info(reflection_log)")]
        
        required_columns = {
            "consolidated": "INTEGER DEFAULT 0",
            "consolidated_at": "TEXT",
            "rule_used": "INTEGER",
            "is_canary_sample": "INTEGER DEFAULT 0",
            "success": "INTEGER DEFAULT 0"
        }
        
        for col, col_type in required_columns.items():
            if col not in columns:
                try:
                    db.execute(f"ALTER TABLE reflection_log ADD COLUMN {col} {col_type}", commit=True)
                    logger.info(f"  ✓ 添加字段: {col}")
                except Exception as e:
                    logger.warning(f"  ⚠ 添加字段 {col} 失败: {e}")
        
        db.execute('SELECT 1', commit=True)
    
    async def process(self, execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理一次执行上下文，所有操作非阻塞且容错
        
        execution_context 应包含：
        {
            "query": str,
            "plan": dict,            # 执行计划
            "tool_calls": list,      # 工具调用详情
            "intermediate_results": list,
            "final_answer": str,
            "confidence": float,
            "model_used": str,
            "user_id": str (可选),
            "session_id": str (可选),
            "duration_ms": int,
        }
        
        返回：
        {
            "success": bool,
            "reflection_id": str,
            "actions_taken": list
        }
        """
        # 增强上下文：确保必要字段
        context = self._enrich_context(execution_context)
        reflection_id = context["reflection_id"]
        
        actions_taken = []
        
        try:
            # 1. 写入营火日志（同步，快速）
            await self._write_campfire_log(context)
            actions_taken.append("campfire_log")
            logger.debug(f"✓ 反思日志写入: {reflection_id}")
            
            if self.enable_induction:
                try:
                    await asyncio.wait_for(
                        self._trigger_induction(context),
                        timeout=self.induction_timeout
                    )
                    actions_taken.append("meta_induction")
                    logger.debug(f"✓ 元归纳触发: {reflection_id}")
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ 元归纳超时 ({self.induction_timeout}秒)")
                except Exception as e:
                    logger.warning(f"元归纳失败: {e}")
            
            if self.enable_jsonl and self._should_sample_jsonl(context):
                await self._append_jsonl(context)
                actions_taken.append("jsonl_sample")
                logger.debug(f"✓ JSONL样本生成: {reflection_id}")
            
            # P1-7: 反思教训回流到spirit_lessons.db
            try:
                await self._write_lesson_to_spirit(context)
                actions_taken.append("spirit_lesson")
            except Exception as e:
                logger.debug(f"反思教训写入跳过: {e}")
            
            return {
                "success": True,
                "reflection_id": reflection_id,
                "actions_taken": actions_taken
            }
            
        except Exception as e:
            logger.error(f"❌ 反思管道处理失败: {e}", exc_info=True)
            return {
                "success": False,
                "reflection_id": reflection_id,
                "error": str(e),
                "actions_taken": actions_taken
            }
    
    def _should_sample_jsonl(self, context: Dict[str, Any]) -> bool:
        """判断是否应采样生成JSONL样本"""
        import random
        
        strategy = self.jsonl_sample_strategy
        success = context.get("success", False)
        confidence = context.get("confidence", 0.5)
        
        if strategy == "low_confidence":
            return confidence < self.min_confidence
        elif strategy == "failures_only":
            return not success
        elif strategy == "balanced":
            if not success:
                return True
            else:
                return random.random() < 0.2
        elif strategy == "all":
            return True
        else:
            return confidence < self.min_confidence
    
    def _calculate_success(self, context: Dict[str, Any]) -> bool:
        """
        多维度成功率计算 - 控制论负反馈信号
        
        维度：
        1. 置信度（权重可配置）
        2. 工具执行（权重可配置）
        3. 计划执行（权重可配置）
        """
        confidence = context.get("confidence", 0.5)
        tool_calls = context.get("tool_calls", [])
        plan = context.get("plan", {})
        execution_results = context.get("execution_results", [])
        
        w_conf = self.weights.get("confidence", 0.5)
        w_tool = self.weights.get("tool_execution", 0.3)
        w_plan = self.weights.get("plan_execution", 0.2)
        
        if confidence > 0.7:
            confidence_score = 1.0
        elif confidence > 0.5:
            confidence_score = 0.5
        else:
            confidence_score = 0.0
        
        if tool_calls:
            tool_success = any(tc.get("status") == "success" for tc in tool_calls)
            tool_score = 1.0 if tool_success else 0.0
        elif execution_results:
            tool_success = any(r.get("status") == "success" for r in execution_results)
            tool_score = 1.0 if tool_success else 0.0
        else:
            tool_score = 0.5
        
        tasks = plan.get("tasks", []) if isinstance(plan, dict) else []
        if tasks:
            task_success = any(t.get("status") == "success" for t in tasks)
            plan_score = 1.0 if task_success else 0.0
        elif execution_results:
            plan_score = 1.0 if len(execution_results) > 0 else 0.0
        else:
            plan_score = 0.5
        
        total_score = w_conf * confidence_score + w_tool * tool_score + w_plan * plan_score
        
        return total_score > self.success_threshold
    
    async def _write_lesson_to_spirit(self, context: Dict[str, Any]):
        """P1-7: 将反思教训写入spirit_lessons.db，供下次规划读取"""
        query = context.get("query", "")
        confidence = context.get("confidence", 0.5)
        success = context.get("success", False)
        lessons = []
        
        if not success:
            lessons.append({
                "lesson_type": "execution_failure",
                "lesson_text": f"查询'{query[:30]}'执行失败，置信度{confidence:.0%}",
                "severity": 3,
                "context": query[:50]
            })
        elif confidence < 0.4:
            lessons.append({
                "lesson_type": "low_confidence",
                "lesson_text": f"查询'{query[:30]}'置信度低({confidence:.0%})，需加强验证",
                "severity": 2,
                "context": query[:50]
            })
        
        tool_calls = context.get("tool_calls", [])
        for tc in tool_calls:
            if not tc.get("success", True):
                lessons.append({
                    "lesson_type": "tool_failure",
                    "lesson_text": f"工具{tc.get('tool','?')}执行失败: {tc.get('error','未知')[:50]}",
                    "severity": 2,
                    "context": query[:50]
                })
        
        if not lessons:
            return
        
        try:
            db = DatabaseManager.get("data/spirit_lessons.db")
            db.executescript('''CREATE TABLE IF NOT EXISTS spirit_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_type TEXT,
                lesson_text TEXT,
                severity INTEGER DEFAULT 1,
                context TEXT,
                created_at TEXT
            )''')
            now = datetime.now().isoformat()
            for lesson in lessons:
                db.execute(
                    "INSERT INTO spirit_lessons (lesson_type, lesson_text, severity, context, created_at) VALUES (?,?,?,?,?)",
                    (lesson["lesson_type"], lesson["lesson_text"], lesson["severity"], lesson["context"], now),
                    commit=True
                )
        except Exception as e:
            logger.debug(f"教训写入失败: {e}")
    
    def _enrich_context(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """补充元数据，生成唯一ID和时间戳"""
        enriched = raw.copy()
        enriched.setdefault("reflection_id", str(uuid.uuid4()))
        enriched.setdefault("timestamp", datetime.utcnow().isoformat())
        enriched.setdefault("confidence", 0.5)
        enriched.setdefault("query", "")
        enriched.setdefault("final_answer", "")
        enriched.setdefault("model_used", "unknown")
        enriched.setdefault("duration_ms", 0)
        
        # 确保工具调用列表可序列化
        if "tool_calls" in enriched:
            enriched["tool_calls"] = [
                {k: str(v) for k, v in tc.items()} 
                for tc in enriched["tool_calls"]
            ]
        else:
            enriched["tool_calls"] = []
        
        # 使用多维度success计算
        if "success" not in enriched:
            enriched["success"] = self._calculate_success(enriched)
        
        return enriched
    
    async def _write_campfire_log(self, context: Dict[str, Any]) -> None:
        """写入营火日志（异步写入）"""
        def _write():
            db = DatabaseManager.get(self.log_db_path)
            columns = [row[1] for row in db.query("PRAGMA table_info(reflection_log)")]
            
            base_sql = """INSERT INTO reflection_log 
               (id, timestamp, query, plan, tool_calls, final_answer, 
                confidence, model_used, user_id, session_id, duration_ms, extra_metadata"""
            values = [
                context["reflection_id"],
                context["timestamp"],
                context.get("query", ""),
                json.dumps(context.get("plan", {}), ensure_ascii=False),
                json.dumps(context.get("tool_calls", []), ensure_ascii=False),
                context.get("final_answer", ""),
                context.get("confidence", 0.0),
                context.get("model_used", "unknown"),
                context.get("user_id", ""),
                context.get("session_id", ""),
                context.get("duration_ms", 0),
                json.dumps(context.get("extra", {}), ensure_ascii=False)
            ]
            
            if "success" in columns:
                base_sql += ", success"
                values.append(1 if context.get("success", False) else 0)
            
            base_sql += ") VALUES (" + ",".join(["?"] * len(values)) + ")"
            
            db.execute(base_sql, tuple(values), commit=True)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write)

    async def _trigger_induction(self, context: Dict[str, Any]) -> None:
        """触发元归纳"""
        try:
            run_induction = None
            
            try:
                from meta.induction import run_induction as ri
                run_induction = ri
                logger.debug("✅ 元归纳模块导入成功 (meta.induction)")
            except ImportError:
                logger.warning("元归纳模块未找到，跳过触发")
                return
            
            experience = {
                "query": context["query"],
                "plan": context.get("plan", {}),
                "final_answer": context.get("final_answer", ""),
                "confidence": context.get("confidence", 0.5),
                "tool_used": bool(context.get("tool_calls")),
                "success": context.get("success", False),
                "timestamp": context.get("timestamp", ""),
                "reflection_id": context.get("reflection_id", "")
            }
            
            loop = asyncio.get_event_loop()
            
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: run_induction(experience=experience, days=1)
                )
            except TypeError:
                result = await loop.run_in_executor(
                    None,
                    lambda: run_induction(days=1)
                )
            
            logger.debug(f"✅ 元归纳执行完成: {result}")
            
        except Exception as e:
            logger.error(f"触发归纳时出错: {e}")

    async def _append_jsonl(self, context: Dict[str, Any]) -> None:
        """将上下文转换为微调样本追加到JSONL文件"""
        try:
            # 构造标准对话格式（指令/输出）
            instruction = context.get("query", "")
            
            # 系统应该输出包含推理过程 + 最终答案
            output_parts = []
            if "plan" in context and context["plan"]:
                output_parts.append(f"【思考计划】\n{json.dumps(context['plan'], ensure_ascii=False, indent=2)}")
            if "tool_calls" in context and context["tool_calls"]:
                output_parts.append(f"【工具调用】\n{json.dumps(context['tool_calls'], ensure_ascii=False, indent=2)}")
            output_parts.append(f"【最终回答】\n{context.get('final_answer', '')}")
            
            output = "\n\n".join(output_parts)
            
            sample = {
                "instruction": instruction,
                "output": output,
                "metadata": {
                    "confidence": context["confidence"],
                    "model": context.get("model_used"),
                    "timestamp": context["timestamp"],
                    "reflection_id": context["reflection_id"]
                }
            }
            
            # 按日期分文件
            date_str = datetime.utcnow().strftime("%Y%m%d")
            file_path = self.jsonl_dir / f"reflection_samples_{date_str}.jsonl"
            
            # 异步写入
            def _write_jsonl():
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _write_jsonl)
            
        except Exception as e:
            logger.error(f"追加JSONL失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取反思管道统计信息"""
        try:
            # 统计日志数量
            db = DatabaseManager.get(self.log_db_path)
            log_count = db.query_one("SELECT COUNT(*) FROM reflection_log")[0]
            
            # 统计JSONL样本数量
            jsonl_count = 0
            for jsonl_file in self.jsonl_dir.glob("*.jsonl"):
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    jsonl_count += sum(1 for _ in f)
            
            return {
                "log_count": log_count,
                "jsonl_count": jsonl_count,
                "jsonl_dir": str(self.jsonl_dir),
                "log_db": self.log_db_path,
                "induction_enabled": self.enable_induction,
                "jsonl_enabled": self.enable_jsonl
            }
        except Exception as e:
            return {"error": str(e)}


# 全局实例
_pipeline = None

def get_reflection_pipeline(config: Dict[str, Any] = None) -> ReflectionPipeline:
    """获取反思管道实例"""
    global _pipeline
    if _pipeline is None:
        _pipeline = ReflectionPipeline(config)
    return _pipeline
