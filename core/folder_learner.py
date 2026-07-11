"""
文件夹学习管理器 - 优化版

核心设计：
1. 策略模式：不同文件类型使用不同提取策略
2. 二阶段学习：先扫描变更，再批量学习
3. 依赖注入：学习器通过构造函数注入
4. 状态快照：内存缓存 + SQLite，提高查询效率
"""

import os
import hashlib
import json
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from loguru import logger
from infrastructure.database_manager import DatabaseManager

try:
    from core.content_extractors import (
        ContentExtractor,
        TextExtractor,
        CodeExtractor,
        PDFExtractor,
        DocxExtractor,
        get_default_extractors
    )
    CONTENT_EXTRACTORS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"内容提取器模块加载失败: {e}，将使用内置提取器")
    CONTENT_EXTRACTORS_AVAILABLE = False
    
    class ContentExtractor(ABC):
        @abstractmethod
        def extract(self, file_path: Path) -> Optional[str]:
            pass
        
        @abstractmethod
        def supports(self, file_path: Path) -> bool:
            pass


if not CONTENT_EXTRACTORS_AVAILABLE:
    class TextExtractor(ContentExtractor):
        def __init__(self, max_size_mb: int = 10):
            self.max_size_mb = max_size_mb
        
        def supports(self, file_path: Path) -> bool:
            text_extensions = {
                '.py', '.md', '.txt', '.json', '.yaml', '.yml',
                '.rst', '.js', '.html', '.css', '.ts', '.jsx', '.tsx',
                '.xml', '.ini', '.cfg', '.toml', '.sh', '.bat',
                '.csv', '.log', '.env', '.gitignore'
            }
            return file_path.suffix.lower() in text_extensions
        
        def extract(self, file_path: Path) -> Optional[str]:
            try:
                file_size = file_path.stat().st_size
                if file_size > self.max_size_mb * 1024 * 1024:
                    return None
                return file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                return None


    class PDFExtractor(ContentExtractor):
        def __init__(self):
            self._available = False
            try:
                import fitz
                self._fitz = fitz
                self._available = True
            except ImportError:
                pass
        
        def supports(self, file_path: Path) -> bool:
            return file_path.suffix.lower() == '.pdf' and self._available
        
        def extract(self, file_path: Path) -> Optional[str]:
            if not self._available:
                return None
            try:
                doc = self._fitz.open(str(file_path))
                text_parts = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    if text:
                        text_parts.append(text)
                doc.close()
                return "\n".join(text_parts) if text_parts else None
            except Exception:
                return None


    class DocxExtractor(ContentExtractor):
        def __init__(self):
            self._available = False
            try:
                import docx
                self._docx = docx
                self._available = True
            except ImportError:
                pass
        
        def supports(self, file_path: Path) -> bool:
            return file_path.suffix.lower() in ('.docx', '.doc') and self._available
        
        def extract(self, file_path: Path) -> Optional[str]:
            if not self._available:
                return None
            try:
                doc = self._docx.Document(str(file_path))
                text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
                return "\n".join(text_parts) if text_parts else None
            except Exception:
                return None


    class CodeExtractor(ContentExtractor):
        def supports(self, file_path: Path) -> bool:
            code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp', '.h'}
            return file_path.suffix.lower() in code_extensions
        
        def extract(self, file_path: Path) -> Optional[str]:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                import re
                lines = content.split('\n')
                extracted = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if re.match(r'^(def|class|import|from)\s', line):
                        extracted.append(line)
                    elif re.match(r'^(function|class|export|import|const\s+\w+\s*=\s*\(?.*\)?\s*=>?)', line):
                        extracted.append(line)
                    elif line.startswith('#') or line.startswith('//') or line.startswith('/*'):
                        if len(extracted) < 20:
                            extracted.append(line)
                return "\n".join(extracted) if extracted else None
            except Exception:
                return None


    class FallbackExtractor(ContentExtractor):
        def supports(self, file_path: Path) -> bool:
            return True
        
        def extract(self, file_path: Path) -> Optional[str]:
            try:
                return file_path.read_text(encoding='utf-8', errors='ignore')[:10000]
            except Exception:
                return None


    def get_default_extractors():
        return [
            CodeExtractor(),
            PDFExtractor(),
            DocxExtractor(),
            TextExtractor(),
            FallbackExtractor(),
        ]


class FolderLearner:
    """
    文件夹学习管理器 - 优化版
    
    改进点：
    1. 策略模式：使用多个 ContentExtractor
    2. 依赖注入：learning_engine 可配置
    3. 批次学习：减少数据库写入次数
    4. 状态快照：加快变更检测
    """
    
    SUPPORTED_EXTENSIONS = {
        '.py', '.md', '.txt', '.json', '.yaml', '.yml', 
        '.csv', '.rst', '.js', '.html', '.css', '.ts',
        '.xml', '.ini', '.cfg', '.toml', '.sh', '.bat',
        '.pdf', '.docx', '.doc', '.xlsx', '.xls',
        '.jsx', '.tsx', '.log', '.env', '.gitignore',
        '.java', '.go', '.rs', '.c', '.cpp', '.h'
    }
    
    IGNORED_DIRS = {
        '__pycache__', 'node_modules', '.git', '.svn',
        'venv', 'env', '.venv', '.env', 'dist', 'build'
    }
    
    def __init__(
        self,
        root_path: str = None,
        state_db: str = "data/folder_learning.db",
        knowledge_db: str = "data/knowledge_store.db",
        learning_engine: Any = None,
        batch_size: int = 50,
        max_file_size_mb: int = 50,
        extractors: List[ContentExtractor] = None
    ):
        self.root_path = Path(root_path).resolve() if root_path else None
        self.state_db = state_db
        self.knowledge_db = knowledge_db
        self.batch_size = batch_size
        self.max_file_size_mb = max_file_size_mb
        
        self.learning_engine = learning_engine
        if self.learning_engine is None:
            try:
                from core.learning import enhanced_learner
                self.learning_engine = enhanced_learner
            except ImportError:
                logger.warning("enhanced_learner 未找到，将使用基础学习")
                self.learning_engine = None
        
        self.extractors = extractors or get_default_extractors()
        
        self.is_running = False
        self.thread = None
        self.pending_notifications = []
        self._snapshot_cache: Dict[str, str] = {}
        
        Path(state_db).parent.mkdir(parents=True, exist_ok=True)
        Path(knowledge_db).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_snapshot()
        
        logger.info(f"文件夹学习器已初始化: {root_path or '未设置'}")
    
    def _init_db(self):
        """初始化数据库"""
        db = DatabaseManager.get(self.state_db)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS learned_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_path TEXT,
                file_path TEXT,
                relative_path TEXT,
                file_hash TEXT,
                file_size INTEGER,
                last_modified REAL,
                last_learned TEXT,
                status TEXT DEFAULT 'pending',
                error_msg TEXT,
                knowledge_count INTEGER DEFAULT 0,
                extracted_preview TEXT,
                created_at TEXT,
                updated_at TEXT
            );

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
            );

            CREATE INDEX IF NOT EXISTS idx_file_path ON learned_files(file_path);
            CREATE INDEX IF NOT EXISTS idx_root_path ON learned_files(root_path);
            CREATE INDEX IF NOT EXISTS idx_status ON learned_files(status)
        ''')
    
    def _load_snapshot(self):
        """加载快照到内存缓存"""
        if not self.root_path:
            return
        
        try:
            db = DatabaseManager.get(self.state_db)
            rows = db.query('''
                SELECT relative_path, file_hash
                FROM learned_files
                WHERE root_path = ? AND status = 'success'
            ''', (str(self.root_path),))
            
            self._snapshot_cache = {
                row['relative_path']: row['file_hash']
                for row in rows
            }
            
            logger.debug(f"加载快照: {len(self._snapshot_cache)} 个文件")
        except Exception as e:
            logger.error(f"加载快照失败: {e}")
    
    def set_root_path(self, root_path: str) -> Dict:
        """设置学习根目录"""
        new_root = Path(root_path).resolve()
        
        if not new_root.exists():
            return {"success": False, "error": f"路径不存在: {root_path}"}
        if not new_root.is_dir():
            return {"success": False, "error": f"不是文件夹: {root_path}"}
        
        self.root_path = new_root
        self._load_snapshot()
        
        logger.info(f"设置学习根目录: {self.root_path}")
        return {"success": True, "root_path": str(self.root_path)}
    
    def _get_extractor(self, file_path: Path) -> Optional[ContentExtractor]:
        """选择合适的提取器"""
        for extractor in self.extractors:
            if extractor.supports(file_path):
                return extractor
        return None
    
    def _extract_content(self, file_path: Path) -> Optional[str]:
        """提取文件内容"""
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size_mb * 1024 * 1024:
                logger.debug(f"文件过大，跳过: {file_path}")
                return None
        except Exception:
            return None
        
        extractor = self._get_extractor(file_path)
        if not extractor:
            logger.debug(f"无合适的提取器: {file_path}")
            return None
        
        return extractor.extract(file_path)
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件哈希（使用 MD5，更快）"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logger.debug(f"哈希计算失败 {file_path}: {e}")
            return ""
    
    def _get_file_info(self, file_path: Path) -> Dict:
        """获取文件信息"""
        try:
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "hash": self._compute_file_hash(file_path)
            }
        except Exception as e:
            logger.debug(f"获取文件信息失败 {file_path}: {e}")
            return {"size": 0, "modified": 0, "hash": ""}
    
    def _should_learn(self, file_path: Path) -> tuple:
        """判断是否需要学习"""
        if not self.root_path:
            return False, "no_root_path"
        
        try:
            rel_path = str(file_path.relative_to(self.root_path))
        except ValueError:
            return False, "not_in_root"
        
        info = self._get_file_info(file_path)
        if not info["hash"]:
            return False, "hash_failed"
        
        cached_hash = self._snapshot_cache.get(rel_path)
        
        if cached_hash is None:
            return True, "new_file"
        
        if cached_hash != info["hash"]:
            return True, "changed"
        
        return False, "already_learned"
    
    def learn_single_file(self, file_path: Path, force: bool = False) -> Dict:
        """学习单个文件"""
        if not self.root_path:
            return {"status": "failed", "error": "未设置学习根目录"}
        
        try:
            rel_path = str(file_path.relative_to(self.root_path))
        except ValueError:
            return {"status": "failed", "error": "文件不在根目录下"}
        
        info = self._get_file_info(file_path)
        if not info["hash"]:
            return {"status": "failed", "error": "无法计算文件哈希"}
        
        if not force:
            cached_hash = self._snapshot_cache.get(rel_path)
            if cached_hash and cached_hash == info["hash"]:
                return {"status": "skipped", "path": rel_path, "reason": "already_learned"}
        
        content = self._extract_content(file_path)
        if content is None or not content.strip():
            self._save_file_state(rel_path, file_path, info, 'skipped', "无有效内容")
            return {"status": "skipped", "path": rel_path, "reason": "empty_or_binary"}
        
        knowledge_count = self._learn_content(file_path.name, content)
        
        self._save_file_state(rel_path, file_path, info, 'success', None, knowledge_count, content[:500])
        
        self._snapshot_cache[rel_path] = info["hash"]
        
        logger.debug(f"学习成功: {rel_path}, 提取{knowledge_count}条知识")
        
        return {
            "status": "success",
            "path": rel_path,
            "knowledge_count": knowledge_count
        }
    
    def _learn_content(self, filename: str, content: str) -> int:
        """学习文件内容（使用学习引擎）"""
        if self.learning_engine is None:
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            return len(lines) // 10 + 1
        
        try:
            if hasattr(self.learning_engine, 'learn_from_file'):
                result = self.learning_engine.learn_from_file(
                    filename=filename,
                    content=content
                )
                return result if isinstance(result, int) else 0
            else:
                return self._basic_learn(content)
        except Exception as e:
            logger.debug(f"学习引擎失败: {e}")
            return self._basic_learn(content)
    
    def _basic_learn(self, content: str) -> int:
        """基础学习（降级方案）"""
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        return len(lines) // 20 + 1
    
    def _save_file_state(self, rel_path: str, file_path: Path, info: Dict,
                         status: str, error_msg: str = None,
                         knowledge_count: int = 0, preview: str = None):
        """保存文件学习状态"""
        db = DatabaseManager.get(self.state_db)
        db.execute('''
            INSERT OR REPLACE INTO learned_files
            (root_path, file_path, relative_path, file_hash, file_size,
             last_modified, last_learned, status, error_msg, knowledge_count,
             extracted_preview, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(self.root_path),
            str(file_path),
            rel_path,
            info["hash"],
            info["size"],
            info["modified"],
            datetime.now().isoformat(),
            status,
            error_msg,
            knowledge_count,
            preview[:500] if preview else None,
            datetime.now().isoformat()
        ), commit=True)
    
    def scan_and_learn(self, progress_callback: Callable = None) -> Dict:
        """扫描文件夹并学习所有文件"""
        if not self.root_path:
            return {"success": False, "error": "未设置学习根目录"}
        
        session_start = datetime.now().isoformat()
        results = {
            "new": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "knowledge_total": 0
        }
        
        logger.info(f"开始扫描文件夹: {self.root_path}")
        
        pending_files = []
        
        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            if any(ignored in file_path.parts for ignored in self.IGNORED_DIRS):
                continue
            
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue
            
            results["total"] += 1
            should_learn, reason = self._should_learn(file_path)
            
            if should_learn:
                pending_files.append((file_path, reason))
            else:
                results["skipped"] += 1
        
        logger.info(f"待学习文件: {len(pending_files)} 个")
        
        for i in range(0, len(pending_files), self.batch_size):
            batch = pending_files[i:i + self.batch_size]
            
            for file_path, reason in batch:
                outcome = self.learn_single_file(file_path)
                
                if outcome["status"] == "success":
                    if reason == "new_file":
                        results["new"] += 1
                    else:
                        results["updated"] += 1
                    results["knowledge_total"] += outcome.get("knowledge_count", 0)
                elif outcome["status"] == "failed":
                    results["failed"] += 1
                else:
                    results["skipped"] += 1
                
                if progress_callback:
                    progress_callback(file_path, outcome)
        
        session_end = datetime.now().isoformat()
        self._record_session(session_start, session_end, results)
        
        if results["new"] > 0 or results["updated"] > 0:
            self.pending_notifications.append({
                "timestamp": datetime.now().isoformat(),
                "new": results["new"],
                "updated": results["updated"],
                "failed": results["failed"],
                "total": results["total"],
                "knowledge": results["knowledge_total"]
            })
        
        logger.info(
            f"扫描完成: 新增{results['new']}, 更新{results['updated']}, "
            f"失败{results['failed']}, 知识{results['knowledge_total']}条"
        )
        
        return {"success": True, **results}
    
    def _record_session(self, start: str, end: str, results: Dict):
        """记录学习会话"""
        db = DatabaseManager.get(self.state_db)
        status = 'completed' if results["failed"] == 0 else 'completed_with_errors'
        db.execute('''
            INSERT INTO learning_sessions
            (root_path, session_start, session_end, total_files,
             new_files, updated_files, failed_files, skipped_files, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(self.root_path),
            start,
            end,
            results["total"],
            results["new"],
            results["updated"],
            results["failed"],
            results["skipped"],
            status
        ), commit=True)
    
    def start_background_monitor(self, interval_seconds: int = 300):
        """启动后台监控"""
        if not self.root_path:
            logger.warning("未设置学习根目录，后台监控无法启动")
            return
        
        if not self.root_path.exists():
            logger.warning(f"学习根目录不存在: {self.root_path}，后台监控无法启动")
            return
        
        if self.is_running:
            logger.warning("后台监控已在运行")
            return
        
        def monitor_loop():
            self.is_running = True
            logger.info(f"启动后台监控，间隔{interval_seconds}秒")
            
            while self.is_running:
                try:
                    if self.root_path and self.root_path.exists():
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
            return {"root_path": None, "total_files": 0}
        
        db = DatabaseManager.get(self.state_db)
        row = db.query_one('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(knowledge_count) as total_knowledge,
                MAX(last_learned) as last_scan
            FROM learned_files
            WHERE root_path = ?
        ''', (str(self.root_path),))
        
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
        
        db = DatabaseManager.get(self.state_db)
        rows = db.query('''
            SELECT relative_path, error_msg, last_learned
            FROM learned_files
            WHERE root_path = ? AND status = 'failed'
            ORDER BY last_learned DESC
        ''', (str(self.root_path),))
        
        return [dict(row) for row in rows]
    
    def get_recent_learned(self, limit: int = 10) -> List[Dict]:
        """获取最近学习的文件"""
        if not self.root_path:
            return []
        
        db = DatabaseManager.get(self.state_db)
        rows = db.query('''
            SELECT relative_path, knowledge_count, last_learned, status
            FROM learned_files
            WHERE root_path = ?
            ORDER BY last_learned DESC
            LIMIT ?
        ''', (str(self.root_path), limit))
        
        return [dict(row) for row in rows]
    
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
            "pending_notifications": len(self.pending_notifications),
            "snapshot_size": len(self._snapshot_cache)
        }


folder_learner = FolderLearner()
