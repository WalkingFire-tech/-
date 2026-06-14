"""
工具管理器 - 动态加载和执行自动生成的工具
"""
import importlib.util
import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from loguru import logger


class ToolManager:
    """工具管理器 - 动态加载和执行工具函数"""
    
    TOOLS_DIR = Path("data/auto_tools")
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self.tools_dir = self.TOOLS_DIR
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        
        self.loaded_tools = {}
        
        logger.info(f"工具管理器已初始化，工具目录: {self.tools_dir}")
    
    def _ensure_tool_file(self, name: str, code: str) -> Path:
        """确保工具文件存在"""
        tool_file = self.tools_dir / f"{name}.py"
        
        if not tool_file.exists() or tool_file.read_text() != code:
            tool_file.write_text(code)
            logger.info(f"工具文件已创建: {name}.py")
        
        return tool_file
    
    def load_tool(self, name: str) -> Optional[Callable]:
        """加载工具函数"""
        
        if name in self.loaded_tools:
            return self.loaded_tools[name]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT code FROM tools WHERE name = ?', (name,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"工具不存在: {name}")
                return None
            
            code = row['code']
        
        try:
            tool_file = self._ensure_tool_file(name, code)
            
            spec = importlib.util.spec_from_file_location(
                f"auto_tool_{name}",
                tool_file
            )
            
            if not spec or not spec.loader:
                logger.error(f"无法创建模块规范: {name}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            
            module_name = f"auto_tools.{name}"
            sys.modules[module_name] = module
            
            spec.loader.exec_module(module)
            
            if hasattr(module, name):
                tool_func = getattr(module, name)
            elif hasattr(module, 'main'):
                tool_func = getattr(module, 'main')
            else:
                func_names = [n for n in dir(module) if not n.startswith('_') and callable(getattr(module, n))]
                if func_names:
                    tool_func = getattr(module, func_names[0])
                else:
                    logger.error(f"工具模块无可调用函数: {name}")
                    return None
            
            self.loaded_tools[name] = tool_func
            logger.info(f"工具已加载: {name}")
            
            return tool_func
            
        except Exception as e:
            logger.error(f"加载工具失败 {name}: {e}")
            return None
    
    def execute_tool(self, name: str, *args, **kwargs) -> Any:
        """执行工具函数"""
        
        tool_func = self.load_tool(name)
        
        if not tool_func:
            raise ValueError(f"工具不存在或加载失败: {name}")
        
        try:
            result = tool_func(*args, **kwargs)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE tools
                    SET usage_count = usage_count + 1
                    WHERE name = ?
                ''', (name,))
                conn.commit()
            
            logger.info(f"工具执行成功: {name}")
            
            return result
            
        except Exception as e:
            logger.error(f"工具执行失败 {name}: {e}")
            raise
    
    def get_tool_info(self, name: str) -> Optional[Dict]:
        """获取工具信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM tools WHERE name = ?', (name,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT name, description, usage_count, created_at
                FROM tools
                ORDER BY usage_count DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_tool(self, name: str, code: str, description: str,
                   triggers: List[str] = None) -> bool:
        """创建新工具"""
        
        try:
            triggers = triggers or []
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO tools
                    (name, code, description, triggers, usage_count, created_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                ''', (
                    name,
                    code,
                    description,
                    str(triggers),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            self._ensure_tool_file(name, code)
            
            logger.info(f"工具已创建: {name}")
            return True
            
        except Exception as e:
            logger.error(f"创建工具失败: {e}")
            return False
    
    def delete_tool(self, name: str) -> bool:
        """删除工具"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM tools WHERE name = ?', (name,))
                conn.commit()
            
            tool_file = self.tools_dir / f"{name}.py"
            if tool_file.exists():
                tool_file.unlink()
            
            if name in self.loaded_tools:
                del self.loaded_tools[name]
            
            logger.info(f"工具已删除: {name}")
            return True
            
        except Exception as e:
            logger.error(f"删除工具失败: {e}")
            return False
    
    def test_tool(self, name: str, test_input: Any = None) -> Dict:
        """测试工具"""
        
        try:
            tool_func = self.load_tool(name)
            
            if not tool_func:
                return {
                    "success": False,
                    "error": "工具加载失败"
                }
            
            if test_input is not None:
                result = tool_func(test_input)
            else:
                result = tool_func()
            
            return {
                "success": True,
                "result": str(result)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def reload_all_tools(self):
        """重新加载所有工具"""
        
        self.loaded_tools.clear()
        
        tools = self.list_tools()
        for tool in tools:
            self.load_tool(tool['name'])
        
        logger.info(f"已重新加载 {len(tools)} 个工具")


tool_manager = ToolManager()