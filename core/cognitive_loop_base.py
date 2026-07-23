"""
认知闭环抽象基类 — 将"感知-决策-行动-反馈"抽象为可复用框架

与core/cognitive_loop.py的关系：
- cognitive_loop.py 是具体实现（7大机制+6层架构）
- 本文件是抽象基类，供15个现有模块继承，消除重复的闭环模式

两种子模式：
- HealthLoop：健康检查→降级→恢复（AdaptiveGovernor, HealthMonitor等）
- LearningLoop：检测→评估→行动→学习（CuriosityEngine, SelfVerifier等）
"""
import time
import threading
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional, Dict
from loguru import logger


class LoopPhase(str, Enum):
    PERCEIVE = "perceive"
    DECIDE = "decide"
    ACT = "act"
    FEEDBACK = "feedback"


class LoopStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"


@dataclass
class LoopResult:
    phase: LoopPhase
    status: LoopStatus
    data: Any = None
    duration_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class LoopMetrics:
    loop_name: str
    total_cycles: int = 0
    success_cycles: int = 0
    failed_cycles: int = 0
    degraded_cycles: int = 0
    last_perceive_ms: float = 0.0
    last_decide_ms: float = 0.0
    last_act_ms: float = 0.0
    last_feedback_ms: float = 0.0
    last_total_ms: float = 0.0
    last_status: LoopStatus = LoopStatus.IDLE
    last_error: Optional[str] = None
    last_timestamp: float = 0.0


class CognitiveLoopBase(ABC):
    """
    认知闭环抽象基类

    子类只需实现4个抽象方法：
    - _perceive() → 感知当前状态
    - _decide(perception) → 基于感知做决策
    - _act(decision) → 执行决策
    - _feedback(perception, decision, action_result) → 反馈学习

    基类自动提供：
    - 完整循环编排（run_cycle）
    - 异常容忍（单阶段失败不阻塞）
    - 冷却恢复（降级后需稳定期）
    - 缓存（感知结果可缓存）
    - 指标收集（LoopMetrics）
    - 线程安全
    """

    def __init__(
        self,
        name: str,
        cooldown_seconds: float = 30.0,
        cache_ttl_seconds: float = 0.0,
        max_failures_before_degraded: int = 3,
    ):
        self._name = name
        self._cooldown_seconds = cooldown_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_failures_before_degraded = max_failures_before_degraded

        self._status = LoopStatus.IDLE
        self._metrics = LoopMetrics(loop_name=name)
        self._lock = threading.Lock()

        self._consecutive_failures = 0
        self._degraded_at: Optional[float] = None
        self._last_perception: Any = None
        self._last_perception_time: float = 0.0

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> LoopStatus:
        return self._status

    @property
    def metrics(self) -> LoopMetrics:
        return self._metrics

    @abstractmethod
    async def _perceive(self) -> Any:
        ...

    @abstractmethod
    async def _decide(self, perception: Any) -> Any:
        ...

    @abstractmethod
    async def _act(self, decision: Any) -> Any:
        ...

    @abstractmethod
    async def _feedback(self, perception: Any, decision: Any, action_result: Any) -> Any:
        ...

    async def run_cycle(self) -> LoopResult:
        with self._lock:
            if self._status == LoopStatus.RUNNING:
                return LoopResult(phase=LoopPhase.PERCEIVE, status=self._status, error="already_running")
            self._status = LoopStatus.RUNNING

        cycle_start = time.time()

        try:
            perception = await self._run_phase(LoopPhase.PERCEIVE, self._perceive)
            if perception is None:
                return self._finish_cycle(LoopPhase.PERCEIVE, cycle_start, "perception_returned_none")

            decision = await self._run_phase(LoopPhase.DECIDE, self._decide, perception)
            if decision is None:
                return self._finish_cycle(LoopPhase.DECIDE, cycle_start, "decision_returned_none")

            action_result = await self._run_phase(LoopPhase.ACT, self._act, decision)

            await self._run_phase(LoopPhase.FEEDBACK, self._feedback, perception, decision, action_result)

            return self._finish_cycle(LoopPhase.FEEDBACK, cycle_start, None)

        except Exception as e:
            last_error = str(e)[:200]
            logger.warning(f"[{self._name}] 循环异常: {e}")
            return self._finish_cycle(LoopPhase.FEEDBACK, cycle_start, last_error)

    async def _run_phase(self, phase: LoopPhase, fn, *args) -> Any:
        start = time.time()
        try:
            if phase == LoopPhase.PERCEIVE and self._cache_ttl_seconds > 0:
                cached = self._get_cached_perception()
                if cached is not None:
                    return cached

            result = await fn(*args) if args else await fn()

            if phase == LoopPhase.PERCEIVE and self._cache_ttl_seconds > 0:
                self._cache_perception(result)

            elapsed_ms = (time.time() - start) * 1000
            self._update_phase_metric(phase, elapsed_ms)
            return result

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            self._update_phase_metric(phase, elapsed_ms)
            logger.warning(f"[{self._name}] {phase.value}阶段异常: {e}")
            raise

    def _get_cached_perception(self) -> Any:
        if self._last_perception is not None and self._last_perception_time > 0:
            if time.time() - self._last_perception_time < self._cache_ttl_seconds:
                return self._last_perception
        return None

    def _cache_perception(self, perception: Any):
        self._last_perception = perception
        self._last_perception_time = time.time()

    def _update_phase_metric(self, phase: LoopPhase, elapsed_ms: float):
        if phase == LoopPhase.PERCEIVE:
            self._metrics.last_perceive_ms = elapsed_ms
        elif phase == LoopPhase.DECIDE:
            self._metrics.last_decide_ms = elapsed_ms
        elif phase == LoopPhase.ACT:
            self._metrics.last_act_ms = elapsed_ms
        elif phase == LoopPhase.FEEDBACK:
            self._metrics.last_feedback_ms = elapsed_ms

    def _finish_cycle(self, last_phase: LoopPhase, cycle_start: float, error: Optional[str]) -> LoopResult:
        total_ms = (time.time() - cycle_start) * 1000
        self._metrics.last_total_ms = total_ms
        self._metrics.last_timestamp = time.time()
        self._metrics.total_cycles += 1

        if error:
            self._consecutive_failures += 1
            self._metrics.failed_cycles += 1
            self._metrics.last_error = error

            if self._consecutive_failures >= self._max_failures_before_degraded:
                self._status = LoopStatus.DEGRADED
                self._degraded_at = time.time()
                self._metrics.degraded_cycles += 1
                logger.warning(f"[{self._name}] 连续{self._consecutive_failures}次失败，进入降级模式")
            else:
                self._status = LoopStatus.FAILED
        else:
            self._consecutive_failures = 0
            self._metrics.success_cycles += 1
            self._metrics.last_error = None

            if self._status == LoopStatus.DEGRADED:
                if self._degraded_at and (time.time() - self._degraded_at) >= self._cooldown_seconds:
                    self._status = LoopStatus.RECOVERING
                    self._degraded_at = None
                    logger.info(f"[{self._name}] 冷却期结束，尝试恢复")
            else:
                self._status = LoopStatus.IDLE

        self._metrics.last_status = self._status
        return LoopResult(
            phase=last_phase,
            status=self._status,
            duration_ms=total_ms,
            error=error,
        )

    def force_recover(self):
        with self._lock:
            self._status = LoopStatus.IDLE
            self._consecutive_failures = 0
            self._degraded_at = None
            logger.info(f"[{self._name}] 强制恢复到IDLE")

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "status": self._status.value,
            "consecutive_failures": self._consecutive_failures,
            "total_cycles": self._metrics.total_cycles,
            "success_rate": (
                self._metrics.success_cycles / self._metrics.total_cycles
                if self._metrics.total_cycles > 0
                else 0.0
            ),
            "last_total_ms": self._metrics.last_total_ms,
            "last_error": self._metrics.last_error,
            "degraded_remaining_s": (
                max(0, self._cooldown_seconds - (time.time() - self._degraded_at))
                if self._degraded_at
                else 0.0
            ),
        }


class HealthLoop(CognitiveLoopBase):
    """
    健康检查闭环 — "感知→降级→恢复"模式

    子类需实现：
    - _check_health() → 返回健康度（0.0-1.0）
    - _compute_mode(health) → 基于健康度计算运行模式
    - _apply_mode(mode) → 应用运行模式
    - _record_health(health, mode) → 记录健康历史
    """

    @abstractmethod
    async def _check_health(self) -> float:
        ...

    @abstractmethod
    async def _compute_mode(self, health: float) -> Any:
        ...

    @abstractmethod
    async def _apply_mode(self, mode: Any) -> Any:
        ...

    @abstractmethod
    async def _record_health(self, health: float, mode: Any) -> Any:
        ...

    async def _perceive(self) -> Any:
        return await self._check_health()

    async def _decide(self, perception: Any) -> Any:
        return await self._compute_mode(perception)

    async def _act(self, decision: Any) -> Any:
        return await self._apply_mode(decision)

    async def _feedback(self, perception: Any, decision: Any, action_result: Any) -> Any:
        return await self._record_health(perception, decision)


class LearningLoop(CognitiveLoopBase):
    """
    学习闭环 — "检测→评估→行动→学习"模式

    子类需实现：
    - _detect() → 检测问题/缺口/缺陷
    - _evaluate(detection) → 评估严重度/优先级
    - _remediate(evaluation) → 执行修正/学习/修复
    - _learn(detection, evaluation, remediation) → 沉淀经验
    """

    @abstractmethod
    async def _detect(self) -> Any:
        ...

    @abstractmethod
    async def _evaluate(self, detection: Any) -> Any:
        ...

    @abstractmethod
    async def _remediate(self, evaluation: Any) -> Any:
        ...

    @abstractmethod
    async def _learn(self, detection: Any, evaluation: Any, remediation: Any) -> Any:
        ...

    async def _perceive(self) -> Any:
        return await self._detect()

    async def _decide(self, perception: Any) -> Any:
        return await self._evaluate(perception)

    async def _act(self, decision: Any) -> Any:
        return await self._remediate(decision)

    async def _feedback(self, perception: Any, decision: Any, action_result: Any) -> Any:
        return await self._learn(perception, decision, action_result)