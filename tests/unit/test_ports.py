"""
P3-Phase3: 端口协议测试

验证：
1. CognitiveStimulus 创建与类型
2. CognitiveResponse 工厂方法
3. EventSink 协议实现
4. NotificationPort 协议实现
5. 向后兼容性（from_user_message）
"""
import pytest
from core.ports import (
    CognitiveStimulus, CognitiveResponse, StimulusType, ResponseType,
    SSEEventSink, NullEventSink, BufferedEventSink, LogEventSink,
    SSENotificationPort, LogNotificationPort, NullNotificationPort,
    EventSink, NotificationPort,
)


class TestCognitiveStimulus:
    def test_from_user_message(self):
        s = CognitiveStimulus.from_user_message("你好", session_id="s1")
        assert s.content == "你好"
        assert s.stimulus_type == StimulusType.USER_MESSAGE
        assert s.session_id == "s1"

    def test_from_scheduled(self):
        s = CognitiveStimulus.from_scheduled("定时检查", context={"task": "health"})
        assert s.stimulus_type == StimulusType.SCHEDULED
        assert s.priority == 0.3

    def test_from_internal(self):
        s = CognitiveStimulus.from_internal("内部事件")
        assert s.stimulus_type == StimulusType.INTERNAL
        assert s.priority == 0.2

    def test_default_type(self):
        s = CognitiveStimulus(content="test")
        assert s.stimulus_type == StimulusType.USER_MESSAGE

    def test_stimulus_types(self):
        assert StimulusType.USER_MESSAGE.value == "user_message"
        assert StimulusType.SYSTEM_EVENT.value == "system_event"
        assert StimulusType.SENSOR.value == "sensor"
        assert StimulusType.INTERNAL.value == "internal"


class TestCognitiveResponse:
    def test_text_response(self):
        r = CognitiveResponse.text("回答内容", confidence=0.9)
        assert r.content == "回答内容"
        assert r.response_type == ResponseType.TEXT
        assert r.confidence == 0.9

    def test_silent_response(self):
        r = CognitiveResponse.silent()
        assert r.content == ""
        assert r.response_type == ResponseType.SILENT

    def test_notification_response(self):
        r = CognitiveResponse.notification("系统通知", confidence=0.8)
        assert r.response_type == ResponseType.NOTIFICATION

    def test_response_types(self):
        assert ResponseType.TEXT.value == "text"
        assert ResponseType.ACTION.value == "action"
        assert ResponseType.SILENT.value == "silent"


class TestEventSinkImplementations:
    def test_null_sink(self):
        sink = NullEventSink()
        result = sink.emit("step", {"phase": "test"})
        assert result is None

    def test_buffered_sink(self):
        sink = BufferedEventSink()
        sink.emit("step", {"phase": "a"})
        sink.emit("result", {"response": "b"})
        assert len(sink.events) == 2
        assert sink.events[0] == ("step", {"phase": "a"})
        cleared = sink.clear()
        assert len(cleared) == 2
        assert len(sink.events) == 0

    def test_log_sink(self):
        sink = LogEventSink()
        sink.emit("step", {"phase": "test"})

    def test_sse_sink_format(self):
        sink = SSEEventSink()
        result = sink.emit("result", {"response": "hello"})
        assert result.startswith("data: ")
        assert "result" in result
        assert "hello" in result

    def test_null_sink_satisfies_protocol(self):
        sink = NullEventSink()
        assert isinstance(sink, EventSink)

    def test_buffered_sink_satisfies_protocol(self):
        sink = BufferedEventSink()
        assert isinstance(sink, EventSink)


class TestNotificationPortImplementations:
    def test_null_port(self):
        port = NullNotificationPort()
        port.notify("test message")

    def test_log_port(self):
        port = LogNotificationPort()
        port.notify("test message", level="warning")

    def test_null_port_satisfies_protocol(self):
        port = NullNotificationPort()
        assert isinstance(port, NotificationPort)

    def test_log_port_satisfies_protocol(self):
        port = LogNotificationPort()
        assert isinstance(port, NotificationPort)


class TestBackwardCompatibility:
    def test_stimulus_from_string(self):
        s = CognitiveStimulus.from_user_message("用户消息")
        assert s.content == "用户消息"
        assert s.stimulus_type == StimulusType.USER_MESSAGE

    def test_response_to_string(self):
        r = CognitiveResponse.text("回复内容")
        assert r.content == "回复内容"