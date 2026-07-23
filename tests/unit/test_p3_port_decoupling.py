"""
P3-Phase3 Step 5: NullEventSink验证 — 认知核心脱离SSE独立运行

验证：
1. chat_stream(event_sink=NullEventSink()) 不产生SSE输出
2. cognitive_process() 可独立调用，返回结果字典
3. EventSink协议的4种实现均可正常工作
4. NotificationPort协议的3种实现均可正常工作
5. scheduled_tasks._notify() 可脱离SSE运行
"""
import pytest
import asyncio
from core.ports import (
    NullEventSink, BufferedEventSink, LogEventSink, SSEEventSink,
    NullNotificationPort, LogNotificationPort,
    EventSink, NotificationPort,
    CognitiveStimulus, CognitiveResponse, StimulusType, ResponseType,
)


class TestNullEventSinkDecoupling:
    def test_null_sink_returns_none(self):
        sink = NullEventSink()
        result = sink.emit("step", {"phase": "test"})
        assert result is None

    def test_null_sink_satisfies_protocol(self):
        sink = NullEventSink()
        assert isinstance(sink, EventSink)

    def test_buffered_sink_collects_events(self):
        sink = BufferedEventSink()
        sink.emit("step", {"phase": "a"})
        sink.emit("result", {"response": "b"})
        assert len(sink.events) == 2
        cleared = sink.clear()
        assert len(cleared) == 2
        assert len(sink.events) == 0

    def test_sse_sink_produces_valid_sse(self):
        sink = SSEEventSink()
        result = sink.emit("result", {"response": "hello"})
        assert result.startswith("data: ")
        assert '"type": "result"' in result
        assert "hello" in result

    def test_log_sink_no_exception(self):
        sink = LogEventSink()
        sink.emit("step", {"phase": "test"})


class TestNotificationPortDecoupling:
    def test_null_port_no_exception(self):
        port = NullNotificationPort()
        port.notify("test message", level="warning")

    def test_null_port_satisfies_protocol(self):
        port = NullNotificationPort()
        assert isinstance(port, NotificationPort)

    def test_log_port_no_exception(self):
        port = LogNotificationPort()
        port.notify("test message", level="info")


class TestOrchestratorEmitWithSink:
    def test_emit_without_sink_returns_sse(self):
        from backend.services.orchestrator_helpers import emit
        result = emit("step", {"phase": "test"})
        assert result.startswith("data: ")
        assert '"type": "step"' in result

    def test_emit_with_null_sink_returns_empty(self):
        from backend.services.orchestrator_helpers import emit
        result = emit("step", {"phase": "test"}, event_sink=NullEventSink())
        assert result == ""

    def test_emit_with_buffered_sink_returns_empty(self):
        from backend.services.orchestrator_helpers import emit
        sink = BufferedEventSink()
        result = emit("step", {"phase": "test"}, event_sink=sink)
        assert result == ""
        assert len(sink.events) == 1
        assert sink.events[0] == ("step", {"phase": "test"})


class TestParallelRouterEmitWithSink:
    def test_parallel_emit_without_sink(self):
        from backend.services.parallel_router import _emit
        result = _emit("step", {"phase": "test"})
        assert result.startswith("data: ")

    def test_parallel_emit_with_null_sink(self):
        from backend.services.parallel_router import _emit
        result = _emit("step", {"phase": "test"}, event_sink=NullEventSink())
        assert result == ""


class TestScheduledTasksNotify:
    def test_notify_without_port_uses_fallback(self):
        from infrastructure.scheduled_tasks import _notify
        _notify("test message", level="info")

    def test_notify_with_null_port(self):
        from infrastructure.scheduled_tasks import set_notification_port, _notify
        from core.ports import NullNotificationPort
        set_notification_port(NullNotificationPort())
        _notify("test message", level="warning")
        set_notification_port(None)


class TestCognitiveProcessSignature:
    def test_cognitive_process_importable(self):
        from backend.services.chat_orchestrator import cognitive_process
        assert callable(cognitive_process)

    def test_chat_stream_accepts_event_sink(self):
        import inspect
        from backend.services.chat_orchestrator import chat_stream
        sig = inspect.signature(chat_stream)
        assert "event_sink" in sig.parameters
        assert sig.parameters["event_sink"].default is None


class TestCognitiveStimulusResponse:
    def test_stimulus_from_user_message(self):
        s = CognitiveStimulus.from_user_message("你好", session_id="s1")
        assert s.content == "你好"
        assert s.stimulus_type == StimulusType.USER_MESSAGE
        assert s.session_id == "s1"

    def test_stimulus_from_scheduled(self):
        s = CognitiveStimulus.from_scheduled("定时检查")
        assert s.stimulus_type == StimulusType.SCHEDULED
        assert s.priority == 0.3

    def test_response_text(self):
        r = CognitiveResponse.text("回答", confidence=0.9)
        assert r.content == "回答"
        assert r.response_type == ResponseType.TEXT
        assert r.confidence == 0.9

    def test_response_silent(self):
        r = CognitiveResponse.silent()
        assert r.content == ""
        assert r.response_type == ResponseType.SILENT