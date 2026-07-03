"""
定时任务调度器 (P1-2)

实现系统定时自检、定时学习、定时报告
通过 event_bus 发布 ScheduledTask 事件，各模块订阅后自行处理

默认调度：
- 5分钟：系统自检（健康检查+模块状态）
- 30分钟：定时学习（知识整合+经验归纳）
- 24小时：每日报告（系统状态摘要+进化建议）
"""

import asyncio
import time
import threading
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ScheduledJob:
    name: str
    interval_seconds: float
    callback: Optional[Callable] = None
    last_run: float = 0.0
    run_count: int = 0
    enabled: bool = True


class ScheduledTaskManager:
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._setup_default_jobs()

    def _setup_default_jobs(self):
        self.register_job("self_check", 300.0, self._job_self_check)
        self.register_job("periodic_learning", 1800.0, self._job_periodic_learning)
        self.register_job("daily_report", 86400.0, self._job_daily_report)
        self.register_job("memory_decay", 3600.0, self._job_memory_decay)
        self.register_job("layered_memory_sync", 3600.0, self._job_layered_memory_sync)
        self.register_job("slow_evolution", 3600.0, self._job_slow_evolution)
        self.register_job("proactivity_check", 600.0, self._job_proactivity_check)

    def register_job(self, name: str, interval_seconds: float, callback: Optional[Callable] = None):
        with self._lock:
            self._jobs[name] = ScheduledJob(
                name=name,
                interval_seconds=interval_seconds,
                callback=callback,
            )
        logger.debug(f"定时任务已注册: {name} (间隔{interval_seconds}s)")

    def unregister_job(self, name: str):
        with self._lock:
            self._jobs.pop(name, None)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"⏰ 定时任务调度器已启动 ({len(self._jobs)}个任务)")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("⏰ 定时任务调度器已停止")

    def _run_loop(self):
        while self._running:
            try:
                now = time.time()
                with self._lock:
                    jobs_to_run = []
                    for job in self._jobs.values():
                        if job.enabled and (now - job.last_run) >= job.interval_seconds:
                            jobs_to_run.append(job)

                for job in jobs_to_run:
                    try:
                        self._execute_job(job)
                    except Exception as e:
                        logger.error(f"定时任务执行失败 {job.name}: {e}")

                time.sleep(30.0)
            except Exception as e:
                logger.error(f"定时任务调度循环异常: {e}")
                time.sleep(60.0)

    def _execute_job(self, job: ScheduledJob):
        job.last_run = time.time()
        job.run_count += 1

        try:
            from infrastructure.event_bus import bus, EventTypes
            bus.publish(EventTypes.ScheduledTask, {
                "job_name": job.name,
                "run_count": job.run_count,
                "interval_seconds": job.interval_seconds,
                "timestamp": time.time(),
            })
        except Exception:
            pass

        if job.callback:
            try:
                job.callback()
            except Exception as e:
                logger.error(f"定时任务回调失败 {job.name}: {e}")

        logger.info(f"⏰ 定时任务执行: {job.name} (第{job.run_count}次, 间隔{job.interval_seconds}s)")

    def _job_self_check(self):
        try:
            from core.module_health import module_health
            report = module_health.get_health_report()
            unhealthy = []
            for status_key, modules in report.items():
                if status_key not in ("healthy",) and modules:
                    unhealthy.extend([m.get("name", "?") for m in modules if isinstance(m, dict)])
            if unhealthy:
                logger.warning(f"⏰ 自检发现{len(unhealthy)}个不健康模块: {unhealthy}")
            else:
                logger.debug("⏰ 系统自检: 所有模块健康 ✅")
        except Exception as e:
            logger.debug(f"自检跳过: {e}")

    def _job_periodic_learning(self):
        try:
            from infrastructure.event_bus import bus, EventTypes
            bus.publish(EventTypes.IdlePeriod, {
                "state": "scheduled_learning",
                "silence_duration": 0,
                "pending_signals": 0,
                "source": "scheduled_task",
            })
            logger.info("⏰ 定时学习: 已发布IdlePeriod事件触发知识整合")
        except Exception as e:
            logger.debug(f"定时学习跳过: {e}")

    def _job_daily_report(self):
        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            status = el.get_status()
            logger.info(
                f"⏰ 每日报告: 状态={status.get('state', '?')}, "
                f"运行={status.get('uptime_seconds', 0):.0f}s, "
                f"心跳={status.get('total_cycles', 0)}, "
                f"整合记忆={status.get('memories_consolidated', 0)}"
            )
        except Exception as e:
            logger.debug(f"每日报告跳过: {e}")

    def _job_memory_decay(self):
        try:
            from core.knowledge_forgetting import knowledge_forgetting
            result = knowledge_forgetting.execute_fading(dry_run=False)
            rules = result.get("rules", {})
            experiences = result.get("experiences", {})
            logger.info(
                f"⏰ 记忆衰减: 规则淡化{rules.get('faded',0)}+清除{rules.get('pruned',0)}+激活{rules.get('reactivated',0)}, "
                f"经验淡化{experiences.get('faded',0)}+清除{experiences.get('pruned',0)}"
            )
        except Exception as e:
            logger.debug(f"记忆衰减跳过: {e}")

    def _job_layered_memory_sync(self):
        try:
            from core.memory.layered_memory import layered_memory
            s = layered_memory.sync_strategic_memory()
            p = layered_memory.sync_procedural_memory()
            t = layered_memory.sync_tool_memory()
            d = layered_memory.decay_outdated()
            stats = layered_memory.get_stats()
            logger.info(
                f"⏰ 分层记忆同步: 战略+{s}/程序+{p}/工具+{t}, "
                f"衰减: 战略-{d.get('strategic_decayed',0)}/程序-{d.get('procedural_decayed',0)}/工具-{d.get('tool_decayed',0)}, "
                f"总计{stats['total']}条"
            )
        except Exception as e:
            logger.debug(f"分层记忆同步跳过: {e}")

    def _job_slow_evolution(self):
        try:
            from infrastructure.dual_speed_evolution import dual_speed_evolution
            result = dual_speed_evolution.run_slow_loop()
            logger.info(
                f"⏰ 慢循环进化: 第{result['slow_loop_count']}次, "
                f"痛点={result['pain_signals_processed']}, "
                f"基因={result['steps'].get('gene_evolution', {}).get('status', '?')}, "
                f"棘轮={result['steps'].get('ratchet_validation', {}).get('status', '?')}"
            )
        except Exception as e:
            logger.debug(f"慢循环进化跳过: {e}")

    def _job_proactivity_check(self):
        try:
            from core.presence.proactivity import get_proactivity_engine, ProactivityContext
            from core.relationship.model import get_relationship_model
            from core.presence.existence_layer import get_existence_layer
            from datetime import datetime

            engine = get_proactivity_engine()
            rm = get_relationship_model()
            el = get_existence_layer()

            silence = el.metrics.silence_duration if el.metrics else 0
            rel = rm.get_relationship_summary()

            ctx = ProactivityContext(
                user_silence_duration=silence,
                relationship_trust=rel.get("trust_level", 0.5),
                recent_interactions=rel.get("total_interactions", 0),
                last_proactivity_time=engine.last_proactivity or datetime.now(),
                user_engagement_level=0.5,
            )

            decision = engine.evaluate(ctx)
            if decision.should_act and decision.content:
                logger.info(f"🌟 主动性触发: type={decision.action_type.value if decision.action_type else '?'} "
                            f"content={decision.content[:60]} reason={decision.reason}")
                try:
                    from infrastructure.event_bus import bus, EventTypes
                    bus.publish(EventTypes.ProactivityTriggered if hasattr(EventTypes, 'ProactivityTriggered') else 'proactivity.triggered', {
                        "action_type": decision.action_type.value if decision.action_type else "unknown",
                        "content": decision.content,
                        "reason": decision.reason,
                        "confidence": decision.confidence,
                    })
                except Exception:
                    pass
            else:
                logger.debug(f"主动性检查: 暂无行动 (silence={silence:.0f}s)")
        except Exception as e:
            logger.debug(f"主动性检查跳过: {e}")

    def get_status(self) -> Dict:
        with self._lock:
            jobs = {}
            for name, job in self._jobs.items():
                jobs[name] = {
                    "interval_seconds": job.interval_seconds,
                    "last_run": job.last_run,
                    "run_count": job.run_count,
                    "enabled": job.enabled,
                    "next_run_in": max(0, job.interval_seconds - (time.time() - job.last_run)) if job.last_run > 0 else job.interval_seconds,
                }
            return {
                "running": self._running,
                "jobs": jobs,
            }


scheduled_task_manager = ScheduledTaskManager()