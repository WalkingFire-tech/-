"""
模块健康监控器 - 故障隔离与自愈

类比人体机制：
- 炎症反应：模块故障时隔离，防止级联故障
- 细胞凋亡：持续异常的模块自动下线
- 干细胞：自动重启并验证修复
"""
import time
from typing import Dict, Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager
from datetime import datetime


class ModuleHealthMonitor:
    """模块级健康监控——故障隔离、自愈开关、异常吞噬"""

    FAILURE_THRESHOLD = 5
    ISOLATION_DURATION = 300
    RESTART_COOLDOWN = 60

    def __init__(self, db_path: str = "data/module_health.db"):
        self.db_path = db_path
        self._init_db()
        self._module_stats: Dict[str, dict] = {}

    def _init_db(self):
        try:
            db = DatabaseManager.get(self.db_path)
            db.executescript('''CREATE TABLE IF NOT EXISTS module_health (
                module_name TEXT PRIMARY KEY,
                status TEXT DEFAULT 'healthy',
                failure_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_failure TEXT,
                last_success TEXT,
                isolated_at TEXT,
                restarted_at TEXT,
                anomaly_patterns TEXT
            );
            CREATE TABLE IF NOT EXISTS health_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_name TEXT,
                event_type TEXT,
                detail TEXT,
                timestamp TEXT
            )''')

        except Exception as e:
            logger.error(f"模块健康数据库初始化失败: {e}")

    def record_success(self, module_name: str):
        """记录模块成功"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("INSERT OR IGNORE INTO module_health (module_name) VALUES (?)", (module_name,), commit=True)
            db.execute("UPDATE module_health SET success_count=success_count+1, last_success=?, status=CASE WHEN status='degraded' THEN 'degraded' ELSE 'healthy' END WHERE module_name=?",
                      (datetime.now().isoformat(), module_name), commit=True)
            db.execute("INSERT INTO health_events (module_name, event_type, detail, timestamp) VALUES (?, 'success', '', ?)",
                      (module_name, datetime.now().isoformat()), commit=True)

        except Exception:
            logger.warning("操作降级跳过")

    def record_failure(self, module_name: str, detail: str = ""):
        """记录模块失败，检查是否需要隔离"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("INSERT OR IGNORE INTO module_health (module_name) VALUES (?)", (module_name,), commit=True)
            db.execute("UPDATE module_health SET failure_count=failure_count+1, last_failure=? WHERE module_name=?",
                      (datetime.now().isoformat(), module_name), commit=True)
            db.execute("INSERT INTO health_events (module_name, event_type, detail, timestamp) VALUES (?, 'failure', ?, ?)",
                      (module_name, detail[:200], datetime.now().isoformat()), commit=True)

            row = db.query_one("SELECT failure_count, success_count FROM module_health WHERE module_name=?", (module_name,))
            if row:
                failures, successes = row[0], row[1]
                total = failures + successes
                error_rate = failures / max(total, 1)
                if failures >= self.FAILURE_THRESHOLD or (total >= 10 and error_rate > 0.5):
                    db.execute("UPDATE module_health SET status='isolated', isolated_at=? WHERE module_name=?",
                              (datetime.now().isoformat(), module_name), commit=True)
                    logger.warning(f"🔒 模块{module_name}已隔离: 失败{failures}次, 错误率{error_rate:.0%}")
                    db.execute("INSERT INTO health_events (module_name, event_type, detail, timestamp) VALUES (?, 'isolated', ?, ?)",
                              (module_name, f"失败{failures}次,错误率{error_rate:.0%}", datetime.now().isoformat()), commit=True)
                elif error_rate > 0.2:
                    db.execute("UPDATE module_health SET status='degraded' WHERE module_name=?", (module_name,), commit=True)
                    logger.warning(f"⚠️ 模块{module_name}降级: 错误率{error_rate:.0%}")

        except Exception:
            logger.warning("操作降级跳过")

    def is_module_available(self, module_name: str) -> bool:
        """检查模块是否可用（未隔离）"""
        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one("SELECT status, isolated_at FROM module_health WHERE module_name=?", (module_name,))

            if not row:
                return True
            status, isolated_at = row[0], row[1]
            if status == "isolated" and isolated_at:
                try:
                    isolated_time = datetime.fromisoformat(isolated_at)
                    if (datetime.now() - isolated_time).total_seconds() > self.ISOLATION_DURATION:
                        return True
                except Exception:
                    logger.warning("操作降级跳过")
            return status != "isolated"
        except Exception:
            return True

    def get_health_report(self) -> dict:
        """获取所有模块的健康报告"""
        report = {"healthy": [], "degraded": [], "isolated": [], "unknown": []}
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query("SELECT module_name, status, failure_count, success_count, last_failure FROM module_health")
            for row in rows:
                entry = {"name": row[0], "status": row[1], "failures": row[2], "successes": row[3], "last_failure": row[4]}
                if row[1] in report:
                    report[row[1]].append(entry)
                else:
                    report["unknown"].append(entry)

        except Exception:
            logger.warning("操作降级跳过")
        return report

    def clear_anomalies(self, module_name: str):
        """异常吞噬：清理模块的异常状态"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("UPDATE module_health SET failure_count=0, status='healthy' WHERE module_name=?", (module_name,), commit=True)
            db.execute("INSERT INTO health_events (module_name, event_type, detail, timestamp) VALUES (?, 'cleared', '异常吞噬：状态重置', ?)",
                      (module_name, datetime.now().isoformat()), commit=True)

            logger.info(f"🧹 模块{module_name}异常已清除")
        except Exception:
            logger.warning("操作降级跳过")


module_health = ModuleHealthMonitor()
