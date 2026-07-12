"""
分层记忆系统 (P1-6 — MUSE启发)

三层记忆架构：
- Strategic Memory（战略记忆）：从真谛沉淀+轨迹进化中提取"困境-策略"对，日级更新
- Procedural Memory（程序记忆）：从技能涌现+规则库中提取SOP，小时级更新
- Tool Memory（工具记忆）：从工具调用记录中提取"肌肉记忆"，分钟级更新

与现有系统的关系：
- 真谛库(truths.db) → Strategic Memory 的核心来源
- 轨迹进化(trajectory_evolution.db) → Strategic Memory 的策略来源
- 学习规则(learning_rules.db) → Procedural Memory 的SOP来源
- 工具执行统计(tool_cache.db) → Tool Memory 的来源
- 经验池(experience_pool.db) → 三层记忆的共享底座
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class LayeredMemory:
    _instance = None

    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db_path = db_path or "data/layered_memory.db"
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        db = DatabaseManager.get(self._db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS strategic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dilemma TEXT NOT NULL,
                strategy TEXT NOT NULL,
                source TEXT,
                domains TEXT,
                evidence_count INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.5,
                importance REAL DEFAULT 0.5,
                last_updated TEXT,
                created_at TEXT,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS procedural_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sop_name TEXT NOT NULL,
                trigger_condition TEXT,
                steps TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 0.5,
                apply_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_updated TEXT,
                created_at TEXT,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS tool_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                query_pattern TEXT,
                best_params TEXT,
                avg_quality REAL DEFAULT 0,
                avg_duration_ms REAL DEFAULT 0,
                call_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_strategic_memory_updated ON strategic_memory(last_updated);
            CREATE INDEX IF NOT EXISTS idx_procedural_memory_updated ON procedural_memory(last_updated);
            CREATE INDEX IF NOT EXISTS idx_tool_memory_updated ON tool_memory(last_used)
        ''')

    def sync_strategic_memory(self) -> int:
        now = datetime.now().isoformat()
        count = 0

        try:
            db1 = DatabaseManager.get("data/truths.db")
            rows = db1.query(
                "SELECT statement, domain, evidence_count, level FROM truths WHERE level >= 3"
            )
            db2 = DatabaseManager.get(self._db_path)
            for statement, domain, evidence, level in rows:
                existing = db2.query_one(
                    "SELECT id FROM strategic_memory WHERE strategy = ?", (statement,)
                )
                if existing:
                    db2.execute(
                        "UPDATE strategic_memory SET evidence_count=?, importance=?, last_updated=? WHERE id=?",
                        (evidence or 1, min(1.0, (evidence or 1) / 5.0), now, existing[0]), commit=True
                    )
                else:
                    db2.execute(
                        "INSERT INTO strategic_memory (dilemma, strategy, source, domains, evidence_count, importance, last_updated, created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (f"如何处理{domain or '通用'}问题", statement, f"truth_L{level}",
                         json.dumps([domain] if domain else []), evidence or 1,
                         min(1.0, (evidence or 1) / 5.0), now, now), commit=True
                    )
                count += 1
        except Exception as e:
            logger.warning(f"战略记忆同步(真谛)跳过: {e}")

        try:
            db1 = DatabaseManager.get("data/trajectory_evolution.db")
            rows = db1.query(
                "SELECT query, steps_json, fitness_score, intent_type FROM trajectories WHERE fitness_score >= 60 ORDER BY fitness_score DESC LIMIT 50"
            )
            db2 = DatabaseManager.get(self._db_path)
            for query, steps_str, fitness, intent_type in rows:
                try:
                    steps = json.loads(steps_str) if steps_str else []
                except (json.JSONDecodeError, TypeError):
                    steps = []
                strategy_desc = "→".join(
                    s.get("phase", "?") for s in steps[:6] if isinstance(s, dict)
                )
                if not strategy_desc:
                    continue
                existing = db2.query_one(
                    "SELECT id FROM strategic_memory WHERE dilemma = ? AND strategy = ?",
                    (query, strategy_desc)
                )
                if not existing:
                    db2.execute(
                        "INSERT INTO strategic_memory (dilemma, strategy, source, domains, evidence_count, success_rate, importance, last_updated, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (query, strategy_desc, "trajectory",
                         json.dumps([intent_type] if intent_type else []),
                         1, (fitness or 50) / 100.0, (fitness or 50) / 100.0, now, now), commit=True
                    )
                    count += 1
        except Exception as e:
            logger.warning(f"战略记忆同步(轨迹)跳过: {e}")

        logger.info(f"战略记忆同步完成: {count}条")
        return count

    def sync_procedural_memory(self) -> int:
        now = datetime.now().isoformat()
        count = 0

        try:
            db1 = DatabaseManager.get("data/learning_rules.db")
            rows = db1.query(
                "SELECT condition, action, confidence, apply_count, success_count, source FROM learning_rules WHERE status='active' AND confidence >= 0.5"
            )
            db2 = DatabaseManager.get(self._db_path)
            for condition, action, confidence, apply_count, success_count, source in rows:
                existing = db2.query_one(
                    "SELECT id FROM procedural_memory WHERE trigger_condition = ? AND sop_name = ?",
                    (condition, action)
                )
                if existing:
                    db2.execute(
                        "UPDATE procedural_memory SET confidence=?, apply_count=?, success_count=?, last_updated=? WHERE id=?",
                        (confidence or 0.5, apply_count or 0, success_count or 0, now, existing[0]), commit=True
                    )
                else:
                    db2.execute(
                        "INSERT INTO procedural_memory (sop_name, trigger_condition, steps, source, confidence, apply_count, success_count, last_updated, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (action, condition, json.dumps([action]), source or "rule",
                         confidence or 0.5, apply_count or 0, success_count or 0, now, now), commit=True
                    )
                    count += 1
        except Exception as e:
            logger.warning(f"程序记忆同步(规则)跳过: {e}")

        logger.info(f"程序记忆同步完成: {count}条")
        return count

    def sync_tool_memory(self) -> int:
        now = datetime.now().isoformat()
        count = 0

        try:
            from core.tool_registry import tool_executor
            stats = tool_executor.get_stats()
            db = DatabaseManager.get(self._db_path)
            for tool_name, stat in stats.items():
                existing = db.query_one(
                    "SELECT id FROM tool_memory WHERE tool_name = ?", (tool_name,)
                )
                if existing:
                    db.execute(
                        "UPDATE tool_memory SET call_count=?, success_count=?, avg_quality=?, last_used=? WHERE id=?",
                        (stat.get("calls", 0), int(stat.get("success_rate", 0) * stat.get("calls", 1)),
                         stat.get("success_rate", 0) * 100, now, existing[0]), commit=True
                    )
                else:
                    db.execute(
                        "INSERT INTO tool_memory (tool_name, call_count, success_count, avg_quality, last_used, created_at) VALUES (?,?,?,?,?,?)",
                        (tool_name, stat.get("calls", 0),
                         int(stat.get("success_rate", 0) * stat.get("calls", 1)),
                         stat.get("success_rate", 0) * 100, now, now), commit=True
                    )
                count += 1
        except Exception as e:
            logger.warning(f"工具记忆同步跳过: {e}")

        logger.info(f"工具记忆同步完成: {count}条")
        return count

    def query_strategic(self, dilemma: str, limit: int = 3) -> List[Dict]:
        try:
            db = DatabaseManager.get(self._db_path)
            rows = db.query(
                "SELECT * FROM strategic_memory WHERE dilemma LIKE ? OR domains LIKE ? ORDER BY importance DESC, success_rate DESC LIMIT ?",
                (f"%{dilemma[:20]}%", f"%{dilemma[:10]}%", limit)
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    def query_procedural(self, situation: str, limit: int = 3) -> List[Dict]:
        try:
            db = DatabaseManager.get(self._db_path)
            rows = db.query(
                "SELECT * FROM procedural_memory WHERE trigger_condition LIKE ? OR sop_name LIKE ? ORDER BY confidence DESC LIMIT ?",
                (f"%{situation[:20]}%", f"%{situation[:10]}%", limit)
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    def query_tool(self, query: str, limit: int = 5) -> List[Dict]:
        try:
            db = DatabaseManager.get(self._db_path)
            rows = db.query(
                "SELECT * FROM tool_memory WHERE tool_name LIKE ? OR query_pattern LIKE ? ORDER BY avg_quality DESC, success_count DESC LIMIT ?",
                (f"%{query[:15]}%", f"%{query[:10]}%", limit)
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_context_for_query(self, query: str) -> Dict:
        strategic = self.query_strategic(query)
        procedural = self.query_procedural(query)
        tool = self.query_tool(query)

        context_parts = []
        if strategic:
            strategies = [f"  - {s['strategy']} (来源:{s.get('source','?')}, 成功率:{s.get('success_rate',0):.0%})" for s in strategic[:2]]
            context_parts.append(f"【战略记忆】\n" + "\n".join(strategies))
        if procedural:
            sops = [f"  - 当{s['trigger_condition']}时→{s['sop_name']} (置信度:{s.get('confidence',0):.0%})" for s in procedural[:2]]
            context_parts.append(f"【程序记忆】\n" + "\n".join(sops))
        if tool:
            tools = [f"  - {t['tool_name']}: 质量{t.get('avg_quality',0):.0f}/调用{t.get('call_count',0)}次" for t in tool[:3]]
            context_parts.append(f"【工具记忆】\n" + "\n".join(tools))

        return {
            "strategic_count": len(strategic),
            "procedural_count": len(procedural),
            "tool_count": len(tool),
            "context": "\n\n".join(context_parts) if context_parts else "",
        }

    def record_tool_usage(self, tool_name: str, query: str, success: bool,
                          quality: int = 0, duration_ms: float = 0, params: Dict = None):
        now = datetime.now().isoformat()
        try:
            db = DatabaseManager.get(self._db_path)
            existing = db.query_one(
                "SELECT id, call_count, success_count, avg_quality, avg_duration_ms FROM tool_memory WHERE tool_name = ? AND query_pattern = ?",
                (tool_name, query[:50])
            )
            if existing:
                eid, calls, succs, avg_q, avg_d = existing
                new_calls = calls + 1
                new_succs = succs + (1 if success else 0)
                new_avg_q = (avg_q * calls + quality) / new_calls
                new_avg_d = (avg_d * calls + duration_ms) / new_calls
                db.execute(
                    "UPDATE tool_memory SET call_count=?, success_count=?, avg_quality=?, avg_duration_ms=?, best_params=?, last_used=? WHERE id=?",
                    (new_calls, new_succs, new_avg_q, new_avg_d,
                     json.dumps(params) if params else None, now, eid), commit=True
                )
            else:
                db.execute(
                    "INSERT INTO tool_memory (tool_name, query_pattern, best_params, avg_quality, avg_duration_ms, call_count, success_count, last_used, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (tool_name, query[:50], json.dumps(params) if params else None,
                     quality, duration_ms, 1, 1 if success else 0, now, now), commit=True
                )
        except Exception as e:
            logger.error(f"工具记忆记录失败: {e}")

    def decay_outdated(self) -> Dict:
        now = datetime.now()
        result = {"strategic_decayed": 0, "procedural_decayed": 0, "tool_decayed": 0}

        try:
            db = DatabaseManager.get(self._db_path)
            strategic_cutoff = (now - timedelta(days=30)).isoformat()
            result["strategic_decayed"] = db.execute(
                "DELETE FROM strategic_memory WHERE last_updated < ? AND evidence_count < 2 AND importance < 0.3",
                (strategic_cutoff,), commit=True
            ).rowcount

            procedural_cutoff = (now - timedelta(hours=72)).isoformat()
            result["procedural_decayed"] = db.execute(
                "DELETE FROM procedural_memory WHERE last_updated < ? AND confidence < 0.3 AND apply_count < 3",
                (procedural_cutoff,), commit=True
            ).rowcount

            tool_cutoff = (now - timedelta(hours=24)).isoformat()
            result["tool_decayed"] = db.execute(
                "DELETE FROM tool_memory WHERE last_used < ? AND call_count < 2",
                (tool_cutoff,), commit=True
            ).rowcount
        except Exception as e:
            logger.error(f"分层记忆衰减失败: {e}")

        return result

    def get_stats(self) -> Dict:
        try:
            db = DatabaseManager.get(self._db_path)
            strategic = db.query_one("SELECT COUNT(*) FROM strategic_memory")[0]
            procedural = db.query_one("SELECT COUNT(*) FROM procedural_memory")[0]
            tool = db.query_one("SELECT COUNT(*) FROM tool_memory")[0]
            return {
                "strategic": strategic,
                "procedural": procedural,
                "tool": tool,
                "total": strategic + procedural + tool,
            }
        except Exception:
            return {"strategic": 0, "procedural": 0, "tool": 0, "total": 0}


layered_memory = LayeredMemory()
