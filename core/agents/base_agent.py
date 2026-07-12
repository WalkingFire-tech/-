"""
Agent基类 - 所有Agent角色的抽象接口
"""
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    event_type: str
    payload: Dict
    message_id: str = ""
    timestamp: float = 0.0
    correlation_id: str = ""

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class Plan:
    plan_id: str
    query: str
    intent_type: str
    steps: List[Dict]
    priority: str = "normal"
    context: Dict = field(default_factory=dict)
    created_at: float = 0.0
    replan_count: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())[:8]


@dataclass
class ExecutionResult:
    plan_id: str
    success: bool
    response: str
    source: str
    quality: float
    attempts: List = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class ReflectionFeedback:
    plan_id: str
    execution_id: str
    quality_score: float
    needs_replan: bool
    lessons: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class BaseAgent:
    def __init__(self, agent_id: str, role: str):
        self.agent_id = agent_id
        self.role = role
        self.state = AgentState.IDLE
        self._message_handlers: Dict[str, callable] = {}
        self._history: List[AgentMessage] = []
        self._stats = {"messages_sent": 0, "messages_received": 0, "errors": 0}

    def send_message(self, event_type: str, payload: Dict,
                     recipient: str = "", correlation_id: str = "") -> AgentMessage:
        msg = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._history.append(msg)
        self._stats["messages_sent"] += 1

        try:
            from infrastructure.event_bus import bus
            bus.publish(event_type, {
                "sender": self.agent_id,
                "recipient": recipient,
                "payload": payload,
                "message_id": msg.message_id,
                "correlation_id": correlation_id,
                "timestamp": msg.timestamp,
            })
        except Exception as e:
            logger.error(f"Agent {self.agent_id} 发送消息失败: {e}")

        return msg

    def receive_message(self, event_type: str, handler: callable):
        self._message_handlers[event_type] = handler
        try:
            from infrastructure.event_bus import bus
            bus.subscribe(event_type, handler)
        except Exception as e:
            logger.error(f"Agent {self.agent_id} 订阅事件失败: {e}")

    def handle_event(self, event_data: Dict):
        event_type = event_data.get("event_type", "")
        if event_type in self._message_handlers:
            try:
                self._message_handlers[event_type](event_data)
                self._stats["messages_received"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Agent {self.agent_id} 处理事件失败: {e}")

    def get_stats(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "state": self.state.value,
            **self._stats,
        }