"""
L4 自修复层 - 自动回滚 (Auto Rollback)

类比：适应性免疫——记住入侵者并快速响应
- 操作前创建快照
- 检测到异常时自动回滚到上一个稳定状态
- 回滚验证与审计
"""
import json
import time
import copy
from infrastructure.database_manager import DatabaseManager
from typing import Dict, List, Optional, Any
from loguru import logger
from datetime import datetime


class AutoRollback:
    MAX_SNAPSHOTS = 50
    ROLLBACK_ENTROPY_THRESHOLD = 0.7

    def __init__(self, db_path: str = "data/defense_snapshots.db"):
        self.db_path = db_path
        self._snapshots: Dict[str, List[dict]] = {}
        self._rollback_log: List[dict] = []
        self._init_db()

    def _init_db(self):
        try:
            db = DatabaseManager.get(self.db_path)
            db.executescript('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    data TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS rollback_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    reason TEXT,
                    entropy_before REAL,
                    entropy_after REAL,
                    created_at TEXT
                )
            ''')
        except Exception as e:
            logger.error(f"快照数据库初始化失败: {e}")

    def create_snapshot(self, target: str, data: Any) -> str:
        snapshot_id = f"snap_{int(time.time()*1000)}"
        snapshot = {
            "id": snapshot_id,
            "target": target,
            "data": copy.deepcopy(data) if isinstance(data, (dict, list)) else data,
            "created_at": datetime.now().isoformat(),
        }
        if target not in self._snapshots:
            self._snapshots[target] = []
        self._snapshots[target].append(snapshot)
        if len(self._snapshots[target]) > self.MAX_SNAPSHOTS:
            self._snapshots[target] = self._snapshots[target][-self.MAX_SNAPSHOTS:]
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("INSERT INTO snapshots (target, data, created_at) VALUES (?, ?, ?)",
                         (target, json.dumps(data, default=str, ensure_ascii=False)[:10000], datetime.now().isoformat()), commit=True)
        except Exception:
            logger.warning("操作降级跳过")
        return snapshot_id

    def rollback(self, target: str, reason: str = "", entropy: float = 0.0) -> Optional[Any]:
        if target not in self._snapshots or not self._snapshots[target]:
            logger.warning(f"⚠️ 无可回滚的快照: {target}")
            return None
        snapshot = self._snapshots[target][-1]
        entry = {
            "target": target,
            "snapshot_id": snapshot["id"],
            "reason": reason,
            "entropy": entropy,
            "timestamp": datetime.now().isoformat(),
        }
        self._rollback_log.append(entry)
        if len(self._rollback_log) > 200:
            self._rollback_log = self._rollback_log[-200:]
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("INSERT INTO rollback_log (target, reason, entropy_before, entropy_after, created_at) VALUES (?, ?, ?, ?, ?)",
                         (target, reason, entropy, 0.0, datetime.now().isoformat()), commit=True)
        except Exception:
            logger.warning("操作降级跳过")
        logger.info(f"⏪ 自动回滚: {target} (原因: {reason}, 熵值: {entropy:.2f})")
        return snapshot["data"]

    def should_rollback(self, entropy: float) -> bool:
        return entropy > self.ROLLBACK_ENTROPY_THRESHOLD

    def get_latest_snapshot(self, target: str) -> Optional[Any]:
        if target in self._snapshots and self._snapshots[target]:
            return self._snapshots[target][-1]["data"]
        return None

    def get_rollback_history(self, limit: int = 20) -> List[dict]:
        return self._rollback_log[-limit:]


auto_rollback = AutoRollback()