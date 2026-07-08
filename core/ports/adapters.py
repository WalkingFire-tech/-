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
    """ConfigManager 适配器 — 包装 infrastructure.config_manager"""

    def __init__(self, manager=None):
        self._manager = manager

    def _get_manager(self):
        if self._manager is None:
            from infrastructure.config_manager import config_manager
            self._manager = config_manager
        return self._manager

    def get(self, key: str, default: Any = None) -> Any:
        return self._get_manager().get(key, default)

    def get_section(self, name: str) -> Dict:
        return self._get_manager().get_section(name)

    def set(self, key: str, value: Any) -> None:
        self._get_manager().set(key, value)

    def is_available(self) -> bool:
        try:
            self._get_manager()
            return True
        except Exception:
            return False


class KnowledgeAdapter(KnowledgePort):
    """KnowledgeStore 适配器 — 包装 infrastructure.knowledge_store"""

    def __init__(self, store=None):
        self._store = store

    def _get_store(self):
        if self._store is None:
            from infrastructure.knowledge_store import knowledge_store
            self._store = knowledge_store
        return self._store

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        return self._get_store().search(query, top_k)

    async def store(self, content: str, metadata: Optional[Dict] = None) -> str:
        return self._get_store().add_knowledge(content, metadata=metadata or {})

    async def count(self) -> int:
        return self._get_store().count()

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