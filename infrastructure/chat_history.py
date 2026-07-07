"""
对话历史存储 - 持久化对话记录

功能：
- 存储用户消息和AI回复
- 按会话分组
- 支持搜索和分页
- 自动清理过期记录
"""

import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

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
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
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
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)')

    def create_session(self, session_id: str = None, title: str = "") -> str:
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at, message_count, metadata) VALUES (?, ?, ?, ?, 0, ?)',
                (session_id, title or f"对话 {now[:10]}", now, now, '{}')
            )
        return session_id

    def add_message(self, session_id: str, role: str, content: str,
                    intent: str = "", route: str = "", confidence: float = 0.0,
                    elapsed: float = 0.0, cbnr_summary: str = "") -> int:
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                'INSERT INTO messages (session_id, role, content, intent, route, confidence, elapsed, cbnr_summary, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (session_id, role, content[:5000], intent, route, confidence, elapsed, cbnr_summary[:500], now)
            )
            conn.execute(
                'UPDATE sessions SET updated_at=?, message_count=message_count+1 WHERE id=?',
                (now, session_id)
            )
            if role == 'user' and content:
                cur2 = conn.execute('SELECT title, message_count FROM sessions WHERE id=?', (session_id,))
                row = cur2.fetchone()
                if row and row[1] <= 1 and not row[0].startswith("对话 "):
                    title = content[:30].replace('\n', ' ')
                    conn.execute('UPDATE sessions SET title=? WHERE id=?', (title, session_id))
            return cur.lastrowid

    def get_sessions(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                'SELECT id, title, created_at, updated_at, message_count FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?',
                (limit, offset)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_messages(self, session_id: str, limit: int = 100, before_id: int = 0) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if before_id > 0:
                cur = conn.execute(
                    'SELECT id, role, content, intent, route, confidence, elapsed, cbnr_summary, timestamp FROM messages WHERE session_id=? AND id<? ORDER BY id DESC LIMIT ?',
                    (session_id, before_id, limit)
                )
                rows = list(reversed([dict(row) for row in cur.fetchall()]))
            else:
                cur = conn.execute(
                    'SELECT id, role, content, intent, route, confidence, elapsed, cbnr_summary, timestamp FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?',
                    (session_id, limit)
                )
                rows = [dict(row) for row in cur.fetchall()]
            return rows

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                'SELECT m.id, m.session_id, m.role, m.content, m.timestamp, s.title FROM messages m JOIN sessions s ON m.session_id=s.id WHERE m.content LIKE ? ORDER BY m.timestamp DESC LIMIT ?',
                (f'%{query}%', limit)
            )
            return [dict(row) for row in cur.fetchall()]

    def delete_session(self, session_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM messages WHERE session_id=?', (session_id,))
            conn.execute('DELETE FROM sessions WHERE id=?', (session_id,))
        return True

    def cleanup(self, max_age_days: int = None):
        max_age = max_age_days or self.MAX_SESSION_AGE_DAYS
        cutoff = datetime.now().timestamp() - max_age * 86400
        cutoff_str = datetime.fromtimestamp(cutoff).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('SELECT id FROM sessions WHERE updated_at<?', (cutoff_str,))
            old_ids = [row[0] for row in cur.fetchall()]
            for sid in old_ids:
                conn.execute('DELETE FROM messages WHERE session_id=?', (sid,))
                conn.execute('DELETE FROM sessions WHERE id=?', (sid,))
        if old_ids:
            logger.info(f"对话历史清理: 删除{len(old_ids)}个过期会话(>{max_age}天)")

    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
            messages = conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
            user_msgs = conn.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0]
            assistant_msgs = conn.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0]
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