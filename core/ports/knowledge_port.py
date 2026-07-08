"""
Knowledge 端口 — 知识库的抽象接口

任何知识库实现必须遵循此接口。
当前实现: infrastructure.knowledge_store.KnowledgeStore
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class KnowledgePort(ABC):
    """知识库端口"""

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索知识，返回 [{"content": str, "probability": float, ...}]"""
        ...

    @abstractmethod
    async def store(self, content: str, metadata: Optional[Dict] = None) -> str:
        """存储知识条目，返回ID"""
        ...

    @abstractmethod
    async def count(self) -> int:
        """返回知识条目总数"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """知识库是否可用"""
        ...