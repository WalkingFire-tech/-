"""
工具管理器 - 安全增强版

功能：
1. 动态加载和执行工具（带沙箱）
2. 工具代码校验（语法检查、导入限制）
3. 执行超时控制
4. 工具缓存和状态管理
5. 工具文件自动清理

安全机制：
- 限制可导入的模块（白名单）
- 限制内置函数（如 open, eval, exec）
- 执行超时（防止死循环）
- 工具代码沙箱隔离
"""

import importlib.util
import sys
import sqlite3
import threading
import time
import ast
import functools
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
from loguru import logger

try:
    import signal
except ImportError:
    signal = None


class ToolManager:
    """工具管理器 - 安全增强版"""
    
    TOOLS_DIR = Path("data/auto_tools")
    BACKUP_DIR = TOOLS_DIR / "backup"
    
    ALLOWED_MODULES = {
        'math', 'random', 'json', 're', 'datetime', 'collections',
        'itertools', 'functools', 'typing', 'enum', 'dataclasses',
        'string', 'time', 'uuid', 'hashlib', 'base64',
        'csv', 'xml.etree.ElementTree', 'json', 'yaml',
    }
    
    FORBIDDEN_BUILTINS = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'input', 'print', 'breakpoint',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr',
        'memoryview', 'buffer'
    }
    
    EXECUTION_TIMEOUT = 30
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self.tools_dir = self.TOOLS_DIR
        self.backup_dir = self.BACKUP_DIR
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._loaded_tools: Dict[str, Callable] = {}
        self._tool_metadata: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._code_cache: Dict[str, str] = {}
        
        self._init_db()
        self._cleanup_orphan_files()
        
        logger.info(f"工具管理器已初始化，工具目录: {self.tools_dir}")
    
    def _init_db(self):
        """初始化工具表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tools (
                    name TEXT PRIMARY KEY,
                    code TEXT,
                    description TEXT,
                    triggers TEXT,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_used TEXT,
                    enabled INTEGER DEFAULT 1
                )
            ''')
            
            # 迁移：添加缺失的列
            try:
                conn.execute('ALTER TABLE tools ADD COLUMN success_count INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute('ALTER TABLE tools ADD COLUMN failure_count INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute('ALTER TABLE tools ADD COLUMN enabled INTEGER DEFAULT 1')
            except sqlite3.OperationalError:
                pass
            
            conn.commit()
    
    def _cleanup_orphan_files(self):
        """清理孤立的工具文件"""
        existing_files = set(self.tools_dir.glob("*.py"))
        if not existing_files:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM tools")
            db_tools = {row[0] for row in cursor.fetchall()}
        
        for tool_file in existing_files:
            tool_name = tool_file.stem
            if tool_name not in db_tools:
                backup_file = self.backup_dir / f"{tool_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
                try:
                    tool_file.rename(backup_file)
                    logger.debug(f"孤儿工具文件已移动到备份: {backup_file}")
                except Exception as e:
                    logger.warning(f"备份孤儿文件失败: {e}")
    
    def _validate_code(self, code: str) -> tuple:
        """校验工具代码的安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if module_name not in self.ALLOWED_MODULES:
                        return False, f"禁止导入模块: {module_name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name not in self.ALLOWED_MODULES:
                        return False, f"禁止导入模块: {module_name}"
            
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.FORBIDDEN_BUILTINS:
                        return False, f"禁止使用内置函数: {func_name}"
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.FORBIDDEN_BUILTINS:
                        return False, f"禁止使用属性: {node.func.attr}"
        
        return True, ""
    
    def _ensure_tool_file(self, name: str, code: str, backup: bool = True) -> Path:
        """确保工具文件存在"""
        tool_file = self.tools_dir / f"{name}.py"
        
        if tool_file.exists():
            if tool_file.read_text() == code:
                return tool_file
            if backup:
                backup_file = self.backup_dir / f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
                try:
                    tool_file.rename(backup_file)
                    logger.debug(f"旧工具已备份: {backup_file}")
                except Exception as e:
                    logger.warning(f"备份旧工具失败: {e}")
        
        tool_file.write_text(code, encoding='utf-8')
        logger.info(f"工具文件已创建: {name}.py")
        return tool_file
    
    def load_tool(self, name: str) -> Optional[Callable]:
        """加载工具函数（带缓存）"""
        with self._lock:
            if name in self._loaded_tools:
                return self._loaded_tools[name]
            
            code = self._code_cache.get(name)
            if code is None:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute('SELECT code, enabled FROM tools WHERE name = ?', (name,))
                    row = cursor.fetchone()
                    if not row:
                        logger.warning(f"工具不存在: {name}")
                        return None
                    if not row['enabled']:
                        logger.warning(f"工具已禁用: {name}")
                        return None
                    code = row['code']
                    self._code_cache[name] = code
            
            is_valid, error = self._validate_code(code)
            if not is_valid:
                logger.error(f"工具代码校验失败 {name}: {error}")
                return None
            
            try:
                safe_globals = {
                    '__builtins__': {
                        'abs': abs, 'all': all, 'any': any,
                        'bool': bool, 'dict': dict, 'float': float,
                        'int': int, 'len': len, 'list': list,
                        'max': max, 'min': min, 'range': range,
                        'round': round, 'set': set, 'str': str,
                        'sum': sum, 'tuple': tuple, 'zip': zip,
                        'enumerate': enumerate, 'filter': filter,
                        'map': map, 'sorted': sorted,
                        'isinstance': isinstance, 'type': type,
                        'print': lambda *args, **kwargs: None,
                    },
                    '__name__': f'auto_tool_{name}',
                    '__doc__': None,
                }
                
                for module_name in self.ALLOWED_MODULES:
                    try:
                        safe_globals[module_name] = __import__(module_name)
                    except ImportError:
                        pass
                
                exec(code, safe_globals)
                
                tool_func = None
                if name in safe_globals and callable(safe_globals[name]):
                    tool_func = safe_globals[name]
                elif 'main' in safe_globals and callable(safe_globals['main']):
                    tool_func = safe_globals['main']
                else:
                    for key, value in safe_globals.items():
                        if callable(value) and not key.startswith('_'):
                            if key not in self.ALLOWED_MODULES:
                                tool_func = value
                                break
                
                if tool_func is None:
                    logger.error(f"工具模块无可调用函数: {name}")
                    return None
                
                wrapped_func = self._wrap_tool_function(tool_func, name)
                
                self._loaded_tools[name] = wrapped_func
                self._tool_metadata[name] = {
                    'loaded_at': datetime.now().isoformat(),
                }
                
                logger.info(f"工具已加载: {name}")
                return wrapped_func
                
            except Exception as e:
                logger.error(f"加载工具失败 {name}: {e}")
                return None
    
    def _wrap_tool_function(self, func: Callable, name: str) -> Callable:
        """包装工具函数，添加超时、日志、异常处理"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"执行工具: {name}")
            start_time = time.time()
            
            try:
                if signal is not None:
                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"工具执行超时 ({self.EXECUTION_TIMEOUT}秒)")
                    
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(self.EXECUTION_TIMEOUT)
                    try:
                        result = func(*args, **kwargs)
                    finally:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                else:
                    result = self._run_with_thread_timeout(func, args, kwargs)
                
                duration = (time.time() - start_time) * 1000
                self._update_tool_stats(name, success=True, duration=duration)
                
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                self._update_tool_stats(name, success=False, duration=duration)
                logger.error(f"工具执行失败 {name}: {e}")
                raise
        
        return wrapper
    
    def _run_with_thread_timeout(self, func: Callable, args: tuple, kwargs: dict) -> Any:
        """使用线程超时（Windows兼容）"""
        result_container = []
        exception_container = []
        completed = threading.Event()
        
        def target():
            try:
                result_container.append(func(*args, **kwargs))
            except Exception as e:
                exception_container.append(e)
            finally:
                completed.set()
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        
        if not completed.wait(timeout=self.EXECUTION_TIMEOUT):
            raise TimeoutError(f"工具执行超时 ({self.EXECUTION_TIMEOUT}秒)")
        
        if exception_container:
            raise exception_container[0]
        
        return result_container[0] if result_container else None
    
    def _update_tool_stats(self, name: str, success: bool, duration: float):
        """更新工具统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if success:
                    conn.execute('''
                        UPDATE tools
                        SET usage_count = usage_count + 1,
                            success_count = success_count + 1,
                            last_used = ?
                        WHERE name = ?
                    ''', (datetime.now().isoformat(), name))
                else:
                    conn.execute('''
                        UPDATE tools
                        SET usage_count = usage_count + 1,
                            failure_count = failure_count + 1,
                            last_used = ?
                        WHERE name = ?
                    ''', (datetime.now().isoformat(), name))
                conn.commit()
        except Exception as e:
            logger.warning(f"更新工具统计失败: {e}")
    
    def execute_tool(self, name: str, *args, **kwargs) -> Any:
        """执行工具函数（公共接口）"""
        tool_func = self.load_tool(name)
        if not tool_func:
            raise ValueError(f"工具不存在或加载失败: {name}")
        
        return tool_func(*args, **kwargs)
    
    def get_tool_info(self, name: str) -> Optional[Dict]:
        """获取工具信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT name, description, triggers, usage_count,
                       success_count, failure_count, created_at, last_used, enabled
                FROM tools WHERE name = ?
            ''', (name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def list_tools(self, include_disabled: bool = False) -> List[Dict]:
        """列出所有工具"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = 'SELECT name, description, usage_count, success_count, created_at, enabled FROM tools'
            if not include_disabled:
                query += ' WHERE enabled = 1'
            query += ' ORDER BY usage_count DESC'
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def create_tool(self, name: str, code: str, description: str,
                   triggers: List[str] = None) -> bool:
        """创建新工具"""
        with self._lock:
            is_valid, error = self._validate_code(code)
            if not is_valid:
                logger.error(f"工具代码校验失败: {error}")
                return False
            
            if not name.isidentifier():
                logger.error(f"工具名不合法: {name}")
                return False
            
            triggers = triggers or []
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO tools
                        (name, code, description, triggers, usage_count,
                         success_count, failure_count, created_at, last_used, enabled)
                        VALUES (?, ?, ?, ?, 0, 0, 0, ?, NULL, 1)
                    ''', (
                        name,
                        code,
                        description,
                        ','.join(triggers),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                
                self._ensure_tool_file(name, code, backup=True)
                
                self._code_cache.pop(name, None)
                self._loaded_tools.pop(name, None)
                
                logger.info(f"工具已创建: {name}")
                return True
                
            except Exception as e:
                logger.error(f"创建工具失败: {e}")
                return False
    
    def delete_tool(self, name: str) -> bool:
        """删除工具"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM tools WHERE name = ?', (name,))
                    conn.commit()
                
                tool_file = self.tools_dir / f"{name}.py"
                if tool_file.exists():
                    backup_file = self.backup_dir / f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
                    try:
                        tool_file.rename(backup_file)
                    except Exception as e:
                        logger.warning(f"备份工具文件失败: {e}")
                
                self._code_cache.pop(name, None)
                self._loaded_tools.pop(name, None)
                self._tool_metadata.pop(name, None)
                
                logger.info(f"工具已删除: {name}")
                return True
                
            except Exception as e:
                logger.error(f"删除工具失败: {e}")
                return False
    
    def enable_tool(self, name: str) -> bool:
        """启用工具"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE tools SET enabled = 1 WHERE name = ?', (name,))
            conn.commit()
        self._loaded_tools.pop(name, None)
        logger.info(f"工具已启用: {name}")
        return True
    
    def disable_tool(self, name: str) -> bool:
        """禁用工具"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE tools SET enabled = 0 WHERE name = ?', (name,))
            conn.commit()
        self._loaded_tools.pop(name, None)
        logger.info(f"工具已禁用: {name}")
        return True
    
    def test_tool(self, name: str, test_input: Any = None) -> Dict:
        """测试工具"""
        try:
            tool_func = self.load_tool(name)
            if not tool_func:
                return {"success": False, "error": "工具加载失败"}
            
            if test_input is not None:
                result = tool_func(test_input)
            else:
                result = tool_func()
            
            return {
                "success": True,
                "result": str(result)
            }
        except TimeoutError as e:
            return {"success": False, "error": f"超时: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def reload_all_tools(self):
        """重新加载所有工具"""
        with self._lock:
            self._loaded_tools.clear()
            self._code_cache.clear()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name FROM tools WHERE enabled = 1")
                tools = cursor.fetchall()
            
            for (name,) in tools:
                self.load_tool(name)
            
            logger.info(f"已重新加载 {len(tools)} 个工具")
    
    def get_tool_usage_stats(self) -> Dict:
        """获取工具使用统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_tools,
                    SUM(usage_count) as total_uses,
                    AVG(success_count * 1.0 / NULLIF(usage_count, 0)) as avg_success_rate,
                    SUM(usage_count) as total_usage
                FROM tools
                WHERE enabled = 1
            ''')
            row = cursor.fetchone()
            return {
                "total_tools": row[0] or 0,
                "total_uses": row[1] or 0,
                "avg_success_rate": row[2] if row[2] is not None else 0,
            }


tool_manager = ToolManager()
