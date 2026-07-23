"""
立体记忆系统 (Stereo Memory System)

核心理念：记忆不是扁平的数据，而是立体的存在
- 内容维度：记忆了什么
- 关系维度：与谁相关
- 自我维度：我当时的角色和感受
- 时间维度：何时发生，如何演变

修复版本：
1. 统一枚举处理
2. 修复 search 方法
3. 完善 save 方法
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from core.ports.adapters import get_storage_port
import os
import json
from loguru import logger


class MemoryType(Enum):
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    EXPERIENCE = "experience"
    EMOTION = "emotion"
    RELATIONSHIP = "relationship"
    SKILL = "skill"


class MemoryImportance(Enum):
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3
    TRIVIAL = 0.1
    
    @classmethod
    def from_value(cls, value: Union[float, int, None]) -> "MemoryImportance":
        """从数值安全创建枚举"""
        if value is None:
            return cls.MEDIUM
        if isinstance(value, cls):
            return value
        try:
            val = float(value)
            for member in cls:
                if abs(member.value - val) < 0.01:
                    return member
            return cls.MEDIUM
        except (ValueError, TypeError):
            return cls.MEDIUM
    
    def to_value(self) -> float:
        """获取数值"""
        return self.value


@dataclass
class MemoryContext:
    user_id: str = "default"
    session_id: str = ""
    conversation_turn: int = 0
    trigger: str = ""
    related_concepts: List[str] = field(default_factory=list)


@dataclass
class SelfDimension:
    role: str = "assistant"
    confidence: float = 0.5
    emotional_state: str = "neutral"
    learning_progress: float = 0.0
    intentions: List[str] = field(default_factory=list)


@dataclass
class TimeDimension:
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    decay_factor: float = 1.0
    reinforcement_count: int = 0


@dataclass
class StereoMemory:
    memory_id: str
    content: Any
    memory_type: MemoryType
    importance: float
    related_memories: Set[str] = field(default_factory=set)
    related_entities: Set[str] = field(default_factory=set)
    self_dimension: SelfDimension = field(default_factory=SelfDimension)
    time_dimension: TimeDimension = field(default_factory=TimeDimension)
    context: MemoryContext = field(default_factory=MemoryContext)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default=None):
        """dict兼容访问器 — 使StereoMemory可像dict一样访问，用于睡眠整合等消费端"""
        if key == "content":
            return self.content
        if key == "memory_id":
            return self.memory_id
        if key == "importance":
            return self.importance
        if key == "memory_type":
            return self.memory_type
        return self.metadata.get(key, default)


@dataclass
class StereoMemoryEntry:
    """立体记忆条目 — 用于对话记忆存储"""
    id: str
    user_content: str
    system_content: str
    intent: str
    topic: str
    trust_change: float = 0.0
    intimacy_change: float = 0.0
    dependency_change: float = 0.0
    self_state_before: Dict = field(default_factory=dict)
    self_state_after: Dict = field(default_factory=dict)
    skills_used: List[str] = field(default_factory=list)
    skills_formed: List[str] = field(default_factory=list)
    timestamp: str = ""
    importance: float = 0.5
    user_emotion: str = "neutral"
    system_emotion: str = "neutral"
    memory_type: MemoryType = MemoryType.CONVERSATION

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class StereoMemorySystem:
    """立体记忆系统"""

    def __init__(self, db_path: str = "data/stereo_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.memories: Dict[str, StereoMemory] = {}
        self.memory_index: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        
        self.stats = {
            "total_memories": 0,
            "by_type": {t.value: 0 for t in MemoryType},
            "total_accesses": 0,
            "total_reinforcements": 0,
        }
        
        self._init_database()
        self._load_memories()

    def _init_database(self):
        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS stereo_memories (
                memory_id TEXT PRIMARY KEY,
                content TEXT,
                memory_type TEXT,
                importance REAL,
                related_memories TEXT,
                related_entities TEXT,
                self_role TEXT,
                self_confidence REAL,
                self_emotional_state TEXT,
                self_learning_progress REAL,
                self_intentions TEXT,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER,
                decay_factor REAL,
                reinforcement_count INTEGER,
                context_user_id TEXT,
                context_session_id TEXT,
                context_conversation_turn INTEGER,
                context_trigger TEXT,
                context_related_concepts TEXT,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memory_type ON stereo_memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_importance ON stereo_memories(importance);
            CREATE INDEX IF NOT EXISTS idx_created_at ON stereo_memories(created_at)
        ''')

    def _load_memories(self):
        try:
            db = get_storage_port(self.db_path)
            for row in db.query("SELECT * FROM stereo_memories"):
                memory = self._row_to_memory(row)
                self.memories[memory.memory_id] = memory
                self._update_index(memory)
            self.stats["total_memories"] = len(self.memories)
        except Exception as e:
            logger.warning(f"加载立体记忆失败: {e}")

    def _row_to_memory(self, row: tuple) -> StereoMemory:
        (
            memory_id, content, memory_type, importance,
            related_memories, related_entities,
            self_role, self_confidence, self_emotional_state,
            self_learning_progress, self_intentions,
            created_at, last_accessed, access_count,
            decay_factor, reinforcement_count,
            context_user_id, context_session_id, context_conversation_turn,
            context_trigger, context_related_concepts,
            metadata
        ) = row
        
        return StereoMemory(
            memory_id=memory_id,
            content=json.loads(content) if content else None,
            memory_type=MemoryType(memory_type),
            importance=importance,
            related_memories=set(json.loads(related_memories)) if related_memories else set(),
            related_entities=set(json.loads(related_entities)) if related_entities else set(),
            self_dimension=SelfDimension(
                role=self_role or "assistant",
                confidence=self_confidence or 0.5,
                emotional_state=self_emotional_state or "neutral",
                learning_progress=self_learning_progress or 0.0,
                intentions=json.loads(self_intentions) if self_intentions else [],
            ),
            time_dimension=TimeDimension(
                created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
                last_accessed=datetime.fromisoformat(last_accessed) if last_accessed else datetime.now(),
                access_count=access_count or 0,
                decay_factor=decay_factor or 1.0,
                reinforcement_count=reinforcement_count or 0,
            ),
            context=MemoryContext(
                user_id=context_user_id or "default",
                session_id=context_session_id or "",
                conversation_turn=context_conversation_turn or 0,
                trigger=context_trigger or "",
                related_concepts=json.loads(context_related_concepts) if context_related_concepts else [],
            ),
            metadata=json.loads(metadata) if metadata else {},
        )

    def _memory_to_dict(self, memory: StereoMemory) -> dict:
        return {
            "memory_id": memory.memory_id,
            "content": json.dumps(memory.content, ensure_ascii=False),
            "memory_type": memory.memory_type.value,
            "importance": memory.importance,
            "related_memories": json.dumps(list(memory.related_memories)),
            "related_entities": json.dumps(list(memory.related_entities)),
            "self_role": memory.self_dimension.role,
            "self_confidence": memory.self_dimension.confidence,
            "self_emotional_state": memory.self_dimension.emotional_state,
            "self_learning_progress": memory.self_dimension.learning_progress,
            "self_intentions": json.dumps(memory.self_dimension.intentions),
            "created_at": memory.time_dimension.created_at.isoformat(),
            "last_accessed": memory.time_dimension.last_accessed.isoformat(),
            "access_count": memory.time_dimension.access_count,
            "decay_factor": memory.time_dimension.decay_factor,
            "reinforcement_count": memory.time_dimension.reinforcement_count,
            "context_user_id": memory.context.user_id,
            "context_session_id": memory.context.session_id,
            "context_conversation_turn": memory.context.conversation_turn,
            "context_trigger": memory.context.trigger,
            "context_related_concepts": json.dumps(memory.context.related_concepts),
            "metadata": json.dumps(memory.metadata),
        }

    def _update_index(self, memory: StereoMemory):
        type_key = f"type:{memory.memory_type.value}"
        if type_key not in self.memory_index:
            self.memory_index[type_key] = set()
        self.memory_index[type_key].add(memory.memory_id)
        for entity in memory.related_entities:
            entity_key = f"entity:{entity}"
            if entity_key not in self.memory_index:
                self.memory_index[entity_key] = set()
            self.memory_index[entity_key].add(memory.memory_id)

    def store(
        self,
        content: Any,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        importance: Union[float, MemoryImportance] = MemoryImportance.MEDIUM,
        related_entities: Set[str] = None,
        self_dimension: SelfDimension = None,
        context: MemoryContext = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """存储立体记忆"""
        with self._lock:
            memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.memories)}"
            
            if isinstance(importance, MemoryImportance):
                importance_value = importance.value
            else:
                importance_value = float(importance)
            
            memory = StereoMemory(
                memory_id=memory_id,
                content=content,
                memory_type=memory_type,
                importance=importance_value,
                related_entities=related_entities or set(),
                self_dimension=self_dimension or SelfDimension(),
                context=context or MemoryContext(),
                metadata=metadata or {},
            )
            
            self.memories[memory_id] = memory
            self._update_index(memory)
            self._save_memory(memory)
            
            self.stats["total_memories"] += 1
            self.stats["by_type"][memory_type.value] += 1
            
            return memory_id

    def _save_memory(self, memory: StereoMemory):
        db = get_storage_port(self.db_path)
        data = self._memory_to_dict(memory)
        db.execute('''
            INSERT OR REPLACE INTO stereo_memories (
                memory_id, content, memory_type, importance,
                related_memories, related_entities,
                self_role, self_confidence, self_emotional_state,
                self_learning_progress, self_intentions,
                created_at, last_accessed, access_count,
                decay_factor, reinforcement_count,
                context_user_id, context_session_id, context_conversation_turn,
                context_trigger, context_related_concepts,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(data.values()), commit=True)

    def recall(self, memory_id: str, reinforce: bool = True) -> Optional[StereoMemory]:
        """回忆记忆"""
        with self._lock:
            if memory_id not in self.memories:
                return None
            
            memory = self.memories[memory_id]
            memory.time_dimension.last_accessed = datetime.now()
            memory.time_dimension.access_count += 1
            
            if reinforce:
                memory.time_dimension.reinforcement_count += 1
                memory.importance = min(1.0, memory.importance + 0.05)
            
            self.stats["total_accesses"] += 1
            if reinforce:
                self.stats["total_reinforcements"] += 1
            
            self._save_memory(memory)
            return memory

    def search(
        self,
        memory_type: MemoryType = None,
        min_importance: float = 0.0,
        entity: str = None,
        query: str = None,
        limit: int = 20,
    ) -> List[StereoMemory]:
        """搜索记忆"""
        with self._lock:
            candidates = set(self.memories.keys())
            
            if memory_type:
                type_key = f"type:{memory_type.value}"
                if type_key in self.memory_index:
                    candidates &= self.memory_index[type_key]
            
            if entity:
                entity_key = f"entity:{entity}"
                if entity_key in self.memory_index:
                    candidates &= self.memory_index[entity_key]
            
            results = []
            for memory_id in candidates:
                memory = self.memories[memory_id]
                if memory.importance >= min_importance:
                    if query:
                        content_str = str(memory.content).lower()
                        if query.lower() not in content_str:
                            continue
                    results.append(memory)
            
            results.sort(key=lambda m: (
                m.importance,
                m.time_dimension.access_count,
                m.time_dimension.last_accessed,
            ), reverse=True)
            
            returned = results[:limit]
            for memory in returned:
                memory.time_dimension.last_accessed = datetime.now()
                memory.time_dimension.access_count += 1
                self.stats["total_accesses"] += 1
                self._save_memory(memory)
            
            return returned

    def relate(self, memory_id1: str, memory_id2: str, relation_type: str = "related"):
        """建立记忆关联"""
        with self._lock:
            if memory_id1 not in self.memories or memory_id2 not in self.memories:
                return
            
            memory1 = self.memories[memory_id1]
            memory2 = self.memories[memory_id2]
            
            memory1.related_memories.add(memory_id2)
            memory2.related_memories.add(memory_id1)
            
            self._save_memory(memory1)
            self._save_memory(memory2)

    def decay(self, hours: float = 24.0):
        """记忆衰减"""
        with self._lock:
            now = datetime.now()
            threshold = now - timedelta(hours=hours)
            to_decay = []
            
            for memory_id, memory in self.memories.items():
                if memory.importance >= MemoryImportance.CRITICAL.value:
                    continue
                
                age_hours = (now - memory.time_dimension.last_accessed).total_seconds() / 3600
                if age_hours > hours:
                    decay_rate = 0.01 * (age_hours / 24)
                    memory.time_dimension.decay_factor *= (1 - decay_rate)
                    if memory.time_dimension.decay_factor < 0.1:
                        to_decay.append(memory_id)
            
            for memory_id in to_decay:
                del self.memories[memory_id]
                self.stats["total_memories"] -= 1

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total = len(self.memories)
            if total == 0:
                return {
                    "total_memories": 0,
                    "by_type": {t.value: 0 for t in MemoryType},
                    "total_accesses": self.stats["total_accesses"],
                    "total_reinforcements": self.stats["total_reinforcements"],
                    "avg_importance": 0.0,
                    "avg_access_count": 0.0,
                }
            
            total_importance = sum(m.importance for m in self.memories.values())
            total_access = sum(m.time_dimension.access_count for m in self.memories.values())
            
            return {
                "total_memories": total,
                "by_type": {
                    t.value: len([m for m in self.memories.values() if m.memory_type == t])
                    for t in MemoryType
                },
                "total_accesses": self.stats["total_accesses"],
                "total_reinforcements": self.stats["total_reinforcements"],
                "avg_importance": total_importance / total,
                "avg_access_count": total_access / total,
            }

    def get_memory_network(self, memory_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取记忆网络"""
        with self._lock:
            if memory_id not in self.memories:
                return {"center": None, "neighbors": []}
            
            center = self.memories[memory_id]
            neighbors = {}
            visited = {memory_id}
            queue = [(memory_id, 0)]
            
            while queue:
                current_id, current_depth = queue.pop(0)
                if current_depth >= depth:
                    continue
                if current_id not in self.memories:
                    continue
                
                current = self.memories[current_id]
                for related_id in current.related_memories:
                    if related_id not in visited and related_id in self.memories:
                        visited.add(related_id)
                        queue.append((related_id, current_depth + 1))
                        related = self.memories[related_id]
                        neighbors[related_id] = {
                            "content": str(related.content)[:100],
                            "type": related.memory_type.value,
                            "importance": related.importance,
                            "depth": current_depth + 1,
                        }
            
            return {
                "center": {
                    "content": str(center.content)[:100],
                    "type": center.memory_type.value,
                    "importance": center.importance,
                },
                "neighbors": neighbors,
            }

    def save(self, entry: Dict) -> str:
        """
        保存记忆条目（适配接口）
        """
        content = entry.get("content", entry.get("user_content", ""))
        memory_type = entry.get("memory_type", MemoryType.CONVERSATION)
        importance = entry.get("importance", MemoryImportance.MEDIUM)
        
        if isinstance(importance, MemoryImportance):
            importance_value = importance.value
        else:
            importance_value = float(importance)
        
        self_dim = SelfDimension(
            role=entry.get("self_role", "assistant"),
            confidence=entry.get("self_confidence", 0.5),
            emotional_state=entry.get("self_emotional_state", "neutral"),
            learning_progress=entry.get("self_learning_progress", 0.0),
            intentions=entry.get("self_intentions", []),
        )
        
        ctx = MemoryContext(
            user_id=entry.get("user_id", "default"),
            session_id=entry.get("session_id", ""),
            conversation_turn=entry.get("conversation_turn", 0),
            trigger=entry.get("trigger", ""),
            related_concepts=entry.get("related_concepts", []),
        )
        
        return self.store(
            content=content,
            memory_type=memory_type if isinstance(memory_type, MemoryType) else MemoryType.CONVERSATION,
            importance=importance_value,
            related_entities=set(entry.get("related_entities", [])),
            self_dimension=self_dim,
            context=ctx,
            metadata=entry.get("metadata", {}),
        )

    def get_recent(self, limit: int = 20) -> List[StereoMemory]:
        """获取最近记忆（SQL排序，避免全量Python排序）"""
        try:
            db = get_storage_port(self.db_path)
            rows = db.query('SELECT * FROM stereo_memories ORDER BY last_accessed DESC LIMIT ?', (limit,))
            results = [self._row_to_memory(row) for row in rows]
            for m in results:
                m.time_dimension.access_count += 1
                m.time_dimension.last_accessed = datetime.now()
                self.stats["total_accesses"] += 1
                self._save_memory(m)
            return results
        except Exception:
            with self._lock:
                all_memories = list(self.memories.values())
                all_memories.sort(key=lambda m: m.time_dimension.last_accessed, reverse=True)
                returned = all_memories[:limit]
                for m in returned:
                    m.time_dimension.access_count += 1
                    m.time_dimension.last_accessed = datetime.now()
                    self.stats["total_accesses"] += 1
                    self._save_memory(m)
                return returned

    def get_by_topic(self, topic: str, limit: int = 10) -> List[StereoMemory]:
        """按主题获取记忆"""
        return self.search(query=topic, limit=limit)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.get_statistics()


_stereo_memory: Optional[StereoMemorySystem] = None
_lock = threading.RLock()


def get_stereo_memory() -> StereoMemorySystem:
    """获取立体记忆系统单例（线程安全）"""
    global _stereo_memory
    with _lock:
        if _stereo_memory is None:
            _stereo_memory = StereoMemorySystem()
        return _stereo_memory
