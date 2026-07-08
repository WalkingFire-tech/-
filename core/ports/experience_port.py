"""
Experience 端口 — 经验池的抽象接口

任何经验池实现必须遵循此接口。
当前实现: infrastructure.experience_pool.ExperiencePool
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class ExperiencePort(ABC):
    """经验池端口"""

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索经验，返回 [{"raw_input": str, "response": str, "similarity": float, ...}]"""
        ...

    @abstractmethod
    async def save(self, user_input: str, response: str, metadata: Optional[Dict] = None) -> str:
        """保存经验条目，返回ID"""
        ...

    @abstractmethod
    async def count(self) -> int:
        """返回经验条目总数"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """经验池是否可用"""
        ...