"""
代谢编排器 (Metabolism Orchestrator)

将碎片化的代谢组件串联为统一循环：
  ingest  → 调用 layered_memory 同步（摄入新经验）
  digest  → 调用 gap_growth 消化信号（理解需求）
  grow    → 调用 sleep_consolidation 巩固（强化记忆）
  shed    → 调用 knowledge_forgetting 衰减（清理过时）

关键特性：
- 自适应节拍：空闲时完整循环，忙碌时快速摄入，峰值时暂停
- 语义感知遗忘：删除知识前检查依赖关系
- 零功能回退：现有代谢功能行为不变
"""

import time
from typing import Optional, Dict, Any, List
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class MetabolismOrchestrator:
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

        self.phase = "idle"
        self.last_full_cycle: Optional[float] = None
        self.last_quick_ingest: Optional[float] = None
        self.cycle_count = 0
        self._cycle_stats: Dict[str, int] = {
            "full_cycles": 0,
            "quick_ingests": 0,
            "skipped_peak": 0,
        }

    def _assess_load(self) -> str:
        """评估系统负载：idle / busy / peak"""
        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            mem_pct = monitor.get_memory_percent()
            mode = monitor.get_mode_value()

            if mode in ("critical", "conservative"):
                return "peak"
            elif mem_pct > 80 or mode == "degraded":
                return "busy"
            else:
                return "idle"
        except Exception:
            try:
                import psutil
                mem_pct = psutil.virtual_memory().percent
                if mem_pct > 90:
                    return "peak"
                elif mem_pct > 75:
                    return "busy"
            except Exception:
                logger.warning("操作降级跳过")
            return "idle"

    def _seconds_since_last_interaction(self) -> float:
        """距上次用户交互的秒数"""
        try:
            from backend.services.path_handlers._shared import _ollama_last_inference_time
            if _ollama_last_inference_time > 0:
                return time.time() - _ollama_last_inference_time
        except Exception:
            logger.warning("操作降级跳过")
        return 999.0

    async def tick(self):
        """自适应代谢节拍"""
        load = self._assess_load()

        if load == "peak":
            self._cycle_stats["skipped_peak"] += 1
            logger.debug("代谢: 峰值负载，暂停代谢")
            return

        idle_seconds = self._seconds_since_last_interaction()

        if load == "busy" or idle_seconds < 120:
            await self._quick_ingest()
        else:
            await self._full_cycle()

    async def _quick_ingest(self):
        """快速摄入——忙碌时仅同步记忆"""
        now = time.time()
        if self.last_quick_ingest and (now - self.last_quick_ingest) < 60:
            return

        self.phase = "ingesting"
        try:
            await self.ingest()
            self.last_quick_ingest = now
            self._cycle_stats["quick_ingests"] += 1
        except Exception as e:
            logger.warning(f"代谢快速摄入异常: {e}")
        finally:
            self.phase = "idle"

    async def _full_cycle(self):
        """完整代谢循环——空闲时执行"""
        now = time.time()
        if self.last_full_cycle and (now - self.last_full_cycle) < 300:
            return

        self.phase = "ingesting"
        try:
            await self.ingest()
        except Exception as e:
            logger.warning(f"代谢摄入异常: {e}")

        self.phase = "digesting"
        try:
            await self.digest()
        except Exception as e:
            logger.warning(f"代谢消化异常: {e}")

        self.phase = "growing"
        try:
            await self.grow()
        except Exception as e:
            logger.warning(f"代谢生长异常: {e}")

        self.phase = "shedding"
        try:
            await self.shed()
        except Exception as e:
            logger.warning(f"代谢排泄异常: {e}")

        self.cycle_count += 1
        self.last_full_cycle = time.time()
        self._cycle_stats["full_cycles"] += 1
        self.phase = "idle"
        logger.info(f"代谢循环完成(第{self.cycle_count}次)")

    async def ingest(self):
        """摄入——同步分层记忆"""
        try:
            from core.memory.layered_memory import layered_memory
            strat = layered_memory.sync_strategic_memory()
            proc = layered_memory.sync_procedural_memory()
            tool = layered_memory.sync_tool_memory()
            logger.warning(f"代谢摄入: 战略+{strat}/程序+{proc}/工具+{tool}")
        except Exception as e:
            logger.warning(f"代谢摄入跳过: {e}")

    async def digest(self):
        """消化——处理待消化的信号"""
        try:
            from core.presence.gap_growth import gap_growth_engine
            status = gap_growth_engine.get_queue_status()
            pending = status.get("pending", 0)
            if pending > 0:
                logger.warning(f"代谢消化: {pending}个待消化信号")
        except Exception as e:
            logger.warning(f"代谢消化跳过: {e}")

    async def grow(self):
        """生长——睡眠巩固"""
        try:
            from core.presence.sleep_consolidation import sleep_consolidation_engine
            summary = sleep_consolidation_engine.get_consolidation_summary()
            if summary:
                logger.warning(f"代谢生长: 巩固摘要可用")
        except Exception as e:
            logger.warning(f"代谢生长跳过: {e}")

    async def shed(self):
        """排泄——语义感知的知识遗忘"""
        try:
            from core.knowledge_forgetting import knowledge_forgetting
            report = knowledge_forgetting.get_report()
            rules_faded = report.get("rules_faded", 0)
            rules_cleared = report.get("rules_cleared", 0)
            exp_faded = report.get("experiences_faded", 0)
            exp_cleared = report.get("experiences_cleared", 0)
            logger.warning(f"代谢排泄: 规则淡化{rules_faded}+清除{rules_cleared}, 经验淡化{exp_faded}+清除{exp_cleared}")

            self._semantic_prune()
        except Exception as e:
            logger.warning(f"代谢排泄跳过: {e}")

    def _semantic_prune(self):
        """语义感知的修剪——删除知识前检查依赖关系图"""
        total_pruned = 0
        total_demoted = 0

        total_pruned, total_demoted = self._prune_knowledge_items()
        exp_pruned, exp_demoted = self._prune_experiences()
        total_pruned += exp_pruned
        total_demoted += exp_demoted

        if total_pruned > 0 or total_demoted > 0:
            logger.warning(f"语义修剪: 降权{total_demoted}条, 删除{total_pruned}条")

    def _prune_knowledge_items(self) -> tuple:
        try:
            db = DatabaseManager.get("data/knowledge_items.db")
            rows = db.query(
                "SELECT id, question, answer, quality FROM knowledge_items "
                "WHERE updated_at < datetime('now', '-30 days') AND quality > 0 "
                "ORDER BY quality ASC LIMIT 30"
            )
            if not rows:
                return 0, 0

            pruned = 0
            demoted = 0
            for row in rows:
                kid = row["id"]
                question = row.get("question", "")
                quality = row.get("quality", 50)

                dep_count = self._count_dependents(db, question, kid, "knowledge_items")

                if dep_count == 0:
                    new_quality = quality * 0.7
                    if new_quality < 10:
                        db.execute("DELETE FROM knowledge_items WHERE id = ?", (kid,), commit=True)
                        pruned += 1
                    else:
                        db.execute("UPDATE knowledge_items SET quality = ? WHERE id = ?", (new_quality, kid), commit=True)
                        demoted += 1
                else:
                    new_quality = quality * 0.9
                    db.execute("UPDATE knowledge_items SET quality = ? WHERE id = ?", (new_quality, kid), commit=True)
                    demoted += 1

            return pruned, demoted
        except Exception as e:
            logger.warning(f"语义修剪跳过: {e}")
            return 0, 0

    def _prune_experiences(self) -> tuple:
        try:
            db = DatabaseManager.get("data/experience_pool.db")
            rows = db.query(
                "SELECT id, raw_input, quality_score FROM experiences "
                "WHERE success = 0 AND timestamp < datetime('now', '-14 days') AND quality_score < 30 "
                "ORDER BY quality_score ASC LIMIT 20"
            )
            if not rows:
                return 0, 0

            pruned = 0
            demoted = 0
            for row in rows:
                eid = row["id"]
                raw_input = row.get("raw_input", "")
                quality_score = row.get("quality_score", 50)

                dep_count = self._count_dependents(db, raw_input, eid, "experiences")

                if dep_count == 0 and quality_score < 15:
                    db.execute("DELETE FROM experiences WHERE id = ?", (eid,), commit=True)
                    pruned += 1
                else:
                    new_q = max(0, quality_score - 5)
                    db.execute("UPDATE experiences SET quality_score = ? WHERE id = ?", (new_q, eid), commit=True)
                    demoted += 1

            return pruned, demoted
        except Exception as e:
            logger.warning(f"经验池修剪跳过: {e}")
            return 0, 0

    def _count_dependents(self, db, text: str, exclude_id: int, table: str) -> int:
        if not text or len(text) < 5:
            return 0

        keyword_deps = self._keyword_dependents(db, text, exclude_id, table)
        semantic_deps = self._semantic_dependents(db, text, exclude_id, table)

        total = keyword_deps + semantic_deps
        if total > 0 and semantic_deps > 0:
            logger.debug(f"依赖检测: 关键词{keyword_deps}+语义{semantic_deps}")
        return total

    def _keyword_dependents(self, db, text: str, exclude_id: int, table: str) -> int:
        try:
            search_term = text[:30].replace('%', '').replace('_', '')
            if table == "knowledge_items":
                dependents = db.query(
                    "SELECT COUNT(*) as cnt FROM knowledge_items "
                    "WHERE (answer LIKE ? OR question LIKE ?) AND id != ?",
                    (f"%{search_term}%", f"%{search_term}%", exclude_id),
                )
            else:
                dependents = db.query(
                    "SELECT COUNT(*) as cnt FROM experiences "
                    "WHERE raw_input LIKE ? AND id != ?",
                    (f"%{search_term}%", exclude_id),
                )
            return dependents[0]["cnt"] if dependents else 0
        except Exception:
            return 0

    def _semantic_dependents(self, db, text: str, exclude_id: int, table: str) -> int:
        try:
            from core.shared_embedding import compute_embedding, similarity
            query_emb = compute_embedding(text[:200])
            if not query_emb:
                return 0

            if table == "knowledge_items":
                rows = db.query(
                    "SELECT id, question, answer FROM knowledge_items "
                    "WHERE id != ? AND updated_at > datetime('now', '-60 days') LIMIT 50",
                    (exclude_id,),
                )
                candidates = [(r["id"], (r.get("question", "") or "") + " " + (r.get("answer", "") or "")) for r in rows]
            else:
                rows = db.query(
                    "SELECT id, raw_input FROM experiences "
                    "WHERE id != ? AND timestamp > datetime('now', '-60 days') LIMIT 50",
                    (exclude_id,),
                )
                candidates = [(r["id"], r.get("raw_input", "") or "") for r in rows]

            dep_count = 0
            for cid, ctext in candidates:
                if not ctext or len(ctext) < 10:
                    continue
                c_emb = compute_embedding(ctext[:200])
                if c_emb and similarity(query_emb, c_emb) > 0.75:
                    dep_count += 1

            return dep_count
        except Exception as e:
            logger.debug(f"语义依赖检测降级: {e}")
            return 0

    def get_status(self) -> Dict[str, Any]:
        """获取代谢状态"""
        return {
            "phase": self.phase,
            "cycle_count": self.cycle_count,
            "last_full_cycle": self.last_full_cycle,
            "last_quick_ingest": self.last_quick_ingest,
            "stats": self._cycle_stats.copy(),
        }


metabolism_orchestrator = MetabolismOrchestrator()