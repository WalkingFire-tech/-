"""工具结果缓存模块 - 避免重复计算，提升响应速度"""
import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
from infrastructure.database_manager import DatabaseManager


class ToolResultCache:
    """工具结果缓存器"""
    
    MAX_PARAMS_SIZE = 10240
    MAX_RESULT_SIZE = 102400
    
    def __init__(self, db_path: str = "data/tool_cache.db", ttl_days: int = 7):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self._init_db()
        
    def _init_db(self):
        db = DatabaseManager.get(self.db_path)
        db.execute("""CREATE TABLE IF NOT EXISTS tool_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                params_hash TEXT NOT NULL,
                params_json TEXT,
                result_json TEXT NOT NULL,
                quality_score REAL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                hit_count INTEGER DEFAULT 0,
                UNIQUE(tool_name, params_hash)
            )""", commit=True)
        db.execute("""CREATE INDEX IF NOT EXISTS idx_tool_cache_lookup
            ON tool_cache(tool_name, params_hash)""", commit=True)
        logger.info(f"工具缓存数据库初始化完成: {self.db_path}")
    
    def _hash_params(self, params: Dict) -> str:
        sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_params.encode()).hexdigest()[:16]
    
    def get(self, tool_name: str, params: Dict) -> Optional[Any]:
        params_hash = self._hash_params(params)
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("""SELECT result_json, expires_at, hit_count
            FROM tool_cache WHERE tool_name = ? AND params_hash = ?""",
            (tool_name, params_hash))
        
        if row:
            result_json, expires_at, hit_count = row
            if expires_at:
                expires = datetime.fromisoformat(expires_at)
                if datetime.now() > expires:
                    logger.debug(f"缓存已过期: {tool_name}")
                    db.execute("""DELETE FROM tool_cache
                        WHERE tool_name = ? AND params_hash = ?""",
                        (tool_name, params_hash), commit=True)
                    return None
            
            db.execute("""UPDATE tool_cache SET hit_count = hit_count + 1
                WHERE tool_name = ? AND params_hash = ?""",
                (tool_name, params_hash), commit=True)
            
            try:
                result = json.loads(result_json)
                logger.debug(f"缓存命中: {tool_name} (命中{hit_count + 1}次)")
                return result
            except Exception:
                logger.warning(f"缓存结果解析失败: {tool_name}")
                return None
        
        return None
    
    def set(self, tool_name: str, params: Dict, result: Any,
            quality_score: float = 1.0, ttl_days: Optional[int] = None):
        params_hash = self._hash_params(params)
        params_json = json.dumps(params, ensure_ascii=False)
        result_json = json.dumps(result, ensure_ascii=False)
        
        if len(params_json) > self.MAX_PARAMS_SIZE:
            logger.warning(f"参数过大，不缓存: {tool_name} ({len(params_json)} bytes)")
            return
        if len(result_json) > self.MAX_RESULT_SIZE:
            logger.warning(f"结果过大，不缓存: {tool_name} ({len(result_json)} bytes)")
            return
        
        ttl = ttl_days or self.ttl_days
        expires_at = (datetime.now() + timedelta(days=ttl)).isoformat()
        
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("""INSERT OR REPLACE INTO tool_cache
                (tool_name, params_hash, params_json, result_json, quality_score, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (tool_name, params_hash, params_json, result_json,
                 quality_score, datetime.now().isoformat(), expires_at),
                commit=True)
            logger.debug(f"缓存已保存: {tool_name} (质量{quality_score:.2f})")
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
    
    def invalidate(self, tool_name: str, params: Optional[Dict] = None):
        db = DatabaseManager.get(self.db_path)
        if params:
            params_hash = self._hash_params(params)
            db.execute("""DELETE FROM tool_cache
                WHERE tool_name = ? AND params_hash = ?""",
                (tool_name, params_hash), commit=True)
        else:
            db.execute("DELETE FROM tool_cache WHERE tool_name = ?",
                       (tool_name,), commit=True)
        logger.info(f"缓存已失效: {tool_name}")
    
    def cleanup_expired(self) -> int:
        db = DatabaseManager.get(self.db_path)
        cur = db.execute("DELETE FROM tool_cache WHERE expires_at < ?",
                         (datetime.now().isoformat(),), commit=True)
        deleted = cur.rowcount
        if deleted > 0:
            logger.info(f"清理过期缓存: {deleted}条")
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        db = DatabaseManager.get(self.db_path)
        total = db.query_one("SELECT COUNT(*) FROM tool_cache")[0]
        rows = db.query("""SELECT tool_name, COUNT(*), SUM(hit_count), AVG(quality_score)
            FROM tool_cache GROUP BY tool_name""")
        by_tool = {}
        for row in rows:
            by_tool[row[0]] = {"count": row[1], "hits": row[2] or 0, "avg_quality": row[3] or 0}
        return {"total_cached": total, "by_tool": by_tool}
