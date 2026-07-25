"""
端口适配器 — 将现有基础设施实现包装为端口接口

每个适配器将同步实现包装为async端口接口，
确保调用方无需关心底层是同步还是异步。
"""
from typing import List, Dict, Any, Optional

from core.ports.fact_store_port import FactStorePort
from core.ports.vector_store_port import VectorStorePort
from core.ports.config_port import ConfigPort
from core.ports.knowledge_port import KnowledgePort
from core.ports.experience_port import ExperiencePort
from core.ports.storage_port import StoragePort
from core.ports.chat_history_port import ChatHistoryPort
from core.ports.event_bus_port import EventBusPort


class FactStoreAdapter(FactStorePort):
    """FactStore 适配器 — 包装 infrastructure.fact_store.FactStore"""

    def __init__(self, fact_store=None):
        self._store = fact_store

    def _get_store(self):
        if self._store is None:
            from infrastructure.fact_store import fact_store
            self._store = fact_store
        return self._store

    async def search_by_keywords(self, text: str, limit: int = 10) -> List[Dict]:
        return self._get_store().search_by_keywords(text, limit)

    async def extract_and_store(self, text: str, source: str = "auto") -> int:
        return self._get_store().extract_and_store(text, source)

    async def get_negations(self, subject: str) -> List[Dict]:
        return self._get_store().get_negations(subject)

    async def mark_used(self, fact_id: int) -> None:
        self._get_store().mark_used(fact_id)

    def add_assertion(self, question: str = "", subject: str = "",
                      predicate: str = "", obj: str = "",
                      source: str = "auto", confidence: float = 0.9) -> int:
        store = self._get_store()
        if hasattr(store, 'add_assertion'):
            return store.add_assertion(question, subject, predicate, obj, source, confidence)
        return 0

    def add_correction(self, question: str = "", old_subject: str = "",
                       old_predicate: str = "", old_obj: str = "",
                       new_subject: str = "", new_predicate: str = "",
                       new_obj: str = "", correction_source: str = "user_correction") -> None:
        store = self._get_store()
        if hasattr(store, 'add_correction'):
            store.add_correction(question, old_subject, old_predicate, old_obj,
                                 new_subject, new_predicate, new_obj, correction_source)

    def get_stats(self) -> Dict:
        store = self._get_store()
        if hasattr(store, 'get_stats'):
            return store.get_stats()
        return {"available": True}

    def is_available(self) -> bool:
        try:
            self._get_store()
            return True
        except Exception:
            return False


class VectorStoreAdapter(VectorStorePort):
    """VectorRetriever 适配器 — 包装 infrastructure.vector_retriever"""

    def __init__(self, retriever=None):
        self._retriever = retriever

    def _get_retriever(self):
        if self._retriever is None:
            from infrastructure.vector_retriever import vector_retriever
            self._retriever = vector_retriever
        return self._retriever

    async def search(self, query: str, k: int = 3, threshold: float = 0.3) -> List[Dict]:
        return self._get_retriever().search(query, k=k, threshold=threshold)

    def is_available(self) -> bool:
        try:
            r = self._get_retriever()
            return r.is_available()
        except Exception:
            return False

    async def index_count(self) -> int:
        try:
            return self._get_retriever().get_index_count()
        except Exception:
            return 0


class ConfigAdapter(ConfigPort):
    """ConfigManager 适配器 — 包装 infrastructure.config_manager.config"""

    def __init__(self, manager=None):
        self._manager = manager

    def _get_manager(self):
        if self._manager is None:
            from infrastructure.config_manager import config
            self._manager = config
        return self._manager

    def get(self, key: str, default: Any = None) -> Any:
        return self._get_manager().get(key, default)

    def get_section(self, name: str) -> Dict:
        mgr = self._get_manager()
        if hasattr(mgr, 'get_section'):
            return mgr.get_section(name)
        return {}

    def set(self, key: str, value: Any) -> None:
        mgr = self._get_manager()
        if hasattr(mgr, 'set'):
            mgr.set(key, value)

    def is_available(self) -> bool:
        try:
            self._get_manager()
            return True
        except Exception:
            return False


class KnowledgeAdapter(KnowledgePort):
    """KnowledgeIndex 适配器 — 包装 infrastructure.knowledge_index.KnowledgeIndex"""

    def __init__(self, store=None):
        self._store = store

    def _get_store(self):
        if self._store is None:
            from infrastructure.knowledge_index import KnowledgeIndex
            self._store = KnowledgeIndex()
        return self._store

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        store = self._get_store()
        if hasattr(store, 'find_knowledge'):
            return store.find_knowledge(query, top_k)
        if hasattr(store, 'search'):
            return store.search(query, top_k)
        return []

    async def store(self, content: str, metadata: Optional[Dict] = None) -> str:
        store = self._get_store()
        if hasattr(store, 'add_topic_entry'):
            return store.add_topic_entry(content, metadata=metadata or {})
        if hasattr(store, 'add_knowledge'):
            return store.add_knowledge(content, metadata=metadata or {})
        return ""

    async def count(self) -> int:
        store = self._get_store()
        if hasattr(store, 'update_count'):
            return store.update_count() if callable(store.update_count) else store.update_count
        if hasattr(store, 'count'):
            return store.count()
        return 0

    def is_available(self) -> bool:
        try:
            self._get_store()
            return True
        except Exception:
            return False


class ExperienceAdapter(ExperiencePort):
    """ExperiencePool 适配器 — 包装 infrastructure.experience_pool"""

    def __init__(self, pool=None):
        self._pool = pool

    def _get_pool(self):
        if self._pool is None:
            from infrastructure.experience_pool import experience_pool
            self._pool = experience_pool
        return self._pool

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        return self._get_pool().search(query, top_k)

    async def save(self, user_input: str, response: str, metadata: Optional[Dict] = None) -> str:
        return self._get_pool().save_experience(user_input, response, metadata=metadata or {})

    async def count(self) -> int:
        return self._get_pool().count()

    def is_available(self) -> bool:
        try:
            self._get_pool()
            return True
        except Exception:
            return False


_adapters: Dict[str, Any] = {}


class StorageAdapter(StoragePort):
    """DatabaseManager 适配器 — 包装 infrastructure.database_manager.DatabaseManager"""

    def __init__(self, db_path: str = None):
        self._db_path = db_path
        self._db = None

    def _get_db(self):
        if self._db is None and self._db_path:
            from infrastructure.database_manager import DatabaseManager
            self._db = DatabaseManager.get(self._db_path)
        return self._db

    def query(self, sql: str, params: tuple = None):
        return self._get_db().query(sql, params or ())

    def query_one(self, sql: str, params: tuple = None):
        return self._get_db().query_one(sql, params or ())

    def execute(self, sql: str, params: tuple = None, commit: bool = False):
        return self._get_db().execute(sql, params or (), commit=commit)

    def get(self, db_path: str, **kwargs) -> "StoragePort":
        return StorageAdapter(db_path)

    def executescript(self, sql_script: str) -> None:
        db = self._get_db()
        if db and hasattr(db, 'executescript'):
            db.executescript(sql_script)
        else:
            for stmt in sql_script.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self.execute(stmt)

    def is_available(self) -> bool:
        try:
            if self._db_path:
                self._get_db()
                return True
            from infrastructure.database_manager import DatabaseManager
            return True
        except Exception:
            return False


def get_storage_port(db_path: str = None, **kwargs) -> StoragePort:
    key = f"storage:{db_path or 'default'}"
    if key not in _adapters:
        _adapters[key] = StorageAdapter(db_path)
    return _adapters[key]


def get_fact_store_port() -> FactStorePort:
    if "fact_store" not in _adapters:
        _adapters["fact_store"] = FactStoreAdapter()
    return _adapters["fact_store"]


def get_vector_store_port() -> VectorStorePort:
    if "vector_store" not in _adapters:
        _adapters["vector_store"] = VectorStoreAdapter()
    return _adapters["vector_store"]


def get_config_port() -> ConfigPort:
    if "config" not in _adapters:
        _adapters["config"] = ConfigAdapter()
    return _adapters["config"]


def get_knowledge_port() -> KnowledgePort:
    if "knowledge" not in _adapters:
        _adapters["knowledge"] = KnowledgeAdapter()
    return _adapters["knowledge"]


def get_experience_port() -> ExperiencePort:
    if "experience" not in _adapters:
        _adapters["experience"] = ExperienceAdapter()
    return _adapters["experience"]


class ChatHistoryAdapter(ChatHistoryPort):

    def __init__(self, chat_history=None):
        self._ch = chat_history

    def _get_ch(self):
        if self._ch is None:
            from infrastructure.chat_history import get_chat_history
            self._ch = get_chat_history()
        return self._ch

    def create_session(self, session_id: str = None, title: str = "") -> str:
        return self._get_ch().create_session(session_id, title)

    def add_message(self, session_id: str, role: str, content: str,
                    intent: str = "", route: str = "", confidence: float = 0.0,
                    elapsed: float = 0.0, cbnr_summary: str = "") -> int:
        return self._get_ch().add_message(session_id, role, content, intent, route, confidence, elapsed, cbnr_summary)

    def get_sessions(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        return self._get_ch().get_sessions(limit, offset)

    def get_messages(self, session_id: str, limit: int = 100, before_id: int = 0) -> List[Dict]:
        return self._get_ch().get_messages(session_id, limit, before_id)

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        return self._get_ch().search(query, limit)

    def delete_session(self, session_id: str) -> bool:
        return self._get_ch().delete_session(session_id)

    def get_stats(self) -> Dict:
        return self._get_ch().get_stats()

    def is_available(self) -> bool:
        try:
            self._get_ch()
            return True
        except Exception:
            return False


class EventBusAdapter(EventBusPort):

    def __init__(self, bus=None):
        self._bus = bus

    def _get_bus(self):
        if self._bus is None:
            from infrastructure.event_bus import bus
            self._bus = bus
        return self._bus

    def publish(self, event_type: str, data: Dict) -> None:
        self._get_bus().publish(event_type, data)

    def subscribe(self, event_type: str, handler) -> None:
        self._get_bus().subscribe(event_type, handler)

    def get_history(self, event_type: str = None, limit: int = 50) -> List[Dict]:
        bus = self._get_bus()
        if hasattr(bus, 'get_history'):
            return bus.get_history(event_type, limit)
        return []

    def get_stats(self) -> Dict:
        bus = self._get_bus()
        if hasattr(bus, 'get_stats'):
            return bus.get_stats()
        return {"available": True}

    def get_subscriber_count(self, event_type) -> int:
        bus = self._get_bus()
        if hasattr(bus, 'get_subscriber_count'):
            return bus.get_subscriber_count(event_type)
        return 0

    def is_available(self) -> bool:
        try:
            self._get_bus()
            return True
        except Exception:
            return False


def get_chat_history_port() -> ChatHistoryPort:
    if "chat_history" not in _adapters:
        _adapters["chat_history"] = ChatHistoryAdapter()
    return _adapters["chat_history"]


def get_event_bus_port() -> EventBusPort:
    if "event_bus" not in _adapters:
        _adapters["event_bus"] = EventBusAdapter()
    return _adapters["event_bus"]