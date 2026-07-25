"""
FactStore 端口 — 事实锚点存储的抽象接口

任何事实存储实现必须遵循此接口。
当前实现: infrastructure.fact_store.FactStore
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class FactStorePort(ABC):
    """事实锚点存储端口"""

    @abstractmethod
    async def search_by_keywords(self, text: str, limit: int = 10) -> List[Dict]:
        ...

    @abstractmethod
    async def extract_and_store(self, text: str, source: str = "auto") -> int:
        ...

    @abstractmethod
    async def get_negations(self, subject: str) -> List[Dict]:
        ...

    @abstractmethod
    async def mark_used(self, fact_id: int) -> None:
        ...

    @abstractmethod
    def add_assertion(self, question: str = "", subject: str = "",
                      predicate: str = "", obj: str = "",
                      source: str = "auto", confidence: float = 0.9) -> int:
        ...

    @abstractmethod
    def add_correction(self, question: str = "", old_subject: str = "",
                       old_predicate: str = "", old_obj: str = "",
                       new_subject: str = "", new_predicate: str = "",
                       new_obj: str = "", correction_source: str = "user_correction") -> None:
        ...

    @abstractmethod
    def get_stats(self) -> Dict:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...