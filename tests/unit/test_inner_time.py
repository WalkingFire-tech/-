"""
内在时间引擎单元测试
"""
import pytest
import time
from unittest.mock import patch
from core.presence.inner_time import (
    InnerTimeEngine, CognitiveTick, CognitiveEventType,
    SubjectiveTimeState, inner_time_engine,
)


@pytest.fixture(autouse=True)
def clean_engine():
    inner_time_engine.reset()
    yield
    inner_time_engine.reset()


class TestCognitiveEventType:
    def test_all_types(self):
        types = [t.value for t in CognitiveEventType]
        assert "perceive" in types
        assert "reason" in types
        assert "learn" in types
        assert "output" in types
        assert "reflect" in types
        assert "explore" in types
        assert "self_modify" in types


class TestCognitiveTick:
    def test_creation(self):
        ct = CognitiveTick(event_type=CognitiveEventType.PERCEIVE, wall_time=1.0)
        assert ct.event_type == CognitiveEventType.PERCEIVE
        assert ct.intensity == 1.0

    def test_to_dict(self):
        ct = CognitiveTick(event_type=CognitiveEventType.LEARN, wall_time=1.0, intensity=0.5)
        d = ct.to_dict()
        assert d["event_type"] == "learn"
        assert d["intensity"] == 0.5


class TestSubjectiveTimeState:
    def test_defaults(self):
        s = SubjectiveTimeState()
        assert s.tick_count == 0
        assert s.flow_rate == 1.0
        assert s.rhythm_bpm == 60.0
        assert s.current_phase == "awake"

    def test_to_dict(self):
        s = SubjectiveTimeState(tick_count=10, flow_rate=2.0)
        d = s.to_dict()
        assert d["tick_count"] == 10
        assert d["flow_rate"] == 2.0


class TestInnerTimeEngine:
    def test_tick_records_event(self):
        engine = InnerTimeEngine()
        ct = engine.tick(CognitiveEventType.PERCEIVE, intensity=0.8)
        assert ct.event_type == CognitiveEventType.PERCEIVE
        assert ct.intensity == 0.8

    def test_tick_count(self):
        engine = InnerTimeEngine()
        engine.tick(CognitiveEventType.PERCEIVE)
        engine.tick(CognitiveEventType.REASON)
        state = engine.get_state()
        assert state.tick_count == 2

    def test_density_increases_with_ticks(self):
        engine = InnerTimeEngine()
        state0 = engine.get_state()
        assert state0.cognitive_density == 0.0

        for _ in range(10):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        state1 = engine.get_state()
        assert state1.cognitive_density > 0

    def test_flow_rate_high_density(self):
        engine = InnerTimeEngine()
        for _ in range(20):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        state = engine.get_state()
        assert state.flow_rate > 1.0

    def test_flow_rate_low_density(self):
        engine = InnerTimeEngine()
        state = engine.get_state()
        assert state.flow_rate == 0.1

    def test_flow_rate_bounds(self):
        engine = InnerTimeEngine()
        for _ in range(50):
            engine.tick(CognitiveEventType.REASON, intensity=2.0)
        state = engine.get_state()
        assert state.flow_rate <= 10.0
        assert state.flow_rate >= 0.1

    def test_rhythm_high_density(self):
        engine = InnerTimeEngine()
        for _ in range(20):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        state = engine.get_state()
        assert state.rhythm_bpm > 60.0

    def test_rhythm_low_density(self):
        engine = InnerTimeEngine()
        state = engine.get_state()
        assert state.rhythm_bpm < 60.0

    def test_rhythm_bounds(self):
        engine = InnerTimeEngine()
        for _ in range(50):
            engine.tick(CognitiveEventType.REASON, intensity=2.0)
        state = engine.get_state()
        assert state.rhythm_bpm <= 180.0
        assert state.rhythm_bpm >= 20.0

    def test_phase_awake_high_density(self):
        engine = InnerTimeEngine()
        for _ in range(30):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        state = engine.get_state()
        assert state.current_phase == "awake"

    def test_phase_sleeping_no_ticks(self):
        engine = InnerTimeEngine()
        state = engine.get_state()
        assert state.current_phase == "sleeping"

    def test_phase_perceiving(self):
        engine = InnerTimeEngine()
        for _ in range(8):
            engine.tick(CognitiveEventType.PERCEIVE, intensity=0.7)
        state = engine.get_state()
        assert state.current_phase in ("awake", "perceiving", "growing")

    def test_get_tick_interval(self):
        engine = InnerTimeEngine()
        for _ in range(20):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        interval = engine.get_tick_interval()
        assert interval > 0
        assert interval < 60

    def test_get_tick_interval_idle(self):
        engine = InnerTimeEngine()
        interval = engine.get_tick_interval()
        assert interval >= 1.0

    def test_get_timeline(self):
        engine = InnerTimeEngine()
        engine.tick(CognitiveEventType.PERCEIVE, description="test event")
        timeline = engine.get_timeline()
        assert len(timeline) == 1
        assert timeline[0]["event"] == "perceive"
        assert "test event" in timeline[0]["description"]

    def test_get_timeline_limit(self):
        engine = InnerTimeEngine()
        for i in range(60):
            engine.tick(CognitiveEventType.REASON, description=f"event_{i}")
        timeline = engine.get_timeline(limit=10)
        assert len(timeline) == 10

    def test_get_time_since_last_tick(self):
        engine = InnerTimeEngine()
        engine.tick(CognitiveEventType.PERCEIVE)
        elapsed = engine.get_time_since_last_tick()
        assert elapsed >= 0

    def test_get_subjective_elapsed(self):
        engine = InnerTimeEngine()
        for _ in range(10):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        subjective = engine.get_subjective_elapsed()
        assert subjective >= 0

    def test_reset(self):
        engine = InnerTimeEngine()
        engine.tick(CognitiveEventType.PERCEIVE)
        engine.tick(CognitiveEventType.REASON)
        engine.reset()
        state = engine.get_state()
        assert state.tick_count == 0

    def test_intensity_clamped(self):
        engine = InnerTimeEngine()
        ct = engine.tick(CognitiveEventType.REASON, intensity=5.0)
        assert ct.intensity == 2.0
        ct2 = engine.tick(CognitiveEventType.REASON, intensity=-1.0)
        assert ct2.intensity == 0.0

    def test_max_tick_window(self):
        engine = InnerTimeEngine(max_window=10)
        for _ in range(20):
            engine.tick(CognitiveEventType.REASON)
        state = engine.get_state()
        assert state.tick_count == 10

    def test_multiple_event_types(self):
        engine = InnerTimeEngine()
        engine.tick(CognitiveEventType.PERCEIVE)
        engine.tick(CognitiveEventType.REASON)
        engine.tick(CognitiveEventType.LEARN)
        engine.tick(CognitiveEventType.OUTPUT)
        state = engine.get_state()
        assert state.tick_count == 4

    def test_phase_transitions_with_density(self):
        engine = InnerTimeEngine()
        state0 = engine.get_state()
        assert state0.current_phase == "sleeping"

        engine.tick(CognitiveEventType.PERCEIVE, intensity=0.3)
        state1 = engine.get_state()
        assert state1.current_phase in ("resting", "growing", "perceiving", "awake")

        for _ in range(20):
            engine.tick(CognitiveEventType.REASON, intensity=1.0)
        state2 = engine.get_state()
        assert state2.current_phase == "awake"


class TestExistenceLayerInnerTimeIntegration:
    def test_existence_layer_has_inner_time(self):
        from core.presence.existence_layer import ExistenceLayer
        layer = ExistenceLayer()
        assert layer.inner_time is not None

    def test_update_state_uses_inner_time(self):
        from core.presence.existence_layer import ExistenceLayer, PresenceState
        layer = ExistenceLayer()
        layer.inner_time.tick(CognitiveEventType.PERCEIVE, intensity=1.0)
        for _ in range(20):
            layer.inner_time.tick(CognitiveEventType.REASON, intensity=1.0)
        layer._update_state(silence=0)
        assert layer.state == PresenceState.AWAKE

    def test_update_state_fallback_no_inner_time(self):
        from core.presence.existence_layer import ExistenceLayer, PresenceState
        layer = ExistenceLayer()
        layer.inner_time = None
        layer._update_state(silence=0)
        assert layer.state == PresenceState.AWAKE
        layer._update_state(silence=200)
        assert layer.state == PresenceState.RESTING

    def test_user_interaction_ticks_perceive(self):
        from core.presence.existence_layer import ExistenceLayer
        layer = ExistenceLayer()
        before = layer.inner_time.get_state().tick_count
        layer.user_interaction()
        after = layer.inner_time.get_state().tick_count
        assert after > before

    def test_get_status_includes_inner_time(self):
        from core.presence.existence_layer import ExistenceLayer
        layer = ExistenceLayer()
        status = layer.get_status()
        assert "inner_time" in status
        assert "cognitive_density" in status["inner_time"]

    def test_heartbeat_ticks_perceive(self):
        from core.presence.existence_layer import ExistenceLayer
        layer = ExistenceLayer()
        before = layer.inner_time.get_state().tick_count
        layer._heartbeat()
        after = layer.inner_time.get_state().tick_count
        assert after > before

    def test_grow_ticks_learn(self):
        from core.presence.existence_layer import ExistenceLayer, PresenceState
        layer = ExistenceLayer()
        layer.state = PresenceState.GROWING
        before = layer.inner_time.get_state().tick_count
        layer._grow()
        after = layer.inner_time.get_state().tick_count
        assert after > before

    def test_phase_driven_by_inner_rhythm(self):
        from core.presence.existence_layer import ExistenceLayer, PresenceState
        layer = ExistenceLayer()
        layer._update_state(silence=0)
        assert layer.state == PresenceState.SLEEPING
        for _ in range(30):
            layer.inner_time.tick(CognitiveEventType.PERCEIVE, intensity=1.0)
        layer._update_state(silence=0)
        assert layer.state == PresenceState.AWAKE