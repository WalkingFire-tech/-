"""
文件夹学习管理器 - 自动扫描、学习、监听文件变化
"""
import os
import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
import threading
import time
from loguru import logger


class FolderLearner:
    """管理一个根文件夹，自动学习所有文件"""
    
    SUPPORTED_EXTENSIONS = {
        '.py', '.md', '.txt', '.json', '.yaml', '.yml', 
        '.csv', '.rst', '.js', '.html', '.css', '.ts',
        '.xml', '.ini', '.cfg', '.toml', '.sh', '.bat'
    }
    
    IGNORED_DIRS = {
        '__pycache__', 'node_modules', '.git', '.svn',
        'venv', 'env', '.venv', '.env', 'dist', 'build'
    }
    
    def __init__(self, root_path: str = None, 
                 state_db: str = "data/folder_learning.db",
                 knowledge_db: str = "data/knowledge_store.db"):
        self.root_path = Path(root_path).resolve() if root_path else None
        self.state_db = state_db
        self.knowledge_db = knowledge_db
        self.is_running = False
        self.thread = None
        self.pending_notifications = []
        
        Path(state_db).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        logger.info(f"文件夹学习器已初始化: {root_path or '未设置'}")
    
    def _init_db(self):
        """初始化状态数据库"""
        with sqlite3.connect(self.state_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learned_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_path TEXT,
                    file_path TEXT,
                    relative_path TEXT,
                    file_hash TEXT,
                    file_size INTEGER,
                    last_learned TEXT,
                    status TEXT DEFAULT 'pending',
                    error_msg TEXT,
                    knowledge_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_path TEXT,
                    session_start TEXT,
                    session_end TEXT,
                    total_files INTEGER,
                    new_files INTEGER,
                    updated_files INTEGER,
                    failed_files INTEGER,
                    skipped_files INTEGER,
                    status TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_path ON learned_files(file_path)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_root_path ON learned_files(root_path)
            ''')
            
            conn.commit()
    
    def set_root_path(self, root_path: str) -> Dict:
        """设置学习根目录"""
        self.root_path = Path(root_path).resolve()
        
        if not self.root_path.exists():
            return {
                "success": False,
                "error": f"路径不存在: {root_path}"
            }
        
        if not self.root_path.is_dir():
            return {
                "success": False,
                "error": f"不是文件夹: {root_path}"
            }
        
        logger.info(f"设置学习根目录: {self.root_path}")
        
        return {
            "success": True,
            "root_path": str(self.root_path)
        }
    
    def _file_hash(self, file_path: Path) -> str:
        """计算文件内容哈希"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算哈希失败: {file_path}: {e}")
            return ""
    
    def _should_learn(self, file_path: Path) -> tuple:
        """判断是否需要学习"""
        if not self.root_path:
            return False, "no_root_path"
        
        try:
            rel_path = str(file_path.relative_to(self.root_path))
        except ValueError:
            return False, "not_in_root"
        
        current_hash = self._file_hash(file_path)
        if not current_hash:
            return False, "hash_failed"
        
        with sqlite3.connect(self.state_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT file_hash, status FROM learned_files
                WHERE root_path = ? AND relative_path = ?
            ''', (str(self.root_path), rel_path))
            
            row = cursor.fetchone()
            
            if not row:
                return True, "new_file"
            
            if row['file_hash'] != current_hash:
                return True, "changed"
            
            if row['status'] != 'success':
                return True, "previous_failed"
            
            return False, "already_learned"
    
    def learn_single_file(self, file_path: Path, force: bool = False) -> Dict:
        """学习单个文件"""
        if not self.root_path:
            return {"status": "failed", "error": "未设置学习根目录"}
        
        try:
            rel_path = str(file_path.relative_to(self.root_path))
        except ValueError:
            return {"status": "failed", "error": "文件不在根目录下"}
        
        current_hash = self._file_hash(file_path)
        file_size = file_path.stat().st_size
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            if not content.strip():
                return {"status": "skipped", "reason": "empty_file"}
            
            from core.learning import enhanced_learner
            
            knowledge_count = enhanced_learner.learn_from_file(
                filename=file_path.name,
                content=content
            )
            
            with sqlite3.connect(self.state_db) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO learned_files
                    (root_path, file_path, relative_path, file_hash, file_size,
                     last_learned, status, error_msg, knowledge_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(self.root_path),
                    str(file_path),
                    rel_path,
                    current_hash,
                    file_size,
                    datetime.now().isoformat(),
                    'success',
                    None,
                    knowledge_count,
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            logger.info(f"学习成功: {rel_path}, 提取{knowledge_count}条知识")
            
            return {
                "status": "success",
                "path": rel_path,
                "knowledge_count": knowledge_count
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"学习失败: {rel_path}: {error_msg}")
            
            with sqlite3.connect(self.state_db) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO learned_files
                    (root_path, file_path, relative_path, file_hash, file_size,
                     last_learned, status, error_msg, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(self.root_path),
                    str(file_path),
                    rel_path,
                    current_hash,
                    file_size,
                    datetime.now().isoformat(),
                    'failed',
                    error_msg,
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            return {
                "status": "failed",
                "path": rel_path,
                "error": error_msg
            }
    
    def scan_and_learn(self, progress_callback: Callable = None) -> Dict:
        """扫描文件夹并学习所有文件"""
        if not self.root_path:
            return {
                "success": False,
                "error": "未设置学习根目录"
            }
        
        session_start = datetime.now().isoformat()
        results = {
            "new": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0
        }
        
        logger.info(f"开始扫描文件夹: {self.root_path}")
        
        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            if any(ignored in file_path.parts for ignored in self.IGNORED_DIRS):
                continue
            
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue
            
            results["total"] += 1
            
            should_learn, reason = self._should_learn(file_path)
            
            if not should_learn:
                results["skipped"] += 1
                continue
            
            outcome = self.learn_single_file(file_path)
            
            if outcome["status"] == "success":
                if reason == "new_file":
                    results["new"] += 1
                else:
                    results["updated"] += 1
            elif outcome["status"] == "failed":
                results["failed"] += 1
            else:
                results["skipped"] += 1
            
            if progress_callback:
                progress_callback(file_path, outcome)
        
        session_end = datetime.now().isoformat()
        
        with sqlite3.connect(self.state_db) as conn:
            conn.execute('''
                INSERT INTO learning_sessions
                (root_path, session_start, session_end, total_files, new_files,
                 updated_files, failed_files, skipped_files, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(self.root_path),
                session_start,
                session_end,
                results["total"],
                results["new"],
                results["updated"],
                results["failed"],
                results["skipped"],
                'completed'
            ))
            conn.commit()
        
        if results["new"] > 0 or results["updated"] > 0:
            self.pending_notifications.append({
                "timestamp": datetime.now().isoformat(),
                "new": results["new"],
                "updated": results["updated"],
                "failed": results["failed"],
                "total": results["total"]
            })
        
        logger.info(f"扫描完成: 新增{results['new']}, 更新{results['updated']}, 失败{results['failed']}")
        
        return {
            "success": True,
            **results
        }
    
    def start_background_monitor(self, interval_seconds: int = 300):
        """启动后台监控"""
        if self.is_running:
            logger.warning("后台监控已在运行")
            return
        
        def monitor_loop():
            self.is_running = True
            logger.info(f"启动后台监控，间隔{interval_seconds}秒")
            
            while self.is_running:
                try:
                    if self.root_path:
                        self.scan_and_learn()
                except Exception as e:
                    logger.error(f"后台学习失败: {e}")
                
                for _ in range(interval_seconds):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        self.thread = threading.Thread(target=monitor_loop, daemon=True)
        self.thread.start()
    
    def stop_monitor(self):
        """停止后台监控"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("后台监控已停止")
    
    def get_summary(self) -> Dict:
        """获取学习状态摘要"""
        if not self.root_path:
            return {
                "root_path": None,
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "total_knowledge": 0,
                "last_scan": None
            }
        
        with sqlite3.connect(self.state_db) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                       SUM(knowledge_count) as total_knowledge,
                       MAX(last_learned) as last_scan
                FROM learned_files
                WHERE root_path = ?
            ''', (str(self.root_path),))
            
            row = cursor.fetchone()
            
            return {
                "root_path": str(self.root_path),
                "total_files": row['total'] or 0,
                "successful": row['successful'] or 0,
                "failed": row['failed'] or 0,
                "total_knowledge": row['total_knowledge'] or 0,
                "last_scan": row['last_scan']
            }
    
    def get_failed_files(self) -> List[Dict]:
        """获取失败的文件列表"""
        if not self.root_path:
            return []
        
        with sqlite3.connect(self.state_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT relative_path, error_msg, last_learned
                FROM learned_files
                WHERE root_path = ? AND status = 'failed'
                ORDER BY last_learned DESC
            ''', (str(self.root_path),))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_learned(self, limit: int = 10) -> List[Dict]:
        """获取最近学习的文件"""
        if not self.root_path:
            return []
        
        with sqlite3.connect(self.state_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT relative_path, knowledge_count, last_learned, status
                FROM learned_files
                WHERE root_path = ?
                ORDER BY last_learned DESC
                LIMIT ?
            ''', (str(self.root_path), limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def pop_notifications(self) -> List[Dict]:
        """取出并清空未读通知"""
        notifs = self.pending_notifications[:]
        self.pending_notifications.clear()
        return notifs
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "running": self.is_running,
            "root_path": str(self.root_path) if self.root_path else None,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "pending_notifications": len(self.pending_notifications)
        }


folder_learner = FolderLearner()