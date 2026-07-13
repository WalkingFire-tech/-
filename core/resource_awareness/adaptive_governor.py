"""
自适应调节器 - 根据资源状态调节系统行为

核心理验：主动降级优于被动崩溃
- 当资源紧张时，系统主动切换到低功耗模式
- 根据资源紧张程度，采取不同级别的调节措施
- 所有资源消耗型操作都经过调节器审批

设计原则：
- 渐进式限制：正常→保守→紧急，逐级收紧
- 可恢复：资源恢复后自动解除限制（带冷却缓冲期）
- 透明：每次调节都有明确原因和日志
- 硬约束：decide()返回allowed=False时，调用方必须遵守

闭环1：资源自我保存
- 冷却缓冲期：EMERGENCY/CONSERVATIVE→NORMAL需要30秒稳定期
- 模式变更回调：模式切换时通知所有订阅者
- 硬约束执行：parallel_router等模块必须遵守decide()的决策
"""

import threading
from typing import Dict, Optional, Any, List, Callable
from datetime import datetime, timedelta
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.resource_awareness.health_monitor import (
    SystemHealthMonitor, OperatingMode, get_health_monitor
)


class ActionType(Enum):
    OLLAMA_INFERENCE = "ollama_inference"
    EXTERNAL_SEARCH = "external_search"
    DENSE_RETRIEVAL = "dense_retrieval"
    BACKGROUND_TASK = "background_task"
    PARALLEL_PATH_EXPANSION = "parallel_path_expansion"
    MEMORY_INTENSIVE = "memory_intensive"
    CACHE_WRITE = "cache_write"


class ActionDecision:
    __slots__ = ('allowed', 'mode', 'message', 'suggestions', 'degraded_to')

    def __init__(self, allowed: bool, mode: str, message: str = "",
                 suggestions: List[str] = None, degraded_to: str = None):
        self.allowed = allowed
        self.mode = mode
        self.message = message
        self.suggestions = suggestions or []
        self.degraded_to = degraded_to

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "message": self.message,
            "suggestions": self.suggestions,
            "degraded_to": self.degraded_to,
        }


class AdaptiveGovernor:
    """
    自适应调节器

    所有资源消耗型操作都经过调节器审批。
    根据当前运行模式决定是否允许、降级或拒绝操作。
    
    闭环1增强：
    - 冷却缓冲期：从降级模式恢复到NORMAL需要30秒稳定期
    - 模式变更回调：模式切换时通知订阅者
    - 硬约束：decide()返回allowed=False时调用方必须遵守
    """

    COOLDOWN_SECONDS = 30
    _MODE_SEVERITY = {OperatingMode.NORMAL: 0, OperatingMode.CONSERVATIVE: 1, OperatingMode.EMERGENCY: 2}

    def __init__(self, health_monitor: SystemHealthMonitor = None):
        self.health_monitor = health_monitor or get_health_monitor()
        self._decision_log: List[Dict] = []
        self._max_log = 200
        self._lock = threading.Lock()

        self._emergency_blocked = {
            ActionType.OLLAMA_INFERENCE,
            ActionType.EXTERNAL_SEARCH,
            ActionType.DENSE_RETRIEVAL,
            ActionType.BACKGROUND_TASK,
            ActionType.PARALLEL_PATH_EXPANSION,
            ActionType.MEMORY_INTENSIVE,
        }

        self._conservative_blocked = {
            ActionType.EXTERNAL_SEARCH,
            ActionType.PARALLEL_PATH_EXPANSION,
        }

        self._conservative_degraded = {
            ActionType.OLLAMA_INFERENCE: "cached_response",
            ActionType.DENSE_RETRIEVAL: "tfidf_fallback",
        }

        self._last_mode: OperatingMode = OperatingMode.NORMAL
        self._effective_mode: OperatingMode = OperatingMode.NORMAL
        self._cooldown_until: Optional[datetime] = None
        self._mode_change_callbacks: List[Callable[[OperatingMode, OperatingMode], None]] = []

        logger.info("⚖️ 自适应调节器已创建（含冷却缓冲+模式变更回调）")

    def on_mode_change(self, callback: Callable[[OperatingMode, OperatingMode], None]):
        self._mode_change_callbacks.append(callback)

    def get_effective_mode(self) -> OperatingMode:
        now = datetime.now()
        raw_mode = self.health_monitor.get_operating_mode()

        if raw_mode != self._last_mode:
            old_mode = self._last_mode
            self._last_mode = raw_mode

            old_sev = self._MODE_SEVERITY.get(old_mode, 0)
            new_sev = self._MODE_SEVERITY.get(raw_mode, 0)

            if new_sev < old_sev:
                self._cooldown_until = now + timedelta(seconds=self.COOLDOWN_SECONDS)
                logger.info(f"⚖️ 资源恢复中：{old_mode.value}→{raw_mode.value}，冷却缓冲{self.COOLDOWN_SECONDS}秒")
            elif new_sev > old_sev:
                self._effective_mode = raw_mode
                self._cooldown_until = None
                logger.warning(f"⚖️ 资源降级：{old_mode.value}→{raw_mode.value}")

            for cb in self._mode_change_callbacks:
                try:
                    cb(old_mode, raw_mode)
                except Exception as e:
                    logger.warning(f"模式变更回调异常: {e}")

        if self._cooldown_until and now < self._cooldown_until:
            return self._effective_mode

        self._effective_mode = raw_mode
        self._cooldown_until = None
        return self._effective_mode

    def decide(self, action: ActionType, context: Dict = None) -> ActionDecision:
        mode = self.get_effective_mode()
        context = context or {}

        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            if action == ActionType.OLLAMA_INFERENCE:
                throttle = get_gpu_throttle()
                if throttle["level"] == "critical":
                    self._log_decision(action, True, mode.value, f"gpu_throttle_critical:delay={throttle['delay_seconds']}s")
                    return ActionDecision(
                        allowed=True, mode=mode.value,
                        message=f"GPU过热({throttle['temperature']}°C)，建议延迟{throttle['delay_seconds']}秒后短推理",
                        suggestions=["优先使用外部API", f"推理token限制{throttle['max_tokens']}"],
                        degraded_to="external_api_first",
                    )
                if throttle["level"] in ("hot", "warm"):
                    self._log_decision(action, True, mode.value, f"gpu_throttle_{throttle['level']}:delay={throttle['delay_seconds']}s")
                    return ActionDecision(
                        allowed=True, mode=mode.value,
                        message=f"GPU偏热({throttle['temperature']}°C)，建议延迟{throttle['delay_seconds']}秒",
                        suggestions=[f"推理token限制{throttle['max_tokens']}"],
                        degraded_to="throttled_inference",
                    )
        except Exception:
            logger.warning("操作降级跳过")

        if mode == OperatingMode.EMERGENCY:
            if action in self._emergency_blocked:
                self._log_decision(action, False, mode.value, "emergency_block")
                return ActionDecision(
                    allowed=False,
                    mode=mode.value,
                    message="系统资源极度紧张，已进入紧急保护模式",
                    suggestions=["等待资源恢复后重试", "减少并发查询"],
                )

        if mode == OperatingMode.CONSERVATIVE:
            if action in self._conservative_blocked:
                self._log_decision(action, False, mode.value, "conservative_block")
                return ActionDecision(
                    allowed=False,
                    mode=mode.value,
                    message="系统资源紧张，已自动限制非关键操作",
                    suggestions=["使用缓存结果", "降低并行度"],
                )

            if action in self._conservative_degraded:
                degraded = self._conservative_degraded[action]
                self._log_decision(action, True, mode.value, f"degraded_to_{degraded}")
                return ActionDecision(
                    allowed=True,
                    mode=mode.value,
                    message=f"资源紧张，已降级为{degraded}",
                    degraded_to=degraded,
                )

        self._log_decision(action, True, mode.value, "normal_allow")
        return ActionDecision(allowed=True, mode=mode.value)

    def decide_ollama(self) -> ActionDecision:
        return self.decide(ActionType.OLLAMA_INFERENCE)

    def decide_search(self) -> ActionDecision:
        return self.decide(ActionType.EXTERNAL_SEARCH)

    def decide_background(self, task_name: str) -> ActionDecision:
        mode = self.get_effective_mode()

        if mode == OperatingMode.EMERGENCY:
            self._log_decision(ActionType.BACKGROUND_TASK, False, mode.value, f"emergency_block:{task_name}")
            return ActionDecision(
                allowed=False,
                mode=mode.value,
                message=f"紧急模式：后台任务「{task_name}」已暂停",
            )

        if mode == OperatingMode.CONSERVATIVE:
            low_impact = {"heartbeat", "self_check", "memory_decay", "proactivity_check"}
            if task_name not in low_impact:
                self._log_decision(ActionType.BACKGROUND_TASK, False, mode.value, f"conservative_block:{task_name}")
                return ActionDecision(
                    allowed=False,
                    mode=mode.value,
                    message=f"保守模式：后台任务「{task_name}」已暂停",
                )

        return ActionDecision(allowed=True, mode=mode.value)

    def get_parallel_path_count(self, requested: int = 9) -> int:
        max_paths = self.health_monitor.get_max_parallel_paths()
        effective = self.get_effective_mode()
        effective_sev = self._MODE_SEVERITY.get(effective, 0)
        if effective_sev >= 2:
            max_paths = min(max_paths, 3)
        elif effective_sev >= 1:
            max_paths = min(max_paths, 5)
        actual = min(requested, max_paths)
        if actual < requested:
            logger.info(f"⚖️ 路径削减：{requested}→{actual}（{effective.value}模式）")
        return actual

    def get_retrieval_strategy(self) -> str:
        if self.health_monitor.should_use_dense_retrieval():
            return "hybrid"
        return "sparse_only"

    def _log_decision(self, action: ActionType, allowed: bool, mode: str, reason: str):
        entry = {
            "action": action.value,
            "allowed": allowed,
            "mode": mode,
            "reason": reason,
            "ts": datetime.now().isoformat(),
        }
        with self._lock:
            self._decision_log.append(entry)
            if len(self._decision_log) > self._max_log:
                self._decision_log = self._decision_log[-self._max_log:]

    def get_decision_log(self, limit: int = 20) -> List[Dict]:
        with self._lock:
            return self._decision_log[-limit:]

    def get_status(self) -> Dict[str, Any]:
        effective = self.get_effective_mode()
        return {
            "health": self.health_monitor.get_status(),
            "effective_mode": effective.value,
            "cooldown_remaining": (self._cooldown_until - datetime.now()).total_seconds() if self._cooldown_until and datetime.now() < self._cooldown_until else 0,
            "recent_decisions": self.get_decision_log(10),
            "parallel_paths": self.get_parallel_path_count(),
            "retrieval_strategy": self.get_retrieval_strategy(),
        }


_governor: Optional[AdaptiveGovernor] = None
_governor_lock = threading.Lock()


def get_adaptive_governor() -> AdaptiveGovernor:
    global _governor
    with _governor_lock:
        if _governor is None:
            _governor = AdaptiveGovernor()
        return _governor