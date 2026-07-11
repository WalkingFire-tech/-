"""
长期记忆系统 (Long-term Memory System)

实现跨对话记忆持久化，让系统能够记住用户并在长期中形成信任
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import threading
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MemoryType(Enum):
    EPISODIC = "episodic"      # 情景记忆：具体事件
    SEMANTIC = "semantic"      # 语义记忆：概念知识
    PROCEDURAL = "procedural"  # 程序记忆：技能方法
    RELATIONAL = "relational"  # 关系记忆：人际交互
    EMOTIONAL = "emotional"    # 情感记忆：情绪体验


class MemoryImportance(Enum):
    CRITICAL = 5     # 关键记忆，永不遗忘
    HIGH = 4         # 高重要度
    MEDIUM = 3       # 中等重要
    LOW = 2          # 低重要度
    TRIVIAL = 1      # 琐碎记忆


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    type: MemoryType
    content: Any
    importance: MemoryImportance
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    decay_rate: float = 0.1
    emotional_valence: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    associations: List[str] = field(default_factory=list)
    source: str = "unknown"
    confidence: float = 0.8
    
    def get_strength(self) -> float:
        """计算记忆强度（考虑衰减和访问）"""
        age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
        decay = 1.0 / (1.0 + self.decay_rate * age_hours)
        access_boost = min(1.0 + 0.1 * self.access_count, 2.0)
        importance_factor = self.importance.value / 5.0
        return decay * access_boost * importance_factor


@dataclass
class ConversationMemory:
    """对话记忆"""
    conversation_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    emotions: List[float] = field(default_factory=list)
    satisfaction: Optional[float] = None
    key_memories: List[str] = field(default_factory=list)


class LongTermMemory:
    """
    长期记忆系统
    
    职责：
    1. 跨对话记忆持久化
    2. 记忆衰减与强化
    3. 记忆检索与联想
    4. 情感记忆管理
    5. 记忆整合与遗忘
    """
    
    def __init__(self, db_path: str = "data/long_term_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._init_database()
        
        self.memory_cache: Dict[str, MemoryItem] = {}
        self.conversation_cache: Dict[str, ConversationMemory] = {}
        
        self.decay_interval_hours = 24
        self.consolidation_threshold = 3
        
        logger.info("📚 长期记忆系统已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        db = DatabaseManager.get(str(self.db_path))
        db.executescript('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                decay_rate REAL DEFAULT 0.1,
                emotional_valence REAL DEFAULT 0.0,
                context TEXT,
                associations TEXT,
                source TEXT DEFAULT 'unknown',
                confidence REAL DEFAULT 0.8
            );
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                messages TEXT,
                topics TEXT,
                emotions TEXT,
                satisfaction REAL,
                key_memories TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                total_conversations INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                trust_score REAL DEFAULT 0.5,
                relationship_depth REAL DEFAULT 0.0,
                preferences TEXT,
                important_topics TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)
        ''')
    
    def store_memory(
        self,
        content: Any,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        emotional_valence: float = 0.0,
        source: str = "interaction",
    ) -> str:
        """存储记忆"""
        import uuid
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        memory = MemoryItem(
            id=memory_id,
            type=memory_type,
            content=content,
            importance=importance,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            emotional_valence=emotional_valence,
            context=context or {},
            source=source,
        )
        
        with self._lock:
            self.memory_cache[memory_id] = memory
            
            db = DatabaseManager.get(str(self.db_path))
            db.execute('''
                INSERT INTO memories 
                (id, type, content, importance, created_at, last_accessed,
                 access_count, decay_rate, emotional_valence, context, 
                 associations, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.id,
                memory.type.value,
                json.dumps(content, ensure_ascii=False),
                memory.importance.value,
                memory.created_at.isoformat(),
                memory.last_accessed.isoformat(),
                memory.access_count,
                memory.decay_rate,
                memory.emotional_valence,
                json.dumps(memory.context, ensure_ascii=False),
                json.dumps(memory.associations),
                memory.source,
                memory.confidence,
            ), commit=True)
        
        logger.debug(f"存储记忆: {memory_id} ({memory_type.value})")
        return memory_id
    
    def retrieve_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """检索单个记忆"""
        if memory_id in self.memory_cache:
            memory = self.memory_cache[memory_id]
            memory.last_accessed = datetime.now()
            memory.access_count += 1
            return memory
        
        db = DatabaseManager.get(str(self.db_path))
        row = db.query_one(
            'SELECT * FROM memories WHERE id = ?',
            (memory_id,)
        )
        
        if row:
            memory = MemoryItem(
                id=row[0],
                type=MemoryType(row[1]),
                content=json.loads(row[2]),
                importance=MemoryImportance(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_accessed=datetime.fromisoformat(row[5]),
                access_count=row[6],
                decay_rate=row[7],
                emotional_valence=row[8],
                context=json.loads(row[9]) if row[9] else {},
                associations=json.loads(row[10]) if row[10] else [],
                source=row[11],
                confidence=row[12],
            )
            
            db.execute('''
                UPDATE memories 
                SET last_accessed = ?, access_count = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), memory.access_count + 1, memory_id), commit=True)
            
            memory.last_accessed = datetime.now()
            memory.access_count += 1
            self.memory_cache[memory_id] = memory
            
            return memory
        
        return None
    
    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        min_importance: Optional[MemoryImportance] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """搜索记忆"""
        memories = []
        
        db = DatabaseManager.get(str(self.db_path))
        sql = 'SELECT * FROM memories WHERE content LIKE ?'
        params = [f'%{query}%']
        
        if memory_type:
            sql += ' AND type = ?'
            params.append(memory_type.value)
        
        if min_importance:
            sql += ' AND importance >= ?'
            params.append(min_importance.value)
        
        sql += ' ORDER BY importance DESC, last_accessed DESC LIMIT ?'
        params.append(limit)
        
        rows = db.query(sql, params)
        
        for row in rows:
            memory = MemoryItem(
                id=row[0],
                type=MemoryType(row[1]),
                content=json.loads(row[2]),
                importance=MemoryImportance(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_accessed=datetime.fromisoformat(row[5]),
                access_count=row[6],
                decay_rate=row[7],
                emotional_valence=row[8],
                context=json.loads(row[9]) if row[9] else {},
                associations=json.loads(row[10]) if row[10] else [],
                source=row[11],
                confidence=row[12],
            )
            memories.append(memory)
        
        return memories
    
    def get_recent_memories(
        self,
        hours: int = 24,
        memory_type: Optional[MemoryType] = None,
        limit: int = 20,
    ) -> List[MemoryItem]:
        """获取最近记忆"""
        cutoff = datetime.now() - timedelta(hours=hours)
        memories = []
        
        db = DatabaseManager.get(str(self.db_path))
        sql = 'SELECT * FROM memories WHERE created_at >= ?'
        params = [cutoff.isoformat()]
        
        if memory_type:
            sql += ' AND type = ?'
            params.append(memory_type.value)
        
        sql += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        rows = db.query(sql, params)
        
        for row in rows:
            memory = MemoryItem(
                id=row[0],
                type=MemoryType(row[1]),
                content=json.loads(row[2]),
                importance=MemoryImportance(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_accessed=datetime.fromisoformat(row[5]),
                access_count=row[6],
                decay_rate=row[7],
                emotional_valence=row[8],
                context=json.loads(row[9]) if row[9] else {},
                associations=json.loads(row[10]) if row[10] else [],
                source=row[11],
                confidence=row[12],
            )
            memories.append(memory)
        
        return memories
    
    def start_conversation(self, user_id: str) -> str:
        """开始新对话"""
        import uuid
        conversation_id = f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        conversation = ConversationMemory(
            conversation_id=conversation_id,
            user_id=user_id,
            started_at=datetime.now(),
        )
        
        self.conversation_cache[conversation_id] = conversation
        
        db = DatabaseManager.get(str(self.db_path))
        row = db.query_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        
        if row:
            db.execute('''
                UPDATE users 
                SET last_seen = ?, total_conversations = total_conversations + 1
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
        else:
            db.execute('''
                INSERT INTO users 
                (user_id, first_seen, last_seen, total_conversations)
                VALUES (?, ?, ?, 1)
            ''', (user_id, datetime.now().isoformat(), datetime.now().isoformat()))
        
        db.execute('''
            INSERT INTO conversations 
            (conversation_id, user_id, started_at, messages, topics, emotions, key_memories)
            VALUES (?, ?, ?, '[]', '[]', '[]', '[]')
        ''', (conversation_id, user_id, conversation.started_at.isoformat()), commit=True)
        
        logger.info(f"开始对话: {conversation_id} (用户: {user_id})")
        return conversation_id
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        emotion: Optional[float] = None,
    ):
        """添加消息到对话"""
        if conversation_id not in self.conversation_cache:
            return
        
        conversation = self.conversation_cache[conversation_id]
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion,
        }
        
        conversation.messages.append(message)
        
        if emotion is not None:
            conversation.emotions.append(emotion)
        
        db = DatabaseManager.get(str(self.db_path))
        row = db.query_one(
            'SELECT messages, emotions FROM conversations WHERE conversation_id = ?',
            (conversation_id,)
        )
        
        if row:
            messages = json.loads(row[0])
            emotions = json.loads(row[1])
            
            messages.append(message)
            if emotion is not None:
                emotions.append(emotion)
            
            db.execute('''
                UPDATE conversations 
                SET messages = ?, emotions = ?
                WHERE conversation_id = ?
            ''', (json.dumps(messages, ensure_ascii=False), json.dumps(emotions), conversation_id))
            
            db.execute('''
                UPDATE users 
                SET total_messages = total_messages + 1
                WHERE user_id = (
                    SELECT user_id FROM conversations WHERE conversation_id = ?
                )
            ''', (conversation_id,), commit=True)
    
    def end_conversation(
        self,
        conversation_id: str,
        satisfaction: Optional[float] = None,
        key_memories: Optional[List[str]] = None,
    ):
        """结束对话"""
        if conversation_id not in self.conversation_cache:
            return
        
        conversation = self.conversation_cache[conversation_id]
        conversation.ended_at = datetime.now()
        conversation.satisfaction = satisfaction
        if key_memories:
            conversation.key_memories = key_memories
        
        db = DatabaseManager.get(str(self.db_path))
        db.execute('''
            UPDATE conversations 
            SET ended_at = ?, satisfaction = ?, key_memories = ?
            WHERE conversation_id = ?
        ''', (
            conversation.ended_at.isoformat(),
            satisfaction,
            json.dumps(key_memories or []),
            conversation_id,
        ), commit=True)
        
        logger.info(f"结束对话: {conversation_id} (满意度: {satisfaction})")
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        db = DatabaseManager.get(str(self.db_path))
        row = db.query_one(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        
        if row:
            return {
                "user_id": row[0],
                "first_seen": row[1],
                "last_seen": row[2],
                "total_conversations": row[3],
                "total_messages": row[4],
                "trust_score": row[5],
                "relationship_depth": row[6],
                "preferences": json.loads(row[7]) if row[7] else {},
                "important_topics": json.loads(row[8]) if row[8] else [],
            }
        
        return {
            "user_id": user_id,
            "first_seen": None,
            "last_seen": None,
            "total_conversations": 0,
            "total_messages": 0,
            "trust_score": 0.5,
            "relationship_depth": 0.0,
            "preferences": {},
            "important_topics": [],
        }
    
    def update_user_trust(self, user_id: str, delta: float):
        """更新用户信任度"""
        db = DatabaseManager.get(str(self.db_path))
        db.execute('''
            UPDATE users 
            SET trust_score = MAX(0.0, MIN(1.0, trust_score + ?))
            WHERE user_id = ?
        ''', (delta, user_id), commit=True)
    
    def consolidate_memories(self):
        """整合记忆（睡眠整合）"""
        logger.info("开始记忆整合...")
        
        db = DatabaseManager.get(str(self.db_path))
        rows = db.query('''
            SELECT id, access_count, importance 
            FROM memories 
            WHERE access_count >= ?
        ''', (self.consolidation_threshold,))
        
        consolidated = 0
        for row in rows:
            memory_id, access_count, importance = row
            
            if importance < MemoryImportance.HIGH.value:
                new_importance = min(importance + 1, MemoryImportance.CRITICAL.value)
                db.execute('''
                    UPDATE memories SET importance = ? WHERE id = ?
                ''', (new_importance, memory_id), commit=True)
                consolidated += 1
        
        cutoff = datetime.now() - timedelta(days=30)
        rows = db.query('''
            SELECT id FROM memories 
            WHERE importance = ? AND last_accessed < ?
        ''', (MemoryImportance.TRIVIAL.value, cutoff.isoformat()))
        
        forgotten = 0
        for row in rows:
            db.execute('DELETE FROM memories WHERE id = ?', (row[0],), commit=True)
            forgotten += 1
        
        logger.info(f"记忆整合完成: 强化 {consolidated} 条, 遗忘 {forgotten} 条")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        db = DatabaseManager.get(str(self.db_path))
        total_memories = db.query_one('SELECT COUNT(*) FROM memories')[0]
        total_conversations = db.query_one('SELECT COUNT(*) FROM conversations')[0]
        total_users = db.query_one('SELECT COUNT(*) FROM users')[0]
        
        type_counts = {}
        for mem_type in MemoryType:
            count = db.query_one(
                'SELECT COUNT(*) FROM memories WHERE type = ?',
                (mem_type.value,)
            )[0]
            type_counts[mem_type.value] = count
        
        return {
            "total_memories": total_memories,
            "total_conversations": total_conversations,
            "total_users": total_users,
            "memories_by_type": type_counts,
            "cache_size": len(self.memory_cache),
        }


long_term_memory = LongTermMemory()
