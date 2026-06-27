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
import sqlite3
import uuid

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
        
        # 初始化日志数据库
        self._init_log_db()
        
        logger.info("🔄 反思管道已初始化")
        logger.info(f"  - 日志库: {self.log_db_path}")
        logger.info(f"  - 微调队列: {self.jsonl_dir}")
        logger.info(f"  - 归纳超时: {self.induction_timeout}秒")
        
    def _init_log_db(self):
        """初始化日志数据库"""
        Path(self.log_db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.log_db_path) as conn:
            conn.execute('''
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
            conn.commit()
    
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
            
            # 2. 触发元归纳（异步，有超时控制）
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
            
            # 3. 生成JSONL样本（如果置信度低于阈值或重要）
            if self.enable_jsonl and context["confidence"] < self.min_confidence:
                await self._append_jsonl(context)
                actions_taken.append("jsonl_sample")
                logger.debug(f"✓ JSONL样本生成: {reflection_id}")
            
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
        
        return enriched
    
    async def _write_campfire_log(self, context: Dict[str, Any]) -> None:
        """写入营火日志（异步写入）"""
        def _write():
            with sqlite3.connect(self.log_db_path) as conn:
                conn.execute(
                    """INSERT INTO reflection_log 
                       (id, timestamp, query, plan, tool_calls, final_answer, 
                        confidence, model_used, user_id, session_id, duration_ms, extra_metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
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
                    )
                )
                conn.commit()
        
        # 在线程池中执行（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write)

    async def _trigger_induction(self, context: Dict[str, Any]) -> None:
        """触发元归纳"""
        try:
            # 尝试多种导入路径
            run_induction = None
            
            try:
                from meta.induction import run_induction as ri
                run_induction = ri
                logger.debug("✅ 元归纳模块导入成功 (meta.induction)")
            except ImportError:
                try:
                    from core.meta.induction import run_induction as ri
                    run_induction = ri
                    logger.debug("✅ 元归纳模块导入成功 (core.meta.induction)")
                except ImportError:
                    logger.warning("元归纳模块未找到，跳过触发")
                    return
            
            # 构造经验条目
            experience = {
                "query": context["query"],
                "plan": context.get("plan", {}),
                "final_answer": context["final_answer"],
                "confidence": context["confidence"],
                "tool_used": bool(context.get("tool_calls")),
                "success": context["confidence"] > 0.7,
                "timestamp": context["timestamp"]
            }
            
            # 执行归纳（同步函数，在线程池中运行）
            loop = asyncio.get_event_loop()
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
            with sqlite3.connect(self.log_db_path) as conn:
                log_count = conn.execute(
                    "SELECT COUNT(*) FROM reflection_log"
                ).fetchone()[0]
            
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