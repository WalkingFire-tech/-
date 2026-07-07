"""
工具结果缓存模块 (Tool Result Cache)
避免重复计算，提升响应速度
"""
import sqlite3
import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path


class ToolResultCache:
    """工具结果缓存器"""
    
    MAX_PARAMS_SIZE = 10240  # 10KB
    MAX_RESULT_SIZE = 102400  # 100KB
    
    def __init__(self, db_path: str = "tool_cache.db", ttl_days: int = 7):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self._init_db()
        
    def _init_db(self):
        """初始化缓存数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_cache (
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
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_cache_lookup
                ON tool_cache(tool_name, params_hash)
            """)
        
        logger.info(f"工具缓存数据库初始化完成: {self.db_path}")
    
    def _hash_params(self, params: Dict) -> str:
        """计算参数哈希"""
        # 排序键确保相同参数产生相同哈希
        sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_params.encode()).hexdigest()[:16]
    
    def get(self, tool_name: str, params: Dict) -> Optional[Any]:
        """
        获取缓存结果
        
        Args:
            tool_name: 工具名称
            params: 工具参数
        
        Returns:
            缓存的结果，未命中返回None
        """
        params_hash = self._hash_params(params)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT result_json, expires_at, hit_count
                FROM tool_cache
                WHERE tool_name = ? AND params_hash = ?
            """, (tool_name, params_hash))
            
            row = cursor.fetchone()
            
            if row:
                result_json, expires_at, hit_count = row
                
                if expires_at:
                    expires = datetime.fromisoformat(expires_at)
                    if datetime.now() > expires:
                        logger.debug(f"缓存已过期: {tool_name}")
                        cursor.execute("""
                            DELETE FROM tool_cache
                            WHERE tool_name = ? AND params_hash = ?
                        """, (tool_name, params_hash))
                        return None
                
                cursor.execute("""
                    UPDATE tool_cache
                    SET hit_count = hit_count + 1
                    WHERE tool_name = ? AND params_hash = ?
                """, (tool_name, params_hash))
                
                try:
                    result = json.loads(result_json)
                    logger.debug(f"缓存命中: {tool_name} (命中{hit_count + 1}次)")
                    return result
                except:
                    logger.warning(f"缓存结果解析失败: {tool_name}")
                    return None
        
        return None
    
    def set(
        self,
        tool_name: str,
        params: Dict,
        result: Any,
        quality_score: float = 1.0,
        ttl_days: Optional[int] = None
    ):
        """
        设置缓存结果
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            result: 工具结果
            quality_score: 质量评分（高质量结果更值得缓存）
            ttl_days: 缓存有效期（天）
        """
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO tool_cache
                    (tool_name, params_hash, params_json, result_json, quality_score, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tool_name,
                    params_hash,
                    params_json,
                    result_json,
                    quality_score,
                    datetime.now().isoformat(),
                    expires_at
                ))
                
                logger.debug(f"缓存已保存: {tool_name} (质量{quality_score:.2f})")
                
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
    
    def invalidate(self, tool_name: str, params: Optional[Dict] = None):
        """
        使缓存失效
        
        Args:
            tool_name: 工具名称
            params: 如果提供，只删除特定参数的缓存；否则删除该工具的所有缓存
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if params:
                params_hash = self._hash_params(params)
                cursor.execute("""
                    DELETE FROM tool_cache
                    WHERE tool_name = ? AND params_hash = ?
                """, (tool_name, params_hash))
            else:
                cursor.execute("""
                    DELETE FROM tool_cache
                    WHERE tool_name = ?
                """, (tool_name,))
            
            deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"缓存已失效: {tool_name} ({deleted}条)")
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM tool_cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            
            deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"清理过期缓存: {deleted}条")
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tool_cache")
            total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT tool_name, COUNT(*), SUM(hit_count), AVG(quality_score)
                FROM tool_cache
                GROUP BY tool_name
            """)
            
            by_tool = {}
            for row in cursor.fetchall():
                by_tool[row[0]] = {
                    "count": row[1],
                    "hits": row[2] or 0,
                    "avg_quality": row[3] or 0
                }
        
        return {
            "total_cached": total,
            "by_tool": by_tool
        }


# 集成到工具执行器
def integrate_with_executor():
    """
    在core/services/planner.py的SubTaskExecutor中集成缓存
    """
    code = """
from infrastructure.tool_cache import ToolResultCache
from infrastructure.database_manager import DatabaseManager

class SubTaskExecutor:
    def __init__(self, tools: Dict[str, Tool], llm_adapter=None):
        self.tools = tools
        self.llm_adapter = llm_adapter
        
        # 添加工具缓存
        self.tool_cache = ToolResultCache()
    
    def execute_tool(self, tool_name: str, params: Dict) -> ToolResult:
        '''执行工具（带缓存）'''
        
        # 1. 尝试从缓存获取
        cached_result = self.tool_cache.get(tool_name, params)
        if cached_result is not None:
            logger.info(f"使用缓存结果: {tool_name}")
            return ToolResult(
                success=True,
                output=cached_result.get("output", ""),
                metadata={"from_cache": True, **cached_result.get("metadata", {})}
            )
        
        # 2. 执行工具
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"工具不存在: {tool_name}")
        
        result = tool.execute(**params)
        
        # 3. 缓存成功结果
        if result.success and result.output:
            self.tool_cache.set(
                tool_name,
                params,
                {
                    "output": result.output,
                    "metadata": result.metadata
                },
                quality_score=result.metadata.get("quality", 1.0)
            )
        
        return result
"""
    return code


if __name__ == "__main__":
    # 测试工具缓存
    print("=" * 60)
    print("工具结果缓存测试")
    print("=" * 60)
    
    cache = ToolResultCache()
    
    # 测试1: 设置缓存
    print("\n测试1: 设置缓存")
    cache.set(
        "calculate",
        {"expression": "2 + 2"},
        {"output": "4", "metadata": {"method": "eval"}},
        quality_score=1.0
    )
    print("  ✓ 缓存已设置")
    
    # 测试2: 获取缓存
    print("\n测试2: 获取缓存")
    result = cache.get("calculate", {"expression": "2 + 2"})
    if result:
        print(f"  ✓ 缓存命中: {result}")
    else:
        print("  ✗ 缓存未命中")
    
    # 测试3: 未命中
    print("\n测试3: 不同参数（未命中）")
    result = cache.get("calculate", {"expression": "3 + 3"})
    if result:
        print(f"  缓存命中: {result}")
    else:
        print("  ✓ 缓存未命中（预期）")
    
    # 测试4: 统计
    print("\n测试4: 缓存统计")
    stats = cache.get_stats()
    print(f"  总缓存数: {stats['total_cached']}")
    print(f"  按工具: {stats['by_tool']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)