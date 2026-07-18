"""
端口协议 — 认知核心与载体之间的抽象接口

Phase 3 核心设计：认知核心不需要知道外界以什么形态连接它，
它只需要知道如何接收输入并生成输出。

三个端口抽象：
1. CognitiveStimulus — 认知刺激（替代 user_input: str）
2. CognitiveResponse — 认知响应（替代 final_response: str）
3. EventSink — 事件接收器（替代 _emit() SSE 推送）
4. NotificationPort — 通知端口（替代 _enqueue_proactivity()）

设计原则：
- 认知核心只依赖协议，不依赖实现
- 每个端口都有默认实现（SSE）和替代实现（Null/Buffered/Log）
- 端口通过构造函数或函数参数注入，不使用全局变量
- 向后兼容：现有代码可以继续使用 user_input/final_response，
  通过适配器转换为端口协议
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable


class StimulusType(Enum):
    USER_MESSAGE = "user_message"
    SYSTEM_EVENT = "system_event"
    SCHEDULED = "scheduled"
    PROACTIVE = "proactive"
    SENSOR = "sensor"
    INTERNAL = "internal"


class ResponseType(Enum):
    TEXT = "text"
    ACTION = "action"
    NOTIFICATION = "notification"
    SILENT = "silent"


@dataclass
class CognitiveStimulus:
    content: str
    stimulus_type: StimulusType = StimulusType.USER_MESSAGE
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    priority: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_user_message(cls, content: str, context: Dict = None, session_id: str = None) -> "CognitiveStimulus":
        return cls(
            content=content,
            stimulus_type=StimulusType.USER_MESSAGE,
            context=context or {},
            session_id=session_id,
            priority=0.5,
        )

    @classmethod
    def from_scheduled(cls, content: str, context: Dict = None) -> "CognitiveStimulus":
        return cls(
            content=content,
            stimulus_type=StimulusType.SCHEDULED,
            context=context or {},
            priority=0.3,
        )

    @classmethod
    def from_internal(cls, content: str, context: Dict = None) -> "CognitiveStimulus":
        return cls(
            content=content,
            stimulus_type=StimulusType.INTERNAL,
            context=context or {},
            priority=0.2,
        )


@dataclass
class CognitiveResponse:
    content: str
    response_type: ResponseType = ResponseType.TEXT
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text(cls, content: str, confidence: float = 0.5, **meta) -> "CognitiveResponse":
        return cls(content=content, response_type=ResponseType.TEXT, confidence=confidence, metadata=meta)

    @classmethod
    def silent(cls, **meta) -> "CognitiveResponse":
        return cls(content="", response_type=ResponseType.SILENT, confidence=0.0, metadata=meta)

    @classmethod
    def notification(cls, content: str, confidence: float = 0.7, **meta) -> "CognitiveResponse":
        return cls(content=content, response_type=ResponseType.NOTIFICATION, confidence=confidence, metadata=meta)


@runtime_checkable
class EventSink(Protocol):
    """
    事件接收器 — 替代 _emit() SSE 推送

    emit() 返回值约定：
    - SSEEventSink 返回 SSE 格式字符串（向后兼容 yield 生成器模式）
    - 其他实现返回 None（认知核心脱离 SSE 独立运行）
    """

    def emit(self, event_type: str, data: dict) -> Optional[str]:
        ...


@runtime_checkable
class NotificationPort(Protocol):
    """
    通知端口 — 替代 _enqueue_proactivity()

    认知核心通过此接口主动向外界发送通知。
    载体层决定通知的传输方式（SSE推送/日志/消息队列）。
    """

    def notify(self, message: str, level: str = "info", **kwargs) -> None:
        ...


class SSEEventSink:
    """SSE事件接收器 — 当前默认实现，生成SSE格式字符串"""

    def emit(self, event_type: str, data: dict) -> str:
        import json
        from backend.services.orchestrator_helpers import SafeEncoder
        return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False, cls=SafeEncoder)}\n\n"


class NullEventSink:
    """空事件接收器 — 认知核心脱离SSE独立运行时使用"""

    def emit(self, event_type: str, data: dict) -> None:
        return None


class BufferedEventSink:
    """缓冲事件接收器 — 批量消费事件"""

    def __init__(self):
        self.events: List[tuple] = []

    def emit(self, event_type: str, data: dict) -> None:
        self.events.append((event_type, data))
        return None

    def clear(self) -> List[tuple]:
        events = self.events[:]
        self.events.clear()
        return events


class LogEventSink:
    """日志事件接收器 — 将认知事件写入日志"""

    def emit(self, event_type: str, data: dict) -> None:
        try:
            from loguru import logger
            logger.debug(f"[EventSink] {event_type}: {str(data)[:200]}")
        except ImportError:
            pass
        return None


class SSENotificationPort:
    """SSE通知端口 — 当前默认实现"""

    def notify(self, message: str, level: str = "info", **kwargs) -> None:
        try:
            from backend.lifespan import _enqueue_proactivity
            _enqueue_proactivity({"type": level, "content": message, **kwargs})
        except ImportError:
            pass


class LogNotificationPort:
    """日志通知端口 — 无SSE时使用"""

    def notify(self, message: str, level: str = "info", **kwargs) -> None:
        try:
            from loguru import logger
            logger.info(f"[NotificationPort:{level}] {message}")
        except ImportError:
            import logging
            logging.getLogger(__name__).info(f"[NotificationPort:{level}] {message}")


class NullNotificationPort:
    """空通知端口 — 静默运行时使用"""

    def notify(self, message: str, level: str = "info", **kwargs) -> None:
        pass