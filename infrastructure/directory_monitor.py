"""
目录监控器 - 实时监控文件变化并自动处理
使用watchdog库监控指定目录,自动触发文件处理
"""
import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from datetime import datetime
from loguru import logger
from infrastructure.config_manager import config

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog未安装,目录监控功能不可用")

ALLOWED_BASE_DIRS = [
    Path.cwd() / "monitored",
    Path.cwd() / "uploads",
    Path.cwd() / "data",
]
MAX_PROCESSED_FILES = 1000


class FileChangeHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """文件变化处理器"""
    
    def __init__(self, 
                 on_created: Optional[Callable] = None,
                 on_modified: Optional[Callable] = None,
                 on_deleted: Optional[Callable] = None,
                 file_patterns: Optional[List[str]] = None,
                 allowed_base_dir: Optional[Path] = None):
        self.on_created_callback = on_created
        self.on_modified_callback = on_modified
        self.on_deleted_callback = on_deleted
        self.file_patterns = file_patterns or ["*.py", "*.txt", "*.md", "*.json"]
        self.processed_files: Set[str] = set()
        self._processed_lock = threading.Lock()
        self.allowed_base_dir = allowed_base_dir
        
        logger.info(f"文件处理器初始化,监控模式: {self.file_patterns}")
    
    def _should_process(self, file_path: str) -> bool:
        """判断是否应该处理该文件"""
        try:
            path = Path(file_path)
            
            if path.is_symlink():
                logger.warning(f"跳过符号链接: {file_path}")
                return False
            
            resolved = path.resolve()
            
            if self.allowed_base_dir:
                if not resolved.is_relative_to(self.allowed_base_dir.resolve()):
                    logger.warning(f"文件路径越权: {file_path}")
                    return False
            
            if not resolved.is_file():
                return False
            
            for pattern in self.file_patterns:
                if resolved.match(pattern):
                    return True
            
            return False
        except (OSError, RuntimeError) as e:
            logger.warning(f"路径验证失败: {file_path} - {e}")
            return False
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        logger.info(f"检测到新文件: {event.src_path}")
        
        if self.on_created_callback:
            try:
                self.on_created_callback(event.src_path, "created")
            except Exception as e:
                logger.error(f"处理创建事件失败: {e}")
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        file_key = f"{event.src_path}_{int(time.time() / 5)}"
        
        with self._processed_lock:
            if file_key in self.processed_files:
                return
            
            self.processed_files.add(file_key)
            
            if len(self.processed_files) > MAX_PROCESSED_FILES:
                self.processed_files.clear()
        
        logger.info(f"检测到文件修改: {event.src_path}")
        
        if self.on_modified_callback:
            try:
                self.on_modified_callback(event.src_path, "modified")
            except Exception as e:
                logger.error(f"处理修改事件失败: {e}")
    
    def on_deleted(self, event):
        """文件删除事件"""
        if event.is_directory:
            return
        
        logger.info(f"检测到文件删除: {event.src_path}")
        
        if self.on_deleted_callback:
            try:
                self.on_deleted_callback(event.src_path, "deleted")
            except Exception as e:
                logger.error(f"处理删除事件失败: {e}")


class DirectoryMonitor:
    """目录监控器"""
    
    def __init__(self):
        self.observer: Optional[Observer] = None
        self.handlers: Dict[str, FileChangeHandler] = {}
        self.watched_dirs: Dict[str, dict] = {}
        self.auto_process_enabled = config.get("monitor.auto_process", True)
        
        if WATCHDOG_AVAILABLE:
            self.observer = Observer()
            logger.info("目录监控器初始化完成")
        else:
            logger.warning("watchdog不可用,监控功能受限")
    
    def watch_directory(self,
                       directory: str,
                       on_created: Optional[Callable] = None,
                       on_modified: Optional[Callable] = None,
                       on_deleted: Optional[Callable] = None,
                       file_patterns: Optional[List[str]] = None,
                       recursive: bool = True) -> Dict:
        """监控指定目录
        
        Args:
            directory: 要监控的目录路径
            on_created: 文件创建回调
            on_modified: 文件修改回调
            on_deleted: 文件删除回调
            file_patterns: 文件匹配模式
            recursive: 是否递归监控子目录
        """
        if not WATCHDOG_AVAILABLE:
            return {
                "success": False,
                "message": "watchdog未安装,请执行: pip install watchdog"
            }
        
        dir_path = Path(directory).resolve()
        
        allowed_dir = None
        for base_dir in ALLOWED_BASE_DIRS:
            base_resolved = base_dir.resolve()
            if not base_resolved.exists():
                try:
                    base_resolved.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.warning(f"无法创建允许目录 {base_dir}: {e}")
                    continue
            
            if dir_path.is_relative_to(base_resolved) or dir_path == base_resolved:
                allowed_dir = base_resolved
                break
        
        if not allowed_dir:
            logger.error(f"目录不在允许范围内: {directory}")
            return {
                "success": False,
                "message": f"目录不在允许范围内。允许的目录: {[str(d) for d in ALLOWED_BASE_DIRS]}"
            }
        
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建监控目录: {directory}")
            except Exception as e:
                logger.error(f"无法创建目录: {e}")
                return {
                    "success": False,
                    "message": f"无法创建目录: {e}"
                }
        
        handler = FileChangeHandler(
            on_created=on_created,
            on_modified=on_modified,
            on_deleted=on_deleted,
            file_patterns=file_patterns,
            allowed_base_dir=allowed_dir
        )
        
        try:
            self.observer.schedule(handler, str(dir_path), recursive=recursive)
            
            watch_id = f"watch_{len(self.watched_dirs)}"
            self.handlers[watch_id] = handler
            self.watched_dirs[watch_id] = {
                "directory": str(dir_path),
                "recursive": recursive,
                "patterns": file_patterns,
                "start_time": datetime.now().isoformat()
            }
            
            logger.info(f"开始监控目录: {dir_path} (递归={recursive})")
            
            return {
                "success": True,
                "watch_id": watch_id,
                "directory": str(dir_path),
                "message": f"已开始监控 {dir_path}"
            }
        
        except Exception as e:
            logger.error(f"监控目录失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def start(self):
        """启动监控"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog不可用,无法启动监控")
            return False
        
        if not self.watched_dirs:
            logger.warning("未配置监控目录")
            return False
        
        try:
            self.observer.start()
            logger.info("目录监控已启动")
            return True
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return False
    
    def stop(self):
        """停止监控"""
        if not WATCHDOG_AVAILABLE:
            return
        
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5.0)
            
            if self.observer.is_alive():
                logger.warning("观察者线程未在5秒内停止")
            else:
                logger.info("目录监控已停止")
    
    def status(self) -> Dict:
        """获取监控状态"""
        return {
            "available": WATCHDOG_AVAILABLE,
            "running": self.observer.is_alive() if self.observer else False,
            "watched_directories": len(self.watched_dirs),
            "details": self.watched_dirs
        }
    
    def list_watched(self) -> List[Dict]:
        """列出所有监控的目录"""
        return [
            {
                "watch_id": watch_id,
                "directory": info["directory"],
                "recursive": info["recursive"],
                "patterns": info["patterns"],
                "start_time": info["start_time"]
            }
            for watch_id, info in self.watched_dirs.items()
        ]
    
    def unwatch(self, watch_id: str) -> Dict:
        """取消监控"""
        if watch_id not in self.watched_dirs:
            return {
                "success": False,
                "message": f"未找到监控: {watch_id}"
            }
        
        try:
            directory = self.watched_dirs[watch_id]["directory"]
            
            del self.watched_dirs[watch_id]
            del self.handlers[watch_id]
            
            logger.info(f"已取消监控: {directory}")
            
            return {
                "success": True,
                "message": f"已取消监控 {directory}"
            }
        
        except Exception as e:
            logger.error(f"取消监控失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }


directory_monitor = DirectoryMonitor()


def create_default_file_handler(allowed_base_dir: Optional[Path] = None) -> Callable:
    """创建默认文件处理器
    
    Args:
        allowed_base_dir: 允许的基目录（沙盒）
    """
    def handle_file_change(file_path: str, event_type: str):
        """处理文件变化"""
        try:
            resolved = Path(file_path).resolve()
            
            if allowed_base_dir:
                if not resolved.is_relative_to(allowed_base_dir.resolve()):
                    logger.warning(f"文件路径越权，拒绝处理: {file_path}")
                    return
            
            logger.info(f"处理文件{event_type}: {file_path}")
            
            if event_type in ["created", "modified"]:
                from adapters.input.file_adapter import file_adapter
                result = file_adapter.on_file_selected(file_path)
                
                if result.get("success"):
                    logger.info(f"自动处理文件成功: {file_path}")
                    
                    from infrastructure.event_bus import bus
                    bus.publish("file_auto_processed", {
                        "file_path": file_path,
                        "event_type": event_type,
                        "content": result.get("event", {}).get("content", "")
                    })
                else:
                    logger.warning(f"自动处理文件失败: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"文件处理异常: {e}")
    
    return handle_file_change