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
from infrastructure.database_manager import DatabaseManager


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
        self.register_job("introspection", 300.0, self._job_introspection)
        self.register_job("deferred_deep_process", 600.0, self._job_deferred_deep_process)
        self.register_job("sleep_consolidation", 3600.0, self._job_sleep_consolidation)

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
            from core.perception_snapshot import get_snapshot
            from datetime import datetime

            snap = get_snapshot()
            engine = get_proactivity_engine()

            existence = snap.existence
            interaction = snap.interaction

            silence = existence.get("silence_duration", 0)
            trust = interaction.get("trust_level", 0.5)
            total_int = interaction.get("total_interactions", 0)
            engagement = interaction.get("engagement", 0.5)

            ctx = ProactivityContext(
                user_silence_duration=silence,
                relationship_trust=trust,
                recent_interactions=total_int,
                last_proactivity_time=engine.last_proactivity or datetime.now(),
                user_engagement_level=engagement,
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
                try:
                    from backend.main_fast import _enqueue_proactivity
                    _enqueue_proactivity({
                        "type": "proactivity",
                        "action_type": decision.action_type.value if decision.action_type else "unknown",
                        "content": decision.content,
                        "reason": decision.reason,
                        "confidence": decision.confidence,
                    })
                except Exception:
                    pass
                try:
                    db = DatabaseManager.get("data/experience_pool.db")
                    db.execute(
                        "INSERT INTO experiences (raw_input, response, quality_score, intent_type, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
                        (f"[主动性:{decision.action_type.value if decision.action_type else 'unknown'}] {decision.reason}",
                         decision.content, int(decision.confidence * 50), "proactivity"),
                        commit=True
                    )
                except Exception:
                    pass
                try:
                    from core.knowledge_graph import get_knowledge_graph, NodeType as _NT
                    _kg = get_knowledge_graph()
                    _node = _kg.add_node(
                        f"主动性:{decision.action_type.value if decision.action_type else 'unknown'} - {decision.reason}",
                        node_type=_NT.EXPERIENCE, importance=decision.confidence * 0.6
                    )
                except Exception:
                    pass
            else:
                logger.debug(f"主动性检查: 暂无行动 (silence={silence:.0f}s)")
        except Exception as e:
            logger.debug(f"主动性检查跳过: {e}")

    def _job_introspection(self):
        try:
            from core.introspector import get_introspector
            introspector = get_introspector()
            report = introspector.run_check()
            if report.critical_count > 0 or report.major_count > 0:
                try:
                    from infrastructure.event_bus import bus, EventTypes
                    bus.publish(EventTypes.SystemAnomaly if hasattr(EventTypes, 'SystemAnomaly') else 'system.anomaly', {
                        "health": report.overall_health,
                        "critical": report.critical_count,
                        "major": report.major_count,
                        "anomalies": report.anomalies[:5],
                        "recommendations": report.recommendations[:3],
                    })
                except Exception:
                    pass
                try:
                    from backend.main_fast import _enqueue_proactivity
                    _enqueue_proactivity({
                        "type": "system_anomaly",
                        "health": report.overall_health,
                        "critical": report.critical_count,
                        "major": report.major_count,
                        "anomalies": report.anomalies[:3],
                        "recommendations": report.recommendations[:2],
                    })
                except Exception:
                    pass
                self._auto_repair(report)
        except Exception as e:
            logger.debug(f"内省检查跳过: {e}")

    def _auto_repair(self, report):
        try:
            from core.perception_snapshot import get_snapshot
            snap = get_snapshot()
            for anomaly in report.anomalies[:5]:
                category = anomaly.category.value if hasattr(anomaly.category, 'value') else str(anomaly.category)
                title = anomaly.title if hasattr(anomaly, 'title') else str(anomaly)

                if category == "RESOURCE" and "内存" in title:
                    try:
                        mem = snap.resource.get("memory_usage", 0)
                        if mem > 0.85:
                            import gc
                            gc.collect()
                            logger.info("自动修复: 内存过高，执行gc.collect()")
                    except Exception:
                        pass

                elif category == "DATA_LOOP" and "规则" in title:
                    try:
                        db = DatabaseManager.get("data/learning_rules.db")
                        db.execute("DELETE FROM rules WHERE apply_count = 0 AND created_at < datetime('now', '-7 days')", commit=True)
                        logger.info("自动修复: 清理7天未使用的trial规则")
                    except Exception:
                        pass

                elif category == "SUBSYSTEM" and "任务" in title:
                    try:
                        paused = [j for j in self._jobs if not j.enabled]
                        for j in paused[:2]:
                            j.enabled = True
                            logger.info(f"自动修复: 重新启用任务 {j.name}")
                    except Exception:
                        pass

                elif category == "PERFORMANCE":
                    try:
                        from core.resource_awareness.background_controller import get_background_controller
                        bc = get_background_controller()
                        if hasattr(bc, 'set_mode'):
                            bc.set_mode("conservative")
                            logger.info("自动修复: 性能异常，切换到conservative模式")
                    except Exception:
                        pass

                elif category == "ALIGNMENT":
                    logger.warning(f"自动修复: 思想对齐异常需人工审查 - {title}")
        except Exception as e:
            logger.debug(f"自动修复跳过: {e}")

    def _job_deferred_deep_process(self):
        """
        回顾固化：处理延迟队列中的学习型输入

        当系统资源充足时，对之前因资源紧张而压缩过度的学习型输入
        进行后台深度处理——将完整内容存入经验池、提取真谛、更新知识图谱
        """
        try:
            from core.input_processor import get_input_processor
            processor = get_input_processor()
            deferred = processor.get_deferred_inputs(limit=3)
            if not deferred:
                return

            try:
                from core.resource_awareness.health_monitor import get_health_monitor
                monitor = get_health_monitor()
                snap = monitor.check()
                if snap.memory_usage > 0.75:
                    logger.debug("资源仍紧张，延迟深度处理跳过")
                    return
            except ImportError:
                pass

            processed_count = 0
            for item in deferred:
                try:
                    original_input = item.get("input", "")
                    skeleton = item.get("skeleton", {})
                    if not original_input or len(original_input) < 100:
                        continue

                    try:
                        db = DatabaseManager.get("data/experience_pool.db")
                        db.execute(
                            "INSERT OR IGNORE INTO experiences (raw_input, response, quality_score, intent_type, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
                            (original_input[:200], f"[延迟深度处理] 骨架: {skeleton.get('topic', 'unknown')}, 类型: {skeleton.get('question_type', 'unknown')}, 实体: {','.join(skeleton.get('entities', [])[:5])}", 30, "deferred_learning"),
                            commit=True
                        )
                    except Exception as e:
                        logger.debug(f"延迟输入存入经验池失败: {e}")

                    try:
                        from core.knowledge_graph import get_knowledge_graph, NodeType
                        kg = get_knowledge_graph()
                        for entity in skeleton.get("entities", [])[:3]:
                            existing = kg.search(entity, top_k=1)
                            if not existing:
                                new_node = kg.add_node(entity, node_type=NodeType.CONCEPT)
                                kg.auto_connect(new_node.id)
                    except Exception:
                        pass

                    if item in deferred:
                        processor.remove_deferred_input(item)
                    processed_count += 1
                except Exception as e:
                    logger.debug(f"延迟输入处理失败: {e}")

            if processed_count > 0:
                logger.info(f"延迟深度处理: 处理了{processed_count}条学习型输入，剩余{len(processor._deferred_inputs)}条")
        except Exception as e:
            logger.debug(f"延迟深度处理跳过: {e}")

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

    def _job_sleep_consolidation(self):
        try:
            consolidated = 0
            forgotten = 0

            db = DatabaseManager.get("data/experience_pool.db")
            row = db.query_one(
                "SELECT COUNT(*) FROM experiences WHERE quality_score >= 70 AND timestamp > datetime('now', '-7 days')"
            )
            high_value_count = row[0]

            cur = db.execute(
                "DELETE FROM experiences WHERE quality_score < 30 AND timestamp < datetime('now', '-30 days')",
                commit=True
            )
            forgotten = cur.rowcount

            cur = db.execute(
                "UPDATE experiences SET quality_score = MIN(quality_score + 5, 100) WHERE quality_score >= 70 AND timestamp > datetime('now', '-7 days')",
                commit=True
            )
            consolidated = cur.rowcount

            try:
                db2 = DatabaseManager.get("data/learning_rules.db")
                cur2 = db2.execute(
                    "DELETE FROM rules WHERE apply_count = 0 AND created_at < datetime('now', '-14 days')",
                    commit=True
                )
                rules_forgotten = cur2.rowcount
            except Exception:
                rules_forgotten = 0

            if consolidated > 0 or forgotten > 0:
                logger.info(f"睡眠巩固: 强化{consolidated}条高价值经验, 遗忘{forgotten}条低质量经验, 清理{rules_forgotten}条无用规则")
        except Exception as e:
            logger.debug(f"睡眠巩固跳过: {e}")


scheduled_task_manager = ScheduledTaskManager()
