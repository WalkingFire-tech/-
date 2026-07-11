"""
记忆系统 - 安全优化版本
使用SQLite实现原子写入和并发安全
"""
import threading
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


class MemoryEntry:
    """记忆条目"""
    def __init__(self, timestamp: str, role: str, content: str):
        self.timestamp = timestamp
        self.role = role
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "role": self.role,
            "content": self.content
        }
    
    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.role}: {self.content}"


class CampfireLogger:
    """营火记忆系统 - SQLite实现"""
    
    MAX_ENTRIES = 10000
    MAX_CONTENT_LEN = 5000
    
    def __init__(self, log_file: str = None):
        filename = log_file or config.get("memory.short_term.file_path", "campfire_log.db")
        filename = Path(filename).name
        if not filename.endswith('.db'):
            filename = filename.rsplit('.', 1)[0] + '.db'
        
        self.log_file = str(Path("logs") / filename)
        self.log_file_dir = Path("logs")
        self.log_file_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_rounds = config.get("memory.short_term.max_rounds", 5)
        self._lock = threading.Lock()
        
        self._init_db()
        logger.info(f"营火记忆系统已初始化: {self.log_file}")
    
    def _init_db(self):
        db = DatabaseManager.get(self.log_file)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                role TEXT,
                content TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_entries(timestamp);
            CREATE INDEX IF NOT EXISTS idx_role ON memory_entries(role);
        ''')
    
    def log_user(self, message: str):
        """记录用户消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = str(message)[:self.MAX_CONTENT_LEN]
        
        with self._lock:
            db = DatabaseManager.get(self.log_file)
            db.execute('''
                INSERT INTO memory_entries (timestamp, role, content)
                VALUES (?, '用户', ?)
            ''', (timestamp, content), commit=True)
            
            self._cleanup_if_needed()
    
    def log_assistant(self, message: str):
        """记录助手消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = str(message)[:self.MAX_CONTENT_LEN]
        
        with self._lock:
            db = DatabaseManager.get(self.log_file)
            db.execute('''
                INSERT INTO memory_entries (timestamp, role, content)
                VALUES (?, '拓荒者', ?)
            ''', (timestamp, content), commit=True)
            
            self._cleanup_if_needed()
    
    def _cleanup_if_needed(self):
        row = DatabaseManager.get(self.log_file).query_one('SELECT COUNT(*) FROM memory_entries')
        count = row[0] if row else 0
        
        if count > self.MAX_ENTRIES:
            DatabaseManager.get(self.log_file).execute('''
                DELETE FROM memory_entries 
                WHERE id IN (
                    SELECT id FROM memory_entries 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
            ''', (count - self.MAX_ENTRIES,), commit=True)
    
    def _parse_all_entries(self) -> List[MemoryEntry]:
        """解析所有记忆条目"""
        entries = []
        
        db = DatabaseManager.get(self.log_file)
        rows = db.query('''
            SELECT timestamp, role, content
            FROM memory_entries
            ORDER BY timestamp ASC
        ''')
        
        return [MemoryEntry(row[0], row[1], row[2]) for row in rows]
    
    def get_recent_context(self, rounds: int = None) -> str:
        if rounds is None:
            rounds = self.max_rounds
        
        db = DatabaseManager.get(self.log_file)
        rows = list(db.query('''
            SELECT role, content
            FROM memory_entries
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (rounds * 2,)))
        
        rows.reverse()
        
        context_lines = [f"{row[0]}: {row[1]}" for row in rows]
        return "\n".join(context_lines)
    
    def get_conversation_summary(self, rounds: int = 3) -> str:
        db = DatabaseManager.get(self.log_file)
        rows = list(db.query('''
            SELECT role, content
            FROM memory_entries
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (rounds * 2,)))
        
        rows.reverse()
        
        if not rows:
            return "我们还没有开始对话。"
        
        summary_parts = []
        for role, content in rows:
            if role == "用户":
                summary_parts.append(f"用户问了: {content[:50]}...")
            else:
                summary_parts.append(f"拓荒者回答了相关内容")
        
        return "、".join(summary_parts[-3:])
    
    def search_memory(self, keyword: str, limit: int = 5) -> List[MemoryEntry]:
        db = DatabaseManager.get(self.log_file)
        rows = db.query('''
            SELECT timestamp, role, content
            FROM memory_entries
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{keyword}%', limit))
        
        return [MemoryEntry(row[0], row[1], row[2]) for row in rows]
    
    def get_user_info(self) -> Dict[str, str]:
        user_info = {}
        
        db = DatabaseManager.get(self.log_file)
        rows = db.query('''
            SELECT content
            FROM memory_entries
            WHERE role = '用户'
            ORDER BY timestamp ASC
        ''')
        
        for row in rows:
            content = row[0]
            name_match = re.search(r'我[叫是](.+?)(?:[,.。!!\s]|$)', content)
            if name_match:
                user_info["name"] = name_match.group(1).strip()
                break
        
        return user_info
    
    def get_last_user_message(self) -> Optional[str]:
        db = DatabaseManager.get(self.log_file)
        row = db.query_one('''
            SELECT content
            FROM memory_entries
            WHERE role = '用户'
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        return row[0] if row else None
    
    def get_last_assistant_message(self) -> Optional[str]:
        db = DatabaseManager.get(self.log_file)
        row = db.query_one('''
            SELECT content
            FROM memory_entries
            WHERE role = '拓荒者'
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        
        return row[0] if row else None
    
    def clear_old_memories(self, keep_rounds: int = 10):
        """清理旧记忆,保留最近N轮"""
        with self._lock:
            db = DatabaseManager.get(self.log_file)
            row = db.query_one('SELECT COUNT(*) FROM memory_entries')
            total = row[0] if row else 0
            
            if total <= keep_rounds * 2:
                return
            
            db.execute('''
                DELETE FROM memory_entries 
                WHERE id IN (
                    SELECT id FROM memory_entries 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
            ''', (total - keep_rounds * 2,), commit=True)
            
            logger.info(f"已清理旧记忆,保留最近{keep_rounds}轮对话")
    
    def get_stats(self) -> Dict:
        db = DatabaseManager.get(self.log_file)
        row = db.query_one('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN role = '用户' THEN 1 ELSE 0 END) as user_count,
                SUM(CASE WHEN role = '拓荒者' THEN 1 ELSE 0 END) as assistant_count
            FROM memory_entries
        ''')
        
        return {
            "total": row[0] if row[0] else 0,
            "user_messages": row[1] if row[1] else 0,
            "assistant_messages": row[2] if row[2] else 0
        }
