"""
运行时触发率监控器 — 确保关键能力"被设计即被调用"

设计原则：
1. 零侵入 — 装饰器/上下文管理器，不改变业务逻辑
2. 轻量级 — 内存计数器+定期持久化，不阻塞主路径
3. 可查询 — 随时获取任意分支的触发率
4. 自动告警 — 触发率低于阈值的分支自动标记

监控维度：
- 分支触发率：某逻辑分支被进入的次数/总调用次数
- 空结果率：某方法返回空/None/空列表的次数占比
- 退化率：某增强功能回退到降级路径的次数占比
"""

import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from loguru import logger
from core.ports.adapters import get_storage_port


class RuntimeTriggerMonitor:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "data/runtime_trigger_monitor.db"):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.db_path = db_path
        self._counters: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "triggered": 0, "empty_result": 0, "degraded": 0})
        self._last_persist = time.time()
        self._persist_interval = 60
        self._alert_threshold = 0.1
        self._init_db()

    def _init_db(self):
        try:
            db = get_storage_port(self.db_path)
            db.executescript('''
                CREATE TABLE IF NOT EXISTS trigger_stats (
                    branch_id TEXT PRIMARY KEY,
                    total_calls INTEGER DEFAULT 0,
                    triggered INTEGER DEFAULT 0,
                    empty_result INTEGER DEFAULT 0,
                    degraded INTEGER DEFAULT 0,
                    last_updated TEXT,
                    last_alerted TEXT
                )
            ''')
        except Exception as e:
            logger.debug(f"触发率监控数据库初始化跳过: {e}")

    def record(self, branch_id: str, triggered: bool = True, empty_result: bool = False, degraded: bool = False):
        """记录一次调用"""
        c = self._counters[branch_id]
        c["total"] += 1
        if triggered:
            c["triggered"] += 1
        if empty_result:
            c["empty_result"] += 1
        if degraded:
            c["degraded"] += 1

        if time.time() - self._last_persist > self._persist_interval:
            self._persist()
            self._last_persist = time.time()

    def get_trigger_rate(self, branch_id: str) -> Optional[float]:
        """获取某分支的触发率"""
        c = self._counters.get(branch_id)
        if not c or c["total"] == 0:
            try:
                db = get_storage_port(self.db_path)
                row = db.query_one("SELECT total_calls, triggered FROM trigger_stats WHERE branch_id=?", (branch_id,))
                if row:
                    total = row[0]
                    trig = row[1]
                    return trig / max(total, 1)
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
            return None
        return c["triggered"] / max(c["total"], 1)

    def get_empty_rate(self, branch_id: str) -> Optional[float]:
        """获取某分支的空结果率"""
        c = self._counters.get(branch_id)
        if not c or c["total"] == 0:
            return None
        return c["empty_result"] / max(c["total"], 1)

    def get_degradation_rate(self, branch_id: str) -> Optional[float]:
        """获取某分支的退化率"""
        c = self._counters.get(branch_id)
        if not c or c["total"] == 0:
            return None
        return c["degraded"] / max(c["total"], 1)

    def get_all_rates(self) -> List[Dict]:
        """获取所有分支的触发率"""
        results = []
        all_branches = set(self._counters.keys())
        try:
            db = get_storage_port(self.db_path)
            rows = db.query("SELECT branch_id FROM trigger_stats")
            for r in rows:
                all_branches.add(r[0])
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        for branch_id in sorted(all_branches):
            rate = self.get_trigger_rate(branch_id)
            empty = self.get_empty_rate(branch_id)
            degr = self.get_degradation_rate(branch_id)
            c = self._counters.get(branch_id, {"total": 0, "triggered": 0, "empty_result": 0, "degraded": 0})
            results.append({
                "branch_id": branch_id,
                "trigger_rate": round(rate, 3) if rate is not None else None,
                "empty_rate": round(empty, 3) if empty is not None else None,
                "degradation_rate": round(degr, 3) if degr is not None else None,
                "total_calls": c["total"],
                "triggered": c["triggered"],
            })
        return results

    def check_alerts(self) -> List[Dict]:
        """检查触发率低于阈值的分支，返回告警列表"""
        alerts = []
        for branch_id, c in self._counters.items():
            if c["total"] < 5:
                continue
            rate = c["triggered"] / max(c["total"], 1)
            if rate < self._alert_threshold:
                alerts.append({
                    "branch_id": branch_id,
                    "trigger_rate": round(rate, 3),
                    "total_calls": c["total"],
                    "severity": "critical" if rate < 0.05 else "warning",
                    "message": f"分支'{branch_id}'触发率仅{rate:.1%}（{c['triggered']}/{c['total']}），可能存在'能力存在但未运行'问题",
                })
        return alerts

    def _persist(self):
        """持久化计数器到数据库"""
        try:
            db = get_storage_port(self.db_path)
            for branch_id, c in self._counters.items():
                now = datetime.now().isoformat()
                db.execute(
                    "INSERT INTO trigger_stats (branch_id, total_calls, triggered, empty_result, degraded, last_updated) "
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(branch_id) DO UPDATE SET "
                    "total_calls=total_calls+?, triggered=triggered+?, empty_result=empty_result+?, degraded=degraded+?, last_updated=?",
                    (branch_id, c["total"], c["triggered"], c["empty_result"], c["degraded"], now,
                     c["total"], c["triggered"], c["empty_result"], c["degraded"], now),
                    commit=True,
                )
            self._counters.clear()
        except Exception as e:
            logger.debug(f"触发率持久化跳过: {e}")

    def flush(self):
        """强制持久化"""
        self._persist()


def monitor_branch(branch_id: str):
    """
    装饰器：自动监控函数的触发率和空结果率
    
    用法：
        @monitor_branch("trace_with_spirit.deep_trace")
        def some_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        monitor = RuntimeTriggerMonitor()

        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            triggered = result is not None and result != False
            empty = False
            if isinstance(result, (list, dict, str)):
                empty = len(result) == 0
            elif isinstance(result, dict):
                empty = not result
            monitor.record(branch_id, triggered=triggered, empty_result=empty)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


trigger_monitor = RuntimeTriggerMonitor()