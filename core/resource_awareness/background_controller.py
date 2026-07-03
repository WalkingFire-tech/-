"""
后台任务控制器 - 管理所有后台循环的资源消耗

核心理念：后台任务不能"偷走"前台的资源
- 所有后台循环在执行前必须向控制器申请许可
- 紧急模式下暂停所有后台任务
- 保守模式下只允许低资源消耗任务运行

设计原则：
- 非侵入式：后台任务只需在循环入口加一行检查
- 可恢复：资源恢复后后台任务自动恢复
- 可观测：所有暂停/恢复事件都有日志
"""

import threading
from typing import Dict, Optional, Any, Set, List
from datetime import datetime
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.resource_awareness.health_monitor import get_health_monitor, OperatingMode
from core.resource_awareness.adaptive_governor import get_adaptive_governor


@dataclass
class BackgroundTaskInfo:
    name: str
    is_running: bool = False
    is_paused: bool = False
    last_run: Optional[str] = None
    skip_count: int = 0
    run_count: int = 0
    resource_impact: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "last_run": self.last_run,
            "skip_count": self.skip_count,
            "run_count": self.run_count,
            "resource_impact": self.resource_impact,
        }


class BackgroundTaskController:
    """
    后台任务控制器

    管理所有后台循环的资源消耗，确保后台任务不会
    在资源紧张时与前台请求争夺资源。
    """

    LOW_IMPACT_TASKS = {
        "heartbeat",
        "self_check",
        "memory_decay",
        "proactivity_check",
        "scheduled_heartbeat",
    }

    MEDIUM_IMPACT_TASKS = {
        "gap_growth",
        "sleep_consolidation",
        "slow_evolution",
        "self_assessment",
        "guardian_patrol",
    }

    HIGH_IMPACT_TASKS = {
        "external_learning",
        "knowledge_reorganization",
        "vector_index_rebuild",
        "model_warmup",
    }

    def __init__(self):
        self._tasks: Dict[str, BackgroundTaskInfo] = {}
        self._lock = threading.Lock()
        self._pause_events: Dict[str, threading.Event] = {}

        for name in self.LOW_IMPACT_TASKS:
            self._register_task(name, "low")
        for name in self.MEDIUM_IMPACT_TASKS:
            self._register_task(name, "medium")
        for name in self.HIGH_IMPACT_TASKS:
            self._register_task(name, "high")

        logger.info(f"🎛️ 后台任务控制器已创建（{len(self._tasks)}个已知任务）")

    def _register_task(self, name: str, impact: str = "medium"):
        """注册一个后台任务"""
        self._tasks[name] = BackgroundTaskInfo(
            name=name,
            resource_impact=impact,
        )
        self._pause_events[name] = threading.Event()
        self._pause_events[name].set()

    def should_run(self, task_name: str) -> bool:
        """判断后台任务是否应该运行"""
        governor = get_adaptive_governor()
        decision = governor.decide_background(task_name)

        with self._lock:
            if task_name not in self._tasks:
                self._register_task(task_name, "medium")
            task = self._tasks[task_name]

            if not decision.allowed:
                task.is_paused = True
                task.skip_count += 1
                pause_event = self._pause_events.get(task_name)
                if pause_event:
                    pause_event.clear()
                if task.skip_count % 5 == 1:
                    logger.info(f"🎛️ 后台任务「{task_name}」已暂停（{decision.message}），累计跳过{task.skip_count}次")
                return False

            task.is_paused = False
            pause_event = self._pause_events.get(task_name)
            if pause_event:
                pause_event.set()
            return True

    def notify_start(self, task_name: str):
        """通知后台任务开始执行"""
        with self._lock:
            if task_name not in self._tasks:
                self._register_task(task_name, "medium")
            self._tasks[task_name].is_running = True
            self._tasks[task_name].run_count += 1
            self._tasks[task_name].last_run = datetime.now().isoformat()

    def notify_end(self, task_name: str):
        """通知后台任务执行结束"""
        with self._lock:
            if task_name in self._tasks:
                self._tasks[task_name].is_running = False

    def wait_if_paused(self, task_name: str, timeout: float = 30.0) -> bool:
        """
        如果任务被暂停，阻塞等待直到恢复或超时

        用于后台循环中，替代time.sleep()，使任务可被动态恢复。
        返回True表示可以继续，False表示超时或应退出。
        """
        event = self._pause_events.get(task_name)
        if event is None:
            return True
        return event.wait(timeout=timeout)

    def pause_all(self):
        """暂停所有后台任务（紧急模式）"""
        with self._lock:
            for name, task in self._tasks.items():
                task.is_paused = True
                event = self._pause_events.get(name)
                if event:
                    event.clear()
        logger.warning("🛑 紧急模式：所有后台任务已暂停")

    def resume_all(self):
        """恢复所有后台任务"""
        with self._lock:
            for name, task in self._tasks.items():
                task.is_paused = False
                event = self._pause_events.get(name)
                if event:
                    event.set()
        logger.info("✅ 所有后台任务已恢复")

    def get_status(self) -> Dict[str, Any]:
        """获取所有后台任务状态"""
        monitor = get_health_monitor()
        with self._lock:
            tasks = {name: info.to_dict() for name, info in self._tasks.items()}
        return {
            "mode": monitor.get_mode_value(),
            "tasks": tasks,
            "paused_count": sum(1 for t in self._tasks.values() if t.is_paused),
            "running_count": sum(1 for t in self._tasks.values() if t.is_running),
        }


_task_controller: Optional[BackgroundTaskController] = None
_tc_lock = threading.Lock()


def get_background_controller() -> BackgroundTaskController:
    """获取后台任务控制器单例"""
    global _task_controller
    with _tc_lock:
        if _task_controller is None:
            _task_controller = BackgroundTaskController()
        return _task_controller