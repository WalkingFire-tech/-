"""
简单的事件总线（观察者模式）
用于解耦各个服务

核心事件类型（P1-1 事件驱动感知框架）：
- UserMessage: 用户消息到达
- ToolResult: 工具执行结果
- KnowledgeUpdate: 知识库更新
- ModelStatusChange: 模型状态变化
- ScheduledTask: 定时任务触发
- IdlePeriod: 空闲期触发（存在层发布）
- SystemHealth: 系统健康状态变化
"""
import threading
from typing import Dict, List, Callable, Any
from loguru import logger


class EventTypes:
    UserMessage = "UserMessage"
    ToolResult = "ToolResult"
    KnowledgeUpdate = "KnowledgeUpdate"
    ModelStatusChange = "ModelStatusChange"
    ScheduledTask = "ScheduledTask"
    IdlePeriod = "IdlePeriod"
    SystemHealth = "SystemHealth"


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._history: List[Dict] = []
        self._max_history = 200

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
        logger.debug(f"订阅事件: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"取消订阅事件: {event_type}")
                except ValueError:
                    pass

    def publish(self, event_type: str, data: Any = None):
        with self._lock:
            if event_type not in self._subscribers:
                self._record(event_type, data, delivered=0)
                return
            callbacks = list(self._subscribers[event_type])

        delivered = 0
        for callback in callbacks:
            try:
                callback(data)
                delivered += 1
            except Exception as e:
                logger.error(f"处理事件 {event_type} 时出错: {e}")

        self._record(event_type, data, delivered=delivered)

    def _record(self, event_type: str, data: Any, delivered: int = 0):
        import time
        record = {
            "type": event_type,
            "data": str(data)[:200] if data else None,
            "delivered": delivered,
            "timestamp": time.time(),
        }
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(self, event_type: str = None, limit: int = 20) -> List[Dict]:
        with self._lock:
            events = self._history
            if event_type:
                events = [e for e in events if e["type"] == event_type]
            return events[-limit:]

    def get_subscriber_count(self, event_type: str) -> int:
        with self._lock:
            return len(self._subscribers.get(event_type, []))

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = {}
            for evt_type, callbacks in self._subscribers.items():
                stats[evt_type] = {
                    "subscribers": len(callbacks),
                    "recent_count": sum(1 for e in self._history if e["type"] == evt_type),
                }
            return stats


bus = EventBus()
