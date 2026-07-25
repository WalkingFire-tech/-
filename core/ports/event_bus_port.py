from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EventBusPort(ABC):

    @abstractmethod
    def publish(self, event_type: str, data: Dict) -> None:
        ...

    @abstractmethod
    def subscribe(self, event_type: str, handler) -> None:
        ...

    @abstractmethod
    def get_history(self, event_type: str = None, limit: int = 50) -> List[Dict]:
        ...

    @abstractmethod
    def get_stats(self) -> Dict:
        ...

    @abstractmethod
    def get_subscriber_count(self, event_type) -> int:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...