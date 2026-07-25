from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ChatHistoryPort(ABC):

    @abstractmethod
    def create_session(self, session_id: str = None, title: str = "") -> str:
        ...

    @abstractmethod
    def add_message(self, session_id: str, role: str, content: str,
                    intent: str = "", route: str = "", confidence: float = 0.0,
                    elapsed: float = 0.0, cbnr_summary: str = "") -> int:
        ...

    @abstractmethod
    def get_sessions(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        ...

    @abstractmethod
    def get_messages(self, session_id: str, limit: int = 100, before_id: int = 0) -> List[Dict]:
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        ...

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        ...

    @abstractmethod
    def get_stats(self) -> Dict:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...