"""
数据库连接池 - 提升并发性能
避免频繁创建和销毁连接
"""
import sqlite3
from queue import Queue
from threading import Lock
from contextlib import contextmanager
from loguru import logger
from typing import Optional


class SQLiteConnectionPool:
    """SQLite连接池"""
    
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: Queue = Queue(maxsize=max_connections)
        self._lock = Lock()
        self._size = 0
        self._create_initial_connections()
        
        logger.info(f"数据库连接池初始化: {db_path}, 最大连接数={max_connections}")
    
    def _create_initial_connections(self):
        """创建初始连接"""
        for _ in range(min(2, self.max_connections)):
            conn = self._create_connection()
            self._pool.put(conn)
            self._size += 1
    
    def _create_connection(self) -> sqlite3.Connection:
        """创建新连接"""
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def get_connection(self):
        """获取连接(上下文管理器)"""
        conn = None
        try:
            if not self._pool.empty():
                conn = self._pool.get(timeout=5)
            else:
                with self._lock:
                    if self._size < self.max_connections:
                        conn = self._create_connection()
                        self._size += 1
                    else:
                        conn = self._pool.get(timeout=5)
            
            yield conn
        
        except Exception as e:
            logger.error(f"获取数据库连接失败: {e}")
            raise
        
        finally:
            if conn:
                try:
                    self._pool.put(conn, timeout=1)
                except Exception:
                    conn.close()
                    with self._lock:
                        self._size -= 1
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get(timeout=1)
                conn.close()
                with self._lock:
                    self._size -= 1
            except Exception:
                pass
        
        logger.info("数据库连接池已关闭")


_pools: dict = {}


def get_db_pool(db_path: str = "model_stats.db", 
                max_connections: int = 5) -> SQLiteConnectionPool:
    """获取数据库连接池单例"""
    if db_path not in _pools:
        _pools[db_path] = SQLiteConnectionPool(db_path, max_connections)
    
    return _pools[db_path]


def close_all_pools():
    """关闭所有连接池"""
    for pool in _pools.values():
        pool.close_all()
    
    _pools.clear()
    logger.info("所有数据库连接池已关闭")