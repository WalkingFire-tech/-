"""
闭环工具混入 — 为同步/异步模块提供可组合的闭环能力

与cognitive_loop_base.py的关系：
- cognitive_loop_base.py 是async抽象基类（适合新模块继承）
- 本文件是同步+异步混入工具（适合现有模块组合使用，不改API）

提供能力：
- 冷却恢复（降级后需稳定期）
- 指标收集（LoopMetrics）
- 缓存（感知结果可缓存）
- 线程安全/协程安全
- 状态快照
"""
import time
import threading
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, Callable
from loguru import logger


class LoopStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"


@dataclass
class LoopMetrics:
    loop_name: str
    total_cycles: int = 0
    success_cycles: int = 0
    failed_cycles: int = 0
    degraded_cycles: int = 0
    last_cycle_ms: float = 0.0
    last_status: LoopStatus = LoopStatus.IDLE
    last_error: Optional[str] = None
    last_timestamp: float = 0.0


class LoopMixin:
    """
    闭环混入工具 — 为任何类添加闭环能力

    用法：
        class MyEngine(LoopMixin):
            def __init__(self):
                super().__init__(name="my_engine", cooldown_seconds=30.0)
                self._cache_ttl_seconds = 600.0

            def my_cycle(self):
                with self.loop_context() as ctx:
                    perception = self._perceive()
                    decision = self._decide(perception)
                    result = self._act(decision)
                    self._feedback(result)
                    return result

    混入提供：
    - loop_context() 上下文管理器：自动计时、状态管理、异常容忍
    - 冷却恢复：连续失败后降级，冷却期后恢复
    - 指标：LoopMetrics自动收集
    - 缓存：_get_cached()/_set_cached()
    - 快照：get_loop_snapshot()
    """

    def __init__(
        self,
        name: str,
        cooldown_seconds: float = 30.0,
        max_failures_before_degraded: int = 3,
    ):
        self._loop_name = name
        self._loop_cooldown_seconds = cooldown_seconds
        self._loop_max_failures = max_failures_before_degraded
        self._loop_failure_history: list = []
        self._loop_failure_history_max = 20

        self._loop_status = LoopStatus.IDLE
        self._loop_metrics = LoopMetrics(loop_name=name)
        self._loop_lock = threading.Lock()

        self._loop_consecutive_failures = 0
        self._loop_degraded_at: Optional[float] = None

        self._loop_cache: Dict[str, Any] = {}
        self._loop_cache_times: Dict[str, float] = {}
        self._cache_ttl_seconds: float = 0.0

    @property
    def loop_status(self) -> LoopStatus:
        return self._loop_status

    @property
    def loop_metrics(self) -> LoopMetrics:
        return self._loop_metrics

    def loop_context(self):
        """循环上下文管理器：自动计时、状态管理、异常容忍"""
        return _LoopContext(self)

    def force_recover(self):
        """强制恢复到IDLE状态"""
        with self._loop_lock:
            self._loop_status = LoopStatus.IDLE
            self._loop_consecutive_failures = 0
            self._loop_degraded_at = None
            logger.info(f"[{self._loop_name}] 强制恢复到IDLE")

    def get_loop_snapshot(self) -> Dict[str, Any]:
        """获取闭环状态快照"""
        return {
            "name": self._loop_name,
            "status": self._loop_status.value,
            "consecutive_failures": self._loop_consecutive_failures,
            "total_cycles": self._loop_metrics.total_cycles,
            "success_rate": (
                self._loop_metrics.success_cycles / self._loop_metrics.total_cycles
                if self._loop_metrics.total_cycles > 0
                else 0.0
            ),
            "last_cycle_ms": self._loop_metrics.last_cycle_ms,
            "last_error": self._loop_metrics.last_error,
            "degraded_remaining_s": (
                max(0, self._loop_cooldown_seconds - (time.time() - self._loop_degraded_at))
                if self._loop_degraded_at
                else 0.0
            ),
        }

    def _get_cached(self, key: str) -> Optional[Any]:
        if self._cache_ttl_seconds <= 0:
            return None
        if key in self._loop_cache and key in self._loop_cache_times:
            if time.time() - self._loop_cache_times[key] < self._cache_ttl_seconds:
                return self._loop_cache[key]
        return None

    def _set_cached(self, key: str, value: Any):
        if self._cache_ttl_seconds > 0:
            self._loop_cache[key] = value
            self._loop_cache_times[key] = time.time()

    def _finish_loop_cycle(self, cycle_start: float, error: Optional[str]):
        """完成一次循环，更新状态和指标"""
        total_ms = (time.time() - cycle_start) * 1000
        self._loop_metrics.last_cycle_ms = total_ms
        self._loop_metrics.last_timestamp = time.time()
        self._loop_metrics.total_cycles += 1

        if error:
            self._loop_consecutive_failures += 1
            self._loop_metrics.failed_cycles += 1
            self._loop_metrics.last_error = error

            if self._should_degrade():
                self._loop_status = LoopStatus.DEGRADED
                self._loop_degraded_at = time.time()
                self._loop_metrics.degraded_cycles += 1
                logger.warning(f"[{self._loop_name}] 连续{self._loop_consecutive_failures}次失败，进入降级模式")
            else:
                self._loop_status = LoopStatus.FAILED
        else:
            self._loop_consecutive_failures = 0
            self._loop_metrics.success_cycles += 1
            self._loop_metrics.last_error = None

            if self._loop_status == LoopStatus.DEGRADED:
                if self._loop_degraded_at and (time.time() - self._loop_degraded_at) >= self._loop_cooldown_seconds:
                    self._loop_status = LoopStatus.RECOVERING
                    self._loop_degraded_at = None
                    logger.info(f"[{self._loop_name}] 冷却期结束，尝试恢复")
            else:
                self._loop_status = LoopStatus.IDLE

        self._loop_metrics.last_status = self._loop_status

    def _should_degrade(self) -> bool:
        """
        概率化降级判断——替代固定阈值
        
        P(degrade) = sigmoid((consecutive - max) * k + failure_rate * w)
        - 连续失败次数超过max时概率急剧上升
        - 近期失败率(5分钟窗口)也影响判断
        - 引入随机性避免"差一次就降级"的边界问题
        """
        if self._loop_consecutive_failures >= self._loop_max_failures * 2:
            return True

        import random
        k = 2.0
        over = self._loop_consecutive_failures - self._loop_max_failures
        sig = 1.0 / (1.0 + pow(2.718, -over * k))

        recent_failures = 0
        if self._loop_failure_history:
            cutoff = time.time() - 300.0
            recent_failures = sum(1 for t in self._loop_failure_history if t > cutoff)
        failure_rate = recent_failures / max(1, self._loop_metrics.total_cycles) if self._loop_metrics.total_cycles > 0 else 0.0
        rate_factor = min(1.0, failure_rate * 3.0)

        prob = min(1.0, sig * 0.7 + rate_factor * 0.3)
        return random.random() < prob


class _LoopContext:
    """循环上下文管理器"""

    def __init__(self, mixin: LoopMixin):
        self._mixin = mixin
        self._start = 0.0

    def __enter__(self):
        with self._mixin._loop_lock:
            if self._mixin._loop_status == LoopStatus.RUNNING:
                logger.debug(f"[{self._mixin._loop_name}] 循环已在运行中，跳过")
                return self
            self._mixin._loop_status = LoopStatus.RUNNING
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        error = str(exc_val)[:200] if exc_val else None
        self._mixin._finish_loop_cycle(self._start, error)
        if exc_val:
            logger.warning(f"[{self._mixin._loop_name}] 循环异常: {exc_val}")
            return True
        return False


class AsyncLoopMixin:
    """
    异步闭环混入工具 — 为异步类添加闭环能力

    用法：
        class MyAsyncEngine(AsyncLoopMixin):
            def __init__(self):
                super().__init__(name="my_async_engine", cooldown_seconds=30.0)
                self._cache_ttl_seconds = 600.0

            async def my_cycle(self):
                async with self.async_loop_context():
                    perception = await self._perceive()
                    decision = await self._decide(perception)
                    result = await self._act(decision)
                    await self._feedback(result)
                    return result

    与LoopMixin的区别：
    - async_loop_context() 是异步上下文管理器（async with）
    - 使用asyncio.Lock替代threading.Lock（协程安全）
    - 其余能力（冷却恢复、指标、缓存、快照）完全一致
    """

    def __init__(
        self,
        name: str,
        cooldown_seconds: float = 30.0,
        max_failures_before_degraded: int = 3,
    ):
        self._loop_name = name
        self._loop_cooldown_seconds = cooldown_seconds
        self._loop_max_failures = max_failures_before_degraded

        self._loop_status = LoopStatus.IDLE
        self._loop_metrics = LoopMetrics(loop_name=name)
        self._async_loop_lock = asyncio.Lock()

        self._loop_consecutive_failures = 0
        self._loop_degraded_at: Optional[float] = None

        self._loop_cache: Dict[str, Any] = {}
        self._loop_cache_times: Dict[str, float] = {}
        self._cache_ttl_seconds: float = 0.0

    @property
    def loop_status(self) -> LoopStatus:
        return self._loop_status

    @property
    def loop_metrics(self) -> LoopMetrics:
        return self._loop_metrics

    def async_loop_context(self):
        """异步循环上下文管理器：自动计时、状态管理、异常容忍"""
        return _AsyncLoopContext(self)

    def force_recover(self):
        """强制恢复到IDLE状态"""
        self._loop_status = LoopStatus.IDLE
        self._loop_consecutive_failures = 0
        self._loop_degraded_at = None
        logger.info(f"[{self._loop_name}] 强制恢复到IDLE")

    def get_loop_snapshot(self) -> Dict[str, Any]:
        """获取闭环状态快照"""
        return {
            "name": self._loop_name,
            "status": self._loop_status.value,
            "consecutive_failures": self._loop_consecutive_failures,
            "total_cycles": self._loop_metrics.total_cycles,
            "success_rate": (
                self._loop_metrics.success_cycles / self._loop_metrics.total_cycles
                if self._loop_metrics.total_cycles > 0
                else 0.0
            ),
            "last_cycle_ms": self._loop_metrics.last_cycle_ms,
            "last_error": self._loop_metrics.last_error,
            "degraded_remaining_s": (
                max(0, self._loop_cooldown_seconds - (time.time() - self._loop_degraded_at))
                if self._loop_degraded_at
                else 0.0
            ),
        }

    def _get_cached(self, key: str) -> Optional[Any]:
        if self._cache_ttl_seconds <= 0:
            return None
        if key in self._loop_cache and key in self._loop_cache_times:
            if time.time() - self._loop_cache_times[key] < self._cache_ttl_seconds:
                return self._loop_cache[key]
        return None

    def _set_cached(self, key: str, value: Any):
        if self._cache_ttl_seconds > 0:
            self._loop_cache[key] = value
            self._loop_cache_times[key] = time.time()

    def _finish_loop_cycle(self, cycle_start: float, error: Optional[str]):
        """完成一次循环，更新状态和指标"""
        total_ms = (time.time() - cycle_start) * 1000
        self._loop_metrics.last_cycle_ms = total_ms
        self._loop_metrics.last_timestamp = time.time()
        self._loop_metrics.total_cycles += 1

        if error:
            self._loop_consecutive_failures += 1
            self._loop_metrics.failed_cycles += 1
            self._loop_metrics.last_error = error

            if self._should_degrade():
                self._loop_status = LoopStatus.DEGRADED
                self._loop_degraded_at = time.time()
                self._loop_metrics.degraded_cycles += 1
                logger.warning(f"[{self._loop_name}] 连续{self._loop_consecutive_failures}次失败，进入降级模式")
            else:
                self._loop_status = LoopStatus.FAILED
        else:
            self._loop_consecutive_failures = 0
            self._loop_metrics.success_cycles += 1
            self._loop_metrics.last_error = None

            if self._loop_status == LoopStatus.DEGRADED:
                if self._loop_degraded_at and (time.time() - self._loop_degraded_at) >= self._loop_cooldown_seconds:
                    self._loop_status = LoopStatus.RECOVERING
                    self._loop_degraded_at = None
                    logger.info(f"[{self._loop_name}] 冷却期结束，尝试恢复")
            else:
                self._loop_status = LoopStatus.IDLE

        self._loop_metrics.last_status = self._loop_status


class _AsyncLoopContext:
    """异步循环上下文管理器"""

    def __init__(self, mixin: AsyncLoopMixin):
        self._mixin = mixin
        self._start = 0.0

    async def __aenter__(self):
        if self._mixin._async_loop_lock.locked():
            logger.debug(f"[{self._mixin._loop_name}] 异步循环已在运行中，跳过")
            return self
        await self._mixin._async_loop_lock.acquire()
        self._mixin._loop_status = LoopStatus.RUNNING
        self._start = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        error = str(exc_val)[:200] if exc_val else None
        self._mixin._finish_loop_cycle(self._start, error)
        if self._mixin._async_loop_lock.locked():
            self._mixin._async_loop_lock.release()
        if exc_val:
            logger.warning(f"[{self._mixin._loop_name}] 异步循环异常: {exc_val}")
            return True
        return False