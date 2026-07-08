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
        """按关键词搜索事实，返回 [{"subject": str, "predicate": str, "object": str, "confidence": float, ...}]"""
        ...

    @abstractmethod
    async def extract_and_store(self, text: str, source: str = "auto") -> int:
        """从文本中提取三元组并存储，返回新增数量"""
        ...

    @abstractmethod
    async def get_negations(self, subject: str) -> List[Dict]:
        """获取某主体的否定事实"""
        ...

    @abstractmethod
    async def mark_used(self, fact_id: int) -> None:
        """标记事实已被使用（用于优先级追踪）"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """事实存储是否可用"""
        ...