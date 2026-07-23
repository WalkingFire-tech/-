"""
学习引擎 - 智能学习调度与优先级管理
"""
import sqlite3
import hashlib
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
from loguru import logger
from core.ports.adapters import get_storage_port


class LearningMode(Enum):
    """学习模式"""
    AUTO = "auto"          # 自动学习所有文件
    SMART = "smart"        # 智能学习：根据优先级和文件类型决定
    MANUAL = "manual"      # 手动学习：只学习用户明确指定的文件


class LearningPriority(Enum):
    """学习优先级"""
    HIGH = 1      # 核心业务代码、用户指定文件
    NORMAL = 2    # 普通代码文件
    LOW = 3       # 文档、配置文件


class LearningEngine:
    """学习引擎 - 管理学习任务队列和调度"""
    
    def __init__(self, db_path: str = "data/learning_engine.db"):
        self.db_path = db_path
        self.mode = LearningMode.SMART
        self.task_queue = queue.PriorityQueue()
        self.is_running = False
        self.worker_thread = None
        self.learning_callback = None
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        self.priority_rules = {
            "high": ["main.py", "app.py", "api.py", "core/", "backend/"],
            "low": [".md", ".txt", ".rst", "docs/", "README"],
            "exclude": ["test_", "_test.py", "tests/", "__pycache__"]
        }
        
        logger.info(f"学习引擎已初始化，模式: {self.mode.value}")
    
    def _init_db(self):
        """初始化数据库"""
        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS learning_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                priority INTEGER,
                status TEXT DEFAULT 'pending',
                event_type TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_msg TEXT,
                knowledge_count INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS learning_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_tasks INTEGER,
                completed_tasks INTEGER,
                failed_tasks INTEGER,
                total_knowledge INTEGER
            )
        ''')
    
    def set_mode(self, mode: str) -> Dict:
        """设置学习模式"""
        try:
            self.mode = LearningMode(mode)
            logger.info(f"学习模式切换为: {self.mode.value}")
            
            return {
                "success": True,
                "mode": self.mode.value
            }
        except ValueError:
            return {
                "success": False,
                "error": f"无效的学习模式: {mode}"
            }
    
    def _calculate_priority(self, file_path: str) -> int:
        """计算文件学习优先级"""
        
        path = Path(file_path)
        filename = path.name
        path_str = str(path)
        
        for pattern in self.priority_rules["exclude"]:
            if pattern in filename or pattern in path_str:
                return 999
        
        for pattern in self.priority_rules["high"]:
            if pattern in filename or pattern in path_str:
                return LearningPriority.HIGH.value
        
        for pattern in self.priority_rules["low"]:
            if pattern in filename or pattern in path_str:
                return LearningPriority.LOW.value
        
        return LearningPriority.NORMAL.value
    
    def _should_learn(self, file_path: str) -> bool:
        """判断是否应该学习该文件"""
        
        if self.mode == LearningMode.MANUAL:
            return False
        
        if self.mode == LearningMode.AUTO:
            return True
        
        if self.mode == LearningMode.SMART:
            path = Path(file_path)
            filename = path.name
            
            for pattern in self.priority_rules["exclude"]:
                if pattern in filename or pattern in str(path):
                    return False
            
            return True
        
        return False
    
    def add_task(self, file_path: str, event_type: str = "manual", 
                 force: bool = False) -> Dict:
        """添加学习任务"""
        
        if not force and not self._should_learn(file_path):
            return {
                "success": False,
                "reason": "文件不符合学习条件"
            }
        
        priority = self._calculate_priority(file_path)
        
        db = get_storage_port(self.db_path)
        try:
            db.execute('''
                INSERT INTO learning_tasks
                (file_path, priority, status, event_type, created_at)
                VALUES (?, ?, 'pending', ?, ?)
            ''', (
                file_path,
                priority,
                event_type,
                datetime.now().isoformat()
            ), commit=True)
            
            self.task_queue.put((priority, file_path))
            
            logger.info(f"添加学习任务: {file_path} (优先级={priority})")
            
            return {
                "success": True,
                "file_path": file_path,
                "priority": priority
            }
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "reason": "任务已存在"
            }
    
    def force_learn(self, file_path: str) -> Dict:
        """强制学习文件"""
        return self.add_task(file_path, event_type="force", force=True)
    
    def process_task(self, file_path: str) -> Dict:
        """处理学习任务"""
        
        db = get_storage_port(self.db_path)
        db.execute('''
            UPDATE learning_tasks
            SET status = 'processing', started_at = ?
            WHERE file_path = ?
        ''', (datetime.now().isoformat(), file_path), commit=True)
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            content = path.read_text(encoding='utf-8', errors='ignore')
            
            if not content.strip():
                raise ValueError("文件内容为空")
            
            from core.learning import enhanced_learner
            
            knowledge_count = enhanced_learner.learn_from_file(
                filename=path.name,
                content=content
            )
            
            db = get_storage_port(self.db_path)
            db.execute('''
                UPDATE learning_tasks
                SET status = 'completed', completed_at = ?, 
                    knowledge_count = ?
                WHERE file_path = ?
            ''', (datetime.now().isoformat(), knowledge_count, file_path), commit=True)
            
            logger.info(f"学习完成: {file_path}, 提取{knowledge_count}条知识")
            
            return {
                "success": True,
                "file_path": file_path,
                "knowledge_count": knowledge_count
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"学习失败: {file_path}: {error_msg}")
            
            db = get_storage_port(self.db_path)
            db.execute('''
                UPDATE learning_tasks
                SET status = 'failed', error_msg = ?, 
                    retry_count = retry_count + 1
                WHERE file_path = ?
            ''', (error_msg, file_path), commit=True)
            
            return {
                "success": False,
                "file_path": file_path,
                "error": error_msg
            }
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.is_running:
            try:
                priority, file_path = self.task_queue.get(timeout=1)
                
                self.process_task(file_path)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {e}")
    
    def start(self):
        """启动学习引擎"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("学习引擎已启动")
    
    def stop(self):
        """停止学习引擎"""
        self.is_running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        logger.info("学习引擎已停止")
    
    def get_stats(self) -> Dict:
        """获取学习统计"""
        db = get_storage_port(self.db_path)
        
        row = db.query_one('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(knowledge_count) as total_knowledge
            FROM learning_tasks
        ''')
        
        return {
            "mode": self.mode.value,
            "is_running": self.is_running,
            "total_tasks": row['total'] or 0,
            "pending_tasks": row['pending'] or 0,
            "processing_tasks": row['processing'] or 0,
            "completed_tasks": row['completed'] or 0,
            "failed_tasks": row['failed'] or 0,
            "total_knowledge": row['total_knowledge'] or 0
        }
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        """获取最近的学习任务"""
        db = get_storage_port(self.db_path)
        rows = db.query('''
            SELECT file_path, status, knowledge_count, created_at, completed_at, error_msg
            FROM learning_tasks
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in rows]
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        db = get_storage_port(self.db_path)
        db.execute("DELETE FROM learning_tasks WHERE status = 'completed'", commit=True)
        
        logger.info("已清理完成的学习任务")


learning_engine = LearningEngine()
