"""
文件监听器 - 基于watchdog实现实时文件变化监听
"""
import time
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Callable, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
from loguru import logger


class LearningFileHandler(FileSystemEventHandler):
    """文件变化事件处理器"""
    
    def __init__(self, callback: Callable = None, 
                 supported_extensions: set = None,
                 ignored_dirs: set = None):
        self.callback = callback
        self.supported_extensions = supported_extensions or {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml',
            '.csv', '.rst', '.js', '.ts', '.html', '.css'
        }
        self.ignored_dirs = ignored_dirs or {
            '__pycache__', 'node_modules', '.git', '.svn',
            'venv', 'env', '.venv', '.env', 'dist', 'build'
        }
        self.learning_queue = []
        self.last_learning_time = {}
        self.debounce_seconds = 2
    
    def _should_process(self, path: str) -> bool:
        """判断是否应该处理该文件"""
        file_path = Path(path)
        
        if not file_path.is_file():
            return False
        
        if file_path.suffix.lower() not in self.supported_extensions:
            return False
        
        if any(ignored in file_path.parts for ignored in self.ignored_dirs):
            return False
        
        return True
    
    def _debounce(self, path: str) -> bool:
        """防抖：避免短时间内重复处理同一文件"""
        now = time.time()
        last_time = self.last_learning_time.get(path, 0)
        
        if now - last_time < self.debounce_seconds:
            return False
        
        self.last_learning_time[path] = now
        return True
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        if not self._debounce(event.src_path):
            return
        
        logger.info(f"检测到文件修改: {event.src_path}")
        
        if self.callback:
            self.callback(event.src_path, "modified")
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        if not self._debounce(event.src_path):
            return
        
        logger.info(f"检测到新文件: {event.src_path}")
        
        if self.callback:
            self.callback(event.src_path, "created")
    
    def on_deleted(self, event):
        """文件删除事件"""
        if event.is_directory:
            return
        
        logger.info(f"检测到文件删除: {event.src_path}")
        
        if self.callback:
            self.callback(event.src_path, "deleted")


class FileMonitor:
    """文件监听管理器"""
    
    def __init__(self):
        self.observers = {}
        self.handlers = {}
        self.watched_paths = {}
        self.is_running = False
        self.learning_callback = None
        
        logger.info("文件监听器已初始化")
    
    def set_learning_callback(self, callback: Callable):
        """设置学习回调函数"""
        self.learning_callback = callback
    
    def add_watch_path(self, path: str, recursive: bool = True, 
                       priority: str = "normal") -> Dict:
        """添加监听路径"""
        
        watch_path = Path(path).resolve()
        
        if not watch_path.exists():
            return {
                "success": False,
                "error": f"路径不存在: {path}"
            }
        
        if not watch_path.is_dir():
            return {
                "success": False,
                "error": f"不是文件夹: {path}"
            }
        
        path_str = str(watch_path)
        
        if path_str in self.observers:
            return {
                "success": False,
                "error": f"路径已在监听中: {path}"
            }
        
        handler = LearningFileHandler(callback=self._handle_file_change)
        
        observer = Observer()
        observer.schedule(handler, path_str, recursive=recursive)
        observer.start()
        
        self.observers[path_str] = observer
        self.handlers[path_str] = handler
        self.watched_paths[path_str] = {
            "path": path_str,
            "recursive": recursive,
            "priority": priority,
            "added_at": datetime.now().isoformat(),
            "files_count": self._count_files(watch_path)
        }
        
        logger.info(f"添加监听路径: {path_str} (递归={recursive}, 优先级={priority})")
        
        return {
            "success": True,
            "path": path_str,
            "files_count": self.watched_paths[path_str]["files_count"]
        }
    
    def remove_watch_path(self, path: str) -> Dict:
        """移除监听路径"""
        
        watch_path = str(Path(path).resolve())
        
        if watch_path not in self.observers:
            return {
                "success": False,
                "error": f"路径未在监听中: {path}"
            }
        
        observer = self.observers[watch_path]
        observer.stop()
        observer.join(timeout=5)
        
        del self.observers[watch_path]
        del self.handlers[watch_path]
        del self.watched_paths[watch_path]
        
        logger.info(f"移除监听路径: {watch_path}")
        
        return {
            "success": True,
            "path": watch_path
        }
    
    def _handle_file_change(self, file_path: str, event_type: str):
        """处理文件变化"""
        
        if event_type == "deleted":
            logger.info(f"文件已删除，跳过学习: {file_path}")
            return
        
        if self.learning_callback:
            try:
                # 传递环境触发器（文件路径）
                self.learning_callback(file_path, event_type, environmental_triggers=file_path)
            except Exception as e:
                logger.error(f"学习回调失败: {e}")
    
    def _count_files(self, path: Path) -> int:
        """统计文件数量"""
        count = 0
        supported_extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml',
            '.csv', '.rst', '.js', '.ts', '.html', '.css'
        }
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                count += 1
        
        return count
    
    def get_status(self) -> Dict:
        """获取监听状态"""
        return {
            "is_running": len(self.observers) > 0,
            "watched_paths": list(self.watched_paths.values()),
            "total_paths": len(self.observers)
        }
    
    def stop_all(self):
        """停止所有监听"""
        for path, observer in list(self.observers.items()):
            try:
                observer.stop()
                observer.join(timeout=5)
            except Exception as e:
                logger.error(f"停止监听失败 {path}: {e}")
        
        self.observers.clear()
        self.handlers.clear()
        
        logger.info("所有文件监听已停止")
    
    def pause(self):
        """暂停监听"""
        for observer in self.observers.values():
            observer.pause()
        
        self.is_running = False
        logger.info("文件监听已暂停")
    
    def resume(self):
        """恢复监听"""
        for observer in self.observers.values():
            observer.resume()
        
        self.is_running = True
        logger.info("文件监听已恢复")


file_monitor = FileMonitor()