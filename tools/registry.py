"""
工具注册表 - 动态注册与管理工具
支持热插拔、自动发现、智能路由

与ToolArbiter的关系：
- ToolRegistry: 注册、查询、统计（不参与选择决策）
- ToolArbiter: 基于UCB1算法的工具选择器（唯一决策点）
- get_best_tool()已标记为deprecated，建议使用ToolArbiter
"""
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Type
from datetime import datetime
from loguru import logger
from tools.base import Tool, ToolCategory, ToolResult


class ToolRegistry:
    """工具注册表"""
    
    _instance = None
    
    def __new__(cls, config: Dict = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Tool] = {}
            
            config = config or {}
            stats_db_path = config.get("stats_db_path", "tool_stats.db")
            
            try:
                from infrastructure.config_manager import ConfigManager
                cm = ConfigManager()
                config_path = cm.get("stats.db_path", stats_db_path)
                if config_path:
                    stats_db_path = config_path
            except:
                pass
            
            cls._instance._stats_db = Path(stats_db_path)
            cls._instance._default_timeout = config.get("default_timeout", 30)
            cls._instance._init_stats_db()
        return cls._instance
    
    def _init_stats_db(self):
        """初始化统计数据库"""
        with sqlite3.connect(self._stats_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tool_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT,
                    category TEXT,
                    success BOOLEAN,
                    execution_time REAL,
                    error TEXT,
                    timestamp TEXT,
                    user_feedback INTEGER,
                    input_params TEXT,
                    output_summary TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tool ON tool_stats(tool_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON tool_stats(category)')
    
    def register(self, tool: Tool, overwrite: bool = False):
        """注册工具"""
        if tool.name in self._tools and not overwrite:
            logger.warning(f"工具已存在: {tool.name}")
            return False
        
        self._tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name} ({tool.category.value})")
        return True
    
    def unregister(self, tool_name: str) -> bool:
        """注销工具"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"注销工具: {tool_name}")
            return True
        return False
    
    def get(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(tool_name)
    
    def list_tools(self, category: ToolCategory = None) -> List[Tool]:
        """列出工具"""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())
    
    def find_tools_by_tags(self, tags: List[str]) -> List[Tool]:
        """根据标签查找工具"""
        result = []
        for tool in self._tools.values():
            metadata = tool.get_metadata()
            if any(tag in metadata.tags for tag in tags):
                result.append(tool)
        return result
    
    def execute(self, tool_name: str, timeout: float = None, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            timeout: 超时时间（秒），None使用默认值
            **kwargs: 工具参数
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"工具不存在: {tool_name}"
            )
        
        timeout = timeout or self._default_timeout
        
        result = tool.safe_execute(**kwargs)
        
        self._record_stats(tool_name, tool.category, result, kwargs)
        
        return result
    
    async def execute_async(self, tool_name: str, timeout: float = None, **kwargs) -> ToolResult:
        """异步执行工具（带超时控制）"""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"工具不存在: {tool_name}"
            )
        
        timeout = timeout or self._default_timeout
        
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: tool.safe_execute(**kwargs)
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            result = ToolResult(
                success=False,
                output=None,
                error=f"工具执行超时 ({timeout}秒)"
            )
        
        self._record_stats(tool_name, tool.category, result, kwargs)
        
        return result
    
    def _record_stats(self, tool_name: str, category: ToolCategory, 
                     result: ToolResult, params: Dict):
        """记录统计"""
        with sqlite3.connect(self._stats_db) as conn:
            conn.execute('''
                INSERT INTO tool_stats 
                (tool_name, category, success, execution_time, error, timestamp, input_params, output_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tool_name,
                category.value,
                result.success,
                result.execution_time,
                result.error,
                datetime.now().isoformat(),
                json.dumps(params, ensure_ascii=False)[:500],
                str(result.output)[:200] if result.output else None
            ))
    
    def get_tool_stats(self, tool_name: str) -> Dict:
        """获取工具统计"""
        with sqlite3.connect(self._stats_db) as conn:
            cur = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                    AVG(execution_time) as avg_time,
                    AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback
                FROM tool_stats
                WHERE tool_name = ?
            ''', (tool_name,))
            
            row = cur.fetchone()
            if row and row[0] > 0:
                return {
                    "total_calls": row[0],
                    "success_count": row[1],
                    "success_rate": row[1] / row[0],
                    "avg_execution_time": row[2],
                    "avg_feedback": row[3]
                }
            
            return {
                "total_calls": 0,
                "success_count": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "avg_feedback": 0.0
            }
    
    def get_best_tool(self, category: ToolCategory, min_success_rate: float = 0.5) -> Optional[Tool]:
        """
        获取最佳工具(基于统计)
        
        @deprecated 建议使用ToolArbiter进行工具选择
        ToolArbiter使用UCB1算法，更好地平衡探索与利用
        """
        import warnings
        warnings.warn(
            "get_best_tool()已废弃，建议使用ToolArbiter进行工具选择",
            DeprecationWarning,
            stacklevel=2
        )
        
        tools = self.list_tools(category)
        
        if not tools:
            return None
        
        scored_tools = []
        for tool in tools:
            stats = self.get_tool_stats(tool.name)
            
            if stats["total_calls"] < 3:
                score = 0.6
            else:
                success_score = stats["success_rate"]
                feedback_score = (stats["avg_feedback"] + 1) / 2 if stats["avg_feedback"] != 0 else 0.5
                speed_score = max(0, 1 - stats["avg_execution_time"] / 10.0)
                
                score = 0.5 * success_score + 0.3 * feedback_score + 0.2 * speed_score
            
            scored_tools.append((tool, score))
        
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        
        best_tool = scored_tools[0][0]
        logger.debug(f"选择最佳工具: {best_tool.name} (得分: {scored_tools[0][1]:.3f})")
        
        return best_tool
    
    def update_feedback(self, tool_name: str, feedback: int, record_id: int = None):
        """
        更新用户反馈
        
        Args:
            tool_name: 工具名称
            feedback: 反馈值 (-1负面, 0中性, 1正面)
            record_id: 指定记录ID，None则更新最新记录
        """
        with sqlite3.connect(self._stats_db) as conn:
            if record_id:
                conn.execute(
                    'UPDATE tool_stats SET user_feedback = ? WHERE id = ?',
                    (feedback, record_id)
                )
            else:
                conn.execute('''
                    UPDATE tool_stats
                    SET user_feedback = ?
                    WHERE id = (
                        SELECT id FROM tool_stats
                        WHERE tool_name = ?
                        ORDER BY timestamp DESC LIMIT 1
                    )
                ''', (feedback, tool_name))
            
            conn.commit()
    
    def get_feedback_history(self, tool_name: str, limit: int = 10) -> List[Dict]:
        """获取工具反馈历史"""
        with sqlite3.connect(self._stats_db) as conn:
            cur = conn.execute('''
                SELECT id, user_feedback, timestamp, success
                FROM tool_stats
                WHERE tool_name = ? AND user_feedback IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (tool_name, limit))
            
            return [
                {
                    "id": row[0],
                    "feedback": row[1],
                    "timestamp": row[2],
                    "success": row[3]
                }
                for row in cur.fetchall()
            ]
    
    def export_tools(self, file_path: str):
        """导出工具定义"""
        tools_data = [tool.to_dict() for tool in self._tools.values()]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tools_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"导出{len(tools_data)}个工具到: {file_path}")
    
    def import_tools(self, file_path: str):
        """导入工具定义(仅元数据)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
        
        logger.info(f"导入{len(tools_data)}个工具定义")
        # 实际工具需要代码实现,这里只记录元数据
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self._stats_db) as conn:
            # 总调用数
            cur = conn.execute('SELECT COUNT(*) FROM tool_stats')
            total_calls = cur.fetchone()[0]
            
            # 工具数量
            total_tools = len(self._tools)
            
            # 按类别统计
            cur = conn.execute('''
                SELECT category, COUNT(*) as count
                FROM tool_stats
                GROUP BY category
            ''')
            by_category = {row[0]: row[1] for row in cur.fetchall()}
            
            # 成功率
            cur = conn.execute('SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0 END) FROM tool_stats')
            success_rate = cur.fetchone()[0] or 0
        
        return {
            "total_tools": total_tools,
            "total_calls": total_calls,
            "by_category": by_category,
            "success_rate": success_rate
        }


# 全局注册表实例
registry = ToolRegistry()