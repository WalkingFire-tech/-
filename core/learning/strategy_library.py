"""
策略库 — 从失败中提炼可复用的抽象策略

灵感来源：哥德尔智能体(Gödel Agent)的"经验抽象"机制
核心思想：将每一次失败都转化为系统进化的"基因"

策略库结构：
- trigger_pattern: 触发条件（如"Ollama超时"、"规则匹配失败"）
- action_patch: 修复动作（如"切换到DeepSeek API"、"降低并行度"）
- confidence: 置信度（0-1，随成功/失败动态调整）
- success_count / fail_count: 统计计数
- source: 来源（curiosity/l5_defect/persistent_solver/experience）

与L5的关系：
- PatchGenerator生成补丁时查询策略库，优先复用已验证策略
- L5修改成功/失败后，结果反馈到策略库

与好奇心的关系：
- 好奇心探索发现的缺口，学习结果沉淀到策略库
- 策略库中的低置信度条目，成为好奇心的探索目标
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    id: Optional[int] = None
    trigger_pattern: str = ""
    action_patch: str = ""
    category: str = ""
    confidence: float = 0.5
    success_count: int = 0
    fail_count: int = 0
    source: str = ""
    context: str = ""
    created_at: str = ""
    last_used: str = ""
    is_active: bool = True


class StrategyLibrary:
    DB_PATH = "data/strategy_library.db"

    def __init__(self):
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(self.DB_PATH)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_pattern TEXT NOT NULL,
                    action_patch TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.5,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    source TEXT DEFAULT '',
                    context TEXT DEFAULT '',
                    created_at TEXT DEFAULT '',
                    last_used TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_trigger ON strategies(trigger_pattern);
                CREATE INDEX IF NOT EXISTS idx_category ON strategies(category);
                CREATE INDEX IF NOT EXISTS idx_confidence ON strategies(confidence DESC);
            """)
        except Exception as e:
            logger.warning(f"策略库初始化跳过: {e}")

    def add_strategy(self, trigger_pattern: str, action_patch: str,
                     category: str = "", source: str = "",
                     context: str = "", confidence: float = 0.5) -> Optional[int]:
        with self._lock:
            try:
                from core.ports.adapters import get_storage_port
                db = get_storage_port(self.DB_PATH)

                existing = db.query_one(
                    "SELECT id FROM strategies WHERE trigger_pattern = ? AND action_patch = ?",
                    (trigger_pattern, action_patch)
                )
                if existing:
                    return existing[0]

                now = datetime.now().isoformat()
                db.execute("""
                    INSERT INTO strategies
                    (trigger_pattern, action_patch, category, confidence,
                     success_count, fail_count, source, context, created_at, last_used, is_active)
                    VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, ?, 1)
                """, (trigger_pattern, action_patch, category, confidence,
                      source, context, now, now), commit=True)

                row = db.query_one(
                    "SELECT id FROM strategies WHERE trigger_pattern = ? AND action_patch = ?",
                    (trigger_pattern, action_patch)
                )
                strategy_id = row[0] if row else None
                logger.info(f"📋 新策略 #{strategy_id}: {trigger_pattern[:40]} → {action_patch[:40]}")
                return strategy_id
            except Exception as e:
                logger.warning(f"策略添加跳过: {e}")
                return None

    def query_strategy(self, trigger_pattern: str, category: str = "") -> List[Strategy]:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(self.DB_PATH)

            if category:
                rows = db.query("""
                    SELECT id, trigger_pattern, action_patch, category, confidence,
                           success_count, fail_count, source, context, created_at, last_used, is_active
                    FROM strategies
                    WHERE is_active = 1 AND category = ?
                    ORDER BY confidence DESC, success_count DESC
                    LIMIT 5
                """, (category,))
            else:
                rows = db.query("""
                    SELECT id, trigger_pattern, action_patch, category, confidence,
                           success_count, fail_count, source, context, created_at, last_used, is_active
                    FROM strategies
                    WHERE is_active = 1
                    ORDER BY confidence DESC, success_count DESC
                    LIMIT 10
                """)

            results = []
            for row in (rows or []):
                trigger = row[1] or ""
                if trigger_pattern.lower() in trigger.lower() or trigger.lower() in trigger_pattern.lower():
                    results.append(Strategy(
                        id=row[0], trigger_pattern=row[1], action_patch=row[2],
                        category=row[3], confidence=row[4], success_count=row[5],
                        fail_count=row[6], source=row[7], context=row[8],
                        created_at=row[9], last_used=row[10], is_active=bool(row[11])
                    ))
            return results
        except Exception as e:
            logger.debug(f"策略查询跳过: {e}")
            return []

    def record_outcome(self, strategy_id: int, success: bool):
        with self._lock:
            try:
                from core.ports.adapters import get_storage_port
                db = get_storage_port(self.DB_PATH)

                if success:
                    db.execute("""
                        UPDATE strategies
                        SET success_count = success_count + 1,
                            confidence = MIN(confidence + 0.05, 1.0),
                            last_used = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), strategy_id), commit=True)
                else:
                    db.execute("""
                        UPDATE strategies
                        SET fail_count = fail_count + 1,
                            confidence = MAX(confidence - 0.1, 0.0),
                            last_used = ?
                        WHERE id = ?
                    """, (datetime.now().isoformat(), strategy_id), commit=True)

                    row = db.query_one(
                        "SELECT confidence, fail_count FROM strategies WHERE id = ?",
                        (strategy_id,)
                    )
                    if row and row[0] < 0.1 and row[1] >= 3:
                        db.execute(
                            "UPDATE strategies SET is_active = 0 WHERE id = ?",
                            (strategy_id,), commit=True
                        )
                        logger.info(f"📋 策略 #{strategy_id} 已停用（置信度过低）")
            except Exception as e:
                logger.debug(f"策略结果记录跳过: {e}")

    def extract_from_failure(self, failure_type: str, failure_detail: str,
                             fix_action: str = "", category: str = "",
                             source: str = "auto") -> Optional[int]:
        if not fix_action:
            fix_action = f"待学习: {failure_type}"

        return self.add_strategy(
            trigger_pattern=failure_type,
            action_patch=fix_action,
            category=category,
            source=source,
            context=failure_detail[:200],
            confidence=0.3,
        )

    def get_low_confidence_strategies(self, threshold: float = 0.4) -> List[Strategy]:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(self.DB_PATH)
            rows = db.query("""
                SELECT id, trigger_pattern, action_patch, category, confidence,
                       success_count, fail_count, source, context, created_at, last_used, is_active
                FROM strategies
                WHERE is_active = 1 AND confidence < ?
                ORDER BY confidence ASC
                LIMIT 10
            """, (threshold,))

            return [Strategy(
                id=row[0], trigger_pattern=row[1], action_patch=row[2],
                category=row[3], confidence=row[4], success_count=row[5],
                fail_count=row[6], source=row[7], context=row[8],
                created_at=row[9], last_used=row[10], is_active=bool(row[11])
            ) for row in (rows or [])]
        except Exception as e:
            logger.debug(f"低置信度策略查询跳过: {e}")
            return []

    def get_stats(self) -> Dict:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(self.DB_PATH)
            total = db.query_one("SELECT COUNT(*) FROM strategies WHERE is_active = 1")
            high_conf = db.query_one("SELECT COUNT(*) FROM strategies WHERE is_active = 1 AND confidence >= 0.7")
            low_conf = db.query_one("SELECT COUNT(*) FROM strategies WHERE is_active = 1 AND confidence < 0.4")
            avg_conf = db.query_one("SELECT AVG(confidence) FROM strategies WHERE is_active = 1")
            return {
                "total_active": total[0] if total else 0,
                "high_confidence": high_conf[0] if high_conf else 0,
                "low_confidence": low_conf[0] if low_conf else 0,
                "avg_confidence": round(avg_conf[0], 2) if avg_conf and avg_conf[0] else 0,
            }
        except Exception:
            return {"total_active": 0, "high_confidence": 0, "low_confidence": 0, "avg_confidence": 0}


strategy_library = StrategyLibrary()