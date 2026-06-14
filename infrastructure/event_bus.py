"""
简单的事件总线（观察者模式）
用于解耦各个服务
"""
import threading
from typing import Dict, List, Callable, Any
from loguru import logger

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
        logger.debug(f"订阅事件: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅事件"""
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"取消订阅事件: {event_type}")
                except ValueError:
                    pass

    def publish(self, event_type: str, data: Any = None):
        """发布事件"""
        with self._lock:
            if event_type not in self._subscribers:
                return
            callbacks = list(self._subscribers[event_type])
        
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"处理事件 {event_type} 时出错: {e}")

# 全局事件总线实例
bus = EventBus()
