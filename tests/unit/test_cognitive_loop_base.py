"""
CognitiveLoopBase / HealthLoop / LearningLoop 测试
"""
import asyncio
import time
import pytest
from core.cognitive_loop_base import (
    CognitiveLoopBase, HealthLoop, LearningLoop,
    LoopPhase, LoopStatus, LoopResult,
)


class SimpleHealthLoop(HealthLoop):
    def __init__(self, **kwargs):
        super().__init__(name="test_health", **kwargs)
        self.health_value = 0.9
        self.mode_applied = None
        self.recorded = []

    async def _check_health(self) -> float:
        return self.health_value

    async def _compute_mode(self, health: float):
        if health < 0.3:
            return "emergency"
        elif health < 0.7:
            return "conservative"
        return "normal"

    async def _apply_mode(self, mode):
        self.mode_applied = mode
        return mode

    async def _record_health(self, health: float, mode):
        self.recorded.append((health, mode))


class SimpleLearningLoop(LearningLoop):
    def __init__(self, **kwargs):
        super().__init__(name="test_learning", **kwargs)
        self.detected = None
        self.evaluated = None
        self.remediated = None
        self.learned = None

    async def _detect(self):
        self.detected = "gap_found"
        return self.detected

    async def _evaluate(self, detection):
        self.evaluated = f"eval_{detection}"
        return self.evaluated

    async def _remediate(self, evaluation):
        self.remediated = f"fix_{evaluation}"
        return self.remediated

    async def _learn(self, detection, evaluation, remediation):
        self.learned = f"learned_{detection}_{evaluation}_{remediation}"


class FailingLoop(HealthLoop):
    def __init__(self, **kwargs):
        super().__init__(name="test_failing", **kwargs)
        self.fail_count = 0

    async def _check_health(self) -> float:
        self.fail_count += 1
        raise RuntimeError("health check failed")

    async def _compute_mode(self, health: float):
        return "normal"

    async def _apply_mode(self, mode):
        return mode

    async def _record_health(self, health: float, mode):
        pass


class TestHealthLoop:
    @pytest.mark.asyncio
    async def test_normal_cycle(self):
        loop = SimpleHealthLoop()
        result = await loop.run_cycle()
        assert result.error is None
        assert result.status == LoopStatus.IDLE
        assert loop.mode_applied == "normal"
        assert len(loop.recorded) == 1
        assert loop.recorded[0] == (0.9, "normal")

    @pytest.mark.asyncio
    async def test_degraded_health(self):
        loop = SimpleHealthLoop()
        loop.health_value = 0.5
        result = await loop.run_cycle()
        assert result.error is None
        assert loop.mode_applied == "conservative"

    @pytest.mark.asyncio
    async def test_emergency_health(self):
        loop = SimpleHealthLoop()
        loop.health_value = 0.2
        result = await loop.run_cycle()
        assert result.error is None
        assert loop.mode_applied == "emergency"

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        loop = SimpleHealthLoop()
        await loop.run_cycle()
        assert loop.metrics.total_cycles == 1
        assert loop.metrics.success_cycles == 1
        assert loop.metrics.failed_cycles == 0
        assert loop.metrics.last_total_ms >= 0

    @pytest.mark.asyncio
    async def test_snapshot(self):
        loop = SimpleHealthLoop()
        await loop.run_cycle()
        snap = loop.get_snapshot()
        assert snap["name"] == "test_health"
        assert snap["status"] == "idle"
        assert snap["success_rate"] == 1.0
        assert snap["total_cycles"] == 1


class TestLearningLoop:
    @pytest.mark.asyncio
    async def test_full_cycle(self):
        loop = SimpleLearningLoop()
        result = await loop.run_cycle()
        assert result.error is None
        assert loop.detected == "gap_found"
        assert loop.evaluated == "eval_gap_found"
        assert loop.remediated == "fix_eval_gap_found"
        assert loop.learned is not None

    @pytest.mark.asyncio
    async def test_metrics(self):
        loop = SimpleLearningLoop()
        await loop.run_cycle()
        assert loop.metrics.total_cycles == 1
        assert loop.metrics.success_cycles == 1


class TestFailureRecovery:
    @pytest.mark.asyncio
    async def test_consecutive_failures_trigger_degraded(self):
        loop = FailingLoop(max_failures_before_degraded=2)
        r1 = await loop.run_cycle()
        assert r1.status == LoopStatus.FAILED
        r2 = await loop.run_cycle()
        assert r2.status == LoopStatus.DEGRADED
        assert loop.metrics.degraded_cycles == 1

    @pytest.mark.asyncio
    async def test_force_recover(self):
        loop = FailingLoop(max_failures_before_degraded=1)
        await loop.run_cycle()
        assert loop.status == LoopStatus.DEGRADED
        loop.force_recover()
        assert loop.status == LoopStatus.IDLE

    @pytest.mark.asyncio
    async def test_cooldown_recovery(self):
        loop = FailingLoop(max_failures_before_degraded=1, cooldown_seconds=0.0)
        await loop.run_cycle()
        assert loop.status == LoopStatus.DEGRADED
        loop._consecutive_failures = 0
        r2 = await loop.run_cycle()
        assert loop.status in (LoopStatus.RECOVERING, LoopStatus.IDLE, LoopStatus.DEGRADED)


class TestCaching:
    @pytest.mark.asyncio
    async def test_perceive_cache(self):
        loop = SimpleHealthLoop(cache_ttl_seconds=10.0)
        await loop.run_cycle()
        assert loop._last_perception is not None
        cached = loop._get_cached_perception()
        assert cached == 0.9

    @pytest.mark.asyncio
    async def test_perceive_cache_expired(self):
        loop = SimpleHealthLoop(cache_ttl_seconds=0.001)
        await loop.run_cycle()
        time.sleep(0.01)
        cached = loop._get_cached_perception()
        assert cached is None