"""
VectorStore 端口 — 向量检索的抽象接口

任何向量检索实现必须遵循此接口。
当前实现: infrastructure.vector_retriever.VectorRetriever
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class VectorStorePort(ABC):
    """向量检索端口"""

    @abstractmethod
    async def search(self, query: str, k: int = 3, threshold: float = 0.3) -> List[Dict]:
        """搜索相似内容，返回 [{"text": str, "probability": float, "source": str, ...}]"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """向量检索是否可用（不可用时调用方降级到 SQLite LIKE）"""
        ...

    @abstractmethod
    async def index_count(self) -> int:
        """返回索引中的记录数"""
        ...