import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ChatHistory:
    MAX_SESSION_AGE_DAYS = 90
    MAX_MESSAGES_PER_SESSION = 500

    def __init__(self, db_path: str = "data/chat_history.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        db = DatabaseManager.get(self.db_path)
        db.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                message_count INTEGER DEFAULT 0,
                metadata TEXT
            )''')
        db.execute('''CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                intent TEXT,
                route TEXT,
                confidence REAL,
                elapsed REAL,
                cbnr_summary TEXT,
                timestamp TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)')

    def create_session(self, session_id: str = None, title: str = "") -> str:
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        now = datetime.now().isoformat()
        db = DatabaseManager.get(self.db_path)
        db.execute(
            'INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at, message_count, metadata) VALUES (?, ?, ?, ?, 0, ?)',
            (session_id, title or f"对话 {now[:10]}", now, now, '{}'),
            commit=True
        )
        return session_id

    def add_message(self, session_id: str, role: str, content: str,
                    intent: str = "", route: str = "", confidence: float = 0.0,
                    elapsed: float = 0.0, cbnr_summary: str = "") -> int:
        now = datetime.now().isoformat()
        db = DatabaseManager.get(self.db_path)
        cur = db.execute(
            'INSERT INTO messages (session_id, role, content, intent, route, confidence, elapsed, cbnr_summary, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (session_id, role, content[:5000], intent, route, confidence, elapsed, cbnr_summary[:500], now),
            commit=True
        )
        db.execute(
            'UPDATE sessions SET updated_at=?, message_count=message_count+1 WHERE id=?',
            (now, session_id),
            commit=True
        )
        if role == 'user' and content:
            row = db.query_one('SELECT title, message_count FROM sessions WHERE id=?', (session_id,))
            if row and row[1] <= 1 and not row[0].startswith("对话 "):
                title = content[:30].replace('\n', ' ')
                db.execute('UPDATE sessions SET title=? WHERE id=?', (title, session_id), commit=True)
        return cur.lastrowid

    def get_sessions(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        db = DatabaseManager.get(self.db_path)
        rows = db.query(
            'SELECT id, title, created_at, updated_at, message_count FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?',
            (limit, offset)
        )
        return [dict(row) for row in rows]

    def get_messages(self, session_id: str, limit: int = 100, before_id: int = 0) -> List[Dict]:
        db = DatabaseManager.get(self.db_path)
        if before_id > 0:
            rows = db.query(
                'SELECT id, role, content, intent, route, confidence, elapsed, cbnr_summary, timestamp FROM messages WHERE session_id=? AND id<? ORDER BY id DESC LIMIT ?',
                (session_id, before_id, limit)
            )
            return list(reversed([dict(row) for row in rows]))
        else:
            rows = db.query(
                'SELECT id, role, content, intent, route, confidence, elapsed, cbnr_summary, timestamp FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?',
                (session_id, limit)
            )
            return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        db = DatabaseManager.get(self.db_path)
        rows = db.query(
            'SELECT m.id, m.session_id, m.role, m.content, m.timestamp, s.title FROM messages m JOIN sessions s ON m.session_id=s.id WHERE m.content LIKE ? ORDER BY m.timestamp DESC LIMIT ?',
            (f'%{query}%', limit)
        )
        return [dict(row) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        db = DatabaseManager.get(self.db_path)
        db.execute('DELETE FROM messages WHERE session_id=?', (session_id,), commit=True)
        db.execute('DELETE FROM sessions WHERE id=?', (session_id,), commit=True)
        return True

    def cleanup(self, max_age_days: int = None):
        max_age = max_age_days or self.MAX_SESSION_AGE_DAYS
        cutoff = datetime.now().timestamp() - max_age * 86400
        cutoff_str = datetime.fromtimestamp(cutoff).isoformat()
        db = DatabaseManager.get(self.db_path)
        rows = db.query('SELECT id FROM sessions WHERE updated_at<?', (cutoff_str,))
        old_ids = [row[0] for row in rows]
        for sid in old_ids:
            db.execute('DELETE FROM messages WHERE session_id=?', (sid,), commit=True)
            db.execute('DELETE FROM sessions WHERE id=?', (sid,), commit=True)
        if old_ids:
            logger.info(f"对话历史清理: 删除{len(old_ids)}个过期会话(>{max_age}天)")

    def get_stats(self) -> Dict:
        db = DatabaseManager.get(self.db_path)
        sessions = db.query_one('SELECT COUNT(*) FROM sessions')[0]
        messages = db.query_one('SELECT COUNT(*) FROM messages')[0]
        user_msgs = db.query_one("SELECT COUNT(*) FROM messages WHERE role='user'")[0]
        assistant_msgs = db.query_one("SELECT COUNT(*) FROM messages WHERE role='assistant'")[0]
        return {
            "total_sessions": sessions,
            "total_messages": messages,
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
        }


_chat_history: Optional[ChatHistory] = None


def get_chat_history() -> ChatHistory:
    global _chat_history
    if _chat_history is None:
        _chat_history = ChatHistory()
    return _chat_history
