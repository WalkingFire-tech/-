import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Any, Dict
from loguru import logger


class DatabaseManager:
    """线程安全的 SQLite 数据库管理器"""

    _instances: Dict[str, "DatabaseManager"] = {}
    _instances_lock = threading.Lock()

    @classmethod
    def get(cls, db_path: str, timeout: float = 10.0) -> "DatabaseManager":
        with cls._instances_lock:
            if db_path not in cls._instances:
                cls._instances[db_path] = cls(db_path, timeout)
            return cls._instances[db_path]

    def __init__(self, db_path: str, timeout: float = 10.0):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._timeout = timeout
        self._local = threading.local()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(str(self._path), timeout=self._timeout, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def execute(self, sql: str, params=(), commit: bool = False) -> sqlite3.Cursor:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(sql, params)
            if commit:
                conn.commit()
            return cursor

    def executemany(self, sql: str, seq_params, commit: bool = True) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.executemany(sql, seq_params)
            if commit:
                conn.commit()

    def executescript(self, script: str) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.executescript(script)

    def query(self, sql: str, params=()) -> List[sqlite3.Row]:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def query_one(self, sql: str, params=()) -> Optional[sqlite3.Row]:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(sql, params)
            return cursor.fetchone()

    def transaction(self, func, *args, **kwargs):
        with self._lock:
            conn = self._get_conn()
            try:
                result = func(conn, *args, **kwargs)
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    @property
    def path(self) -> str:
        return str(self._path)