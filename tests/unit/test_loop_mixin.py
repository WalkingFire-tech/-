"""
LoopMixin 测试 — 验证闭环混入工具的冷却恢复、指标、缓存、异常容忍
"""
import time
import asyncio
import pytest
from core.loop_mixin import LoopMixin, AsyncLoopMixin, LoopStatus


class SimpleEngine(LoopMixin):
    def __init__(self, **kwargs):
        super().__init__(name="test_engine", **kwargs)
        self.cycle_count = 0
        self.should_fail = False

    def run(self):
        with self.loop_context():
            if self.should_fail:
                raise RuntimeError("intentional failure")
            self.cycle_count += 1
            return "ok"


class SimpleAsyncEngine(AsyncLoopMixin):
    def __init__(self, **kwargs):
        super().__init__(name="test_async_engine", **kwargs)
        self.cycle_count = 0
        self.should_fail = False

    async def run(self):
        async with self.async_loop_context():
            if self.should_fail:
                raise RuntimeError("intentional async failure")
            self.cycle_count += 1
            return "ok"


class TestLoopMixin:
    def test_normal_cycle(self):
        engine = SimpleEngine()
        result = engine.run()
        assert result == "ok"
        assert engine.cycle_count == 1
        assert engine.loop_status == LoopStatus.IDLE
        assert engine.loop_metrics.success_cycles == 1

    def test_metrics_tracking(self):
        engine = SimpleEngine()
        engine.run()
        engine.run()
        assert engine.loop_metrics.total_cycles == 2
        assert engine.loop_metrics.success_cycles == 2
        assert engine.loop_metrics.failed_cycles == 0

    def test_failure_tracking(self):
        engine = SimpleEngine(max_failures_before_degraded=3)
        engine.should_fail = True
        engine.run()
        assert engine.loop_metrics.failed_cycles == 1
        assert engine.loop_status == LoopStatus.FAILED

    def test_degraded_after_consecutive_failures(self):
        engine = SimpleEngine(max_failures_before_degraded=2)
        engine.should_fail = True
        engine.run()
        assert engine.loop_status == LoopStatus.FAILED
        engine.run()
        assert engine.loop_status == LoopStatus.DEGRADED
        assert engine.loop_metrics.degraded_cycles == 1

    def test_force_recover(self):
        engine = SimpleEngine(max_failures_before_degraded=1)
        engine.should_fail = True
        engine.run()
        assert engine.loop_status == LoopStatus.DEGRADED
        engine.force_recover()
        assert engine.loop_status == LoopStatus.IDLE

    def test_cooldown_recovery(self):
        engine = SimpleEngine(max_failures_before_degraded=1, cooldown_seconds=0.0)
        engine.should_fail = True
        engine.run()
        assert engine.loop_status == LoopStatus.DEGRADED
        engine.should_fail = False
        engine.run()
        assert engine.loop_status in (LoopStatus.RECOVERING, LoopStatus.IDLE)

    def test_exception_tolerance(self):
        engine = SimpleEngine()
        engine.should_fail = True
        result = engine.run()
        assert result is None  # exception suppressed
        assert engine.loop_metrics.failed_cycles == 1

    def test_snapshot(self):
        engine = SimpleEngine()
        engine.run()
        snap = engine.get_loop_snapshot()
        assert snap["name"] == "test_engine"
        assert snap["status"] == "idle"
        assert snap["total_cycles"] == 1
        assert snap["success_rate"] == 1.0

    def test_cache(self):
        engine = SimpleEngine()
        engine._cache_ttl_seconds = 10.0
        engine._set_cached("key1", "value1")
        assert engine._get_cached("key1") == "value1"

    def test_cache_expired(self):
        engine = SimpleEngine()
        engine._cache_ttl_seconds = 0.001
        engine._set_cached("key1", "value1")
        time.sleep(0.01)
        assert engine._get_cached("key1") is None

    def test_cache_disabled(self):
        engine = SimpleEngine()
        engine._cache_ttl_seconds = 0.0
        engine._set_cached("key1", "value1")
        assert engine._get_cached("key1") is None


class TestAsyncLoopMixin:
    def test_async_normal_cycle(self):
        engine = SimpleAsyncEngine()
        result = asyncio.get_event_loop().run_until_complete(engine.run())
        assert result == "ok"
        assert engine.cycle_count == 1
        assert engine.loop_status == LoopStatus.IDLE
        assert engine.loop_metrics.success_cycles == 1

    def test_async_metrics_tracking(self):
        engine = SimpleAsyncEngine()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(engine.run())
        loop.run_until_complete(engine.run())
        assert engine.loop_metrics.total_cycles == 2
        assert engine.loop_metrics.success_cycles == 2

    def test_async_failure_tracking(self):
        engine = SimpleAsyncEngine(max_failures_before_degraded=3)
        engine.should_fail = True
        asyncio.get_event_loop().run_until_complete(engine.run())
        assert engine.loop_metrics.failed_cycles == 1
        assert engine.loop_status == LoopStatus.FAILED

    def test_async_degraded_after_consecutive_failures(self):
        engine = SimpleAsyncEngine(max_failures_before_degraded=2)
        engine.should_fail = True
        loop = asyncio.get_event_loop()
        loop.run_until_complete(engine.run())
        assert engine.loop_status == LoopStatus.FAILED
        loop.run_until_complete(engine.run())
        assert engine.loop_status == LoopStatus.DEGRADED

    def test_async_force_recover(self):
        engine = SimpleAsyncEngine(max_failures_before_degraded=1)
        engine.should_fail = True
        asyncio.get_event_loop().run_until_complete(engine.run())
        assert engine.loop_status == LoopStatus.DEGRADED
        engine.force_recover()
        assert engine.loop_status == LoopStatus.IDLE

    def test_async_exception_tolerance(self):
        engine = SimpleAsyncEngine()
        engine.should_fail = True
        result = asyncio.get_event_loop().run_until_complete(engine.run())
        assert result is None
        assert engine.loop_metrics.failed_cycles == 1

    def test_async_snapshot(self):
        engine = SimpleAsyncEngine()
        asyncio.get_event_loop().run_until_complete(engine.run())
        snap = engine.get_loop_snapshot()
        assert snap["name"] == "test_async_engine"
        assert snap["status"] == "idle"
        assert snap["total_cycles"] == 1
        assert snap["success_rate"] == 1.0

    def test_async_cache(self):
        engine = SimpleAsyncEngine()
        engine._cache_ttl_seconds = 10.0
        engine._set_cached("akey", "aval")
        assert engine._get_cached("akey") == "aval"

    def test_async_cooldown_recovery(self):
        engine = SimpleAsyncEngine(max_failures_before_degraded=1, cooldown_seconds=0.0)
        engine.should_fail = True
        loop = asyncio.get_event_loop()
        loop.run_until_complete(engine.run())
        assert engine.loop_status == LoopStatus.DEGRADED
        engine.should_fail = False
        loop.run_until_complete(engine.run())
        assert engine.loop_status in (LoopStatus.RECOVERING, LoopStatus.IDLE)