"""
反馈信号捕获器 - 扩展L1感知层，捕获多维反馈信号

支持的信号类型：
- 显式信号：点赞/点踩/评分/原因选择
- 隐式信号：复制行为/重试次数/对话停留时间/追问模式
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from pathlib import Path
from core.ports.adapters import get_storage_port

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    LIKE = "like"
    DISLIKE = "dislike"
    RATING = "rating"
    COPY = "copy"
    RETRY = "retry"
    ABANDON = "abandon"
    CORRECTION = "correction"
    FOLLOW_UP = "follow_up"
    EXPLICIT_REASON = "explicit_reason"


@dataclass
class FeedbackSignal:
    """反馈信号"""
    signal_id: str
    conversation_id: str
    turn_id: str
    feedback_type: FeedbackType
    value: Any
    context: Dict[str, Any]
    timestamp: str
    response_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "ui"


class FeedbackSignalCapture:
    """
    反馈信号捕获器
    
    扩展L1感知层，在捕获用户输入的同时捕获所有反馈信号。
    """
    
    def __init__(self, db_path: str = "data/feedback_signals.db"):
        self.db_path = Path(db_path)
        self._init_database()
        
        logger.info("📡 反馈信号捕获器已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db = get_storage_port(str(self.db_path))
        db.execute("""
            CREATE TABLE IF NOT EXISTS feedback_signals (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                turn_id TEXT,
                feedback_type TEXT,
                value TEXT,
                context TEXT,
                response_id TEXT,
                user_id TEXT,
                source TEXT,
                timestamp TEXT,
                processed INTEGER DEFAULT 0
            )
        """)
        db.execute('CREATE INDEX IF NOT EXISTS idx_conv ON feedback_signals(conversation_id)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_type ON feedback_signals(feedback_type)', commit=True)
    
    def capture(self, signal: FeedbackSignal) -> str:
        """捕获一个反馈信号"""
        db = get_storage_port(str(self.db_path))
        db.execute("""
            INSERT INTO feedback_signals
            (id, conversation_id, turn_id, feedback_type, value, context,
             response_id, user_id, source, timestamp, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            signal.signal_id,
            signal.conversation_id,
            signal.turn_id,
            signal.feedback_type.value,
            json.dumps(signal.value, ensure_ascii=False),
            json.dumps(signal.context, ensure_ascii=False),
            signal.response_id,
            signal.user_id,
            signal.source,
            signal.timestamp
        ), commit=True)
        
        logger.debug(f"捕获反馈信号: {signal.feedback_type.value} (ID={signal.signal_id})")
        
        return signal.signal_id
    
    def get_signals_by_conversation(self, conversation_id: str) -> List[Dict]:
        """获取一个对话的所有反馈信号"""
        db = get_storage_port(str(self.db_path))
        rows = db.query(
            "SELECT * FROM feedback_signals WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,)
        )
        return [dict(r) for r in rows]
    
    def get_unprocessed_signals(self, limit: int = 100) -> List[Dict]:
        """获取未处理的信号（用于后台处理）"""
        db = get_storage_port(str(self.db_path))
        rows = db.query(
            "SELECT * FROM feedback_signals WHERE processed = 0 ORDER BY timestamp LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in rows]
    
    def mark_processed(self, signal_id: str):
        """标记信号为已处理"""
        db = get_storage_port(str(self.db_path))
        db.execute(
            "UPDATE feedback_signals SET processed = 1 WHERE id = ?",
            (signal_id,),
            commit=True
        )


signal_capture = FeedbackSignalCapture()