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

_notification_port = None


def set_notification_port(port):
    global _notification_port
    _notification_port = port


def _notify(message: str, level: str = "info", **kwargs):
    if _notification_port is not None:
        _notification_port.notify(message, level=level, **kwargs)
    else:
        try:
            from backend.main_fast import _enqueue_proactivity
            _enqueue_proactivity({"type": level, "content": message, **kwargs})
        except Exception:
            pass


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
        self.register_job("layered_memory_sync", 21600.0, self._job_layered_memory_sync)
        self.register_job("slow_evolution", 3600.0, self._job_slow_evolution)
        self.register_job("proactivity_check", 600.0, self._job_proactivity_check)
        self.register_job("introspection", 300.0, self._job_introspection)
        self.register_job("deferred_deep_process", 600.0, self._job_deferred_deep_process)
        self.register_job("sleep_consolidation", 3600.0, self._job_sleep_consolidation)
        self.register_job("metabolism", 300.0, self._job_metabolism)
        self.register_job("capability_assessment", 1800.0, self._job_capability_assessment)
        self.register_job("self_modification_check", 3600.0, self._job_self_modification_check)
        self.register_job("system_diagnostics", 1800.0, self._job_system_diagnostics)
        self.register_job("l5_rollback_monitor", 600.0, self._job_l5_rollback_monitor)
        self.register_job("trial_rule_timeout", 86400.0, self._job_trial_rule_timeout)
        self.register_job("reality_check", 1800.0, self._job_reality_check)
        try:
            from core.resource_awareness.adaptive_governor import get_adaptive_governor
            from core.resource_awareness.health_monitor import OperatingMode
            governor = get_adaptive_governor()
            governor.on_mode_change(self._on_resource_mode_change)
            logger.info("✅ 已注册资源模式变更回调")
        except Exception as e:
            logger.warning(f"资源模式变更回调注册失败: {e}")

    def _on_resource_mode_change(self, old_mode, new_mode):
        try:
            from core.resource_awareness.health_monitor import OperatingMode
            _MODE_SEVERITY = {OperatingMode.NORMAL: 0, OperatingMode.CONSERVATIVE: 1, OperatingMode.EMERGENCY: 2}
            old_sev = _MODE_SEVERITY.get(old_mode, 0)
            new_sev = _MODE_SEVERITY.get(new_mode, 0)
            if new_sev > old_sev:
                from core.resource_awareness.health_monitor import OperatingMode
                from infrastructure.hardware_monitor import get_gpu_stats
                _gs = get_gpu_stats()
                _gpu_temp = _gs.get("temperature", 0) if _gs.get("available") else 0
                _mode_label = {OperatingMode.CONSERVATIVE: "保守", OperatingMode.EMERGENCY: "紧急"}.get(new_mode, "未知")
                _msg = f"系统进入{_mode_label}模式（GPU {_gpu_temp}°C），已自动降低并行度以保证稳定。"
                try:
                    _notify(_msg, level="warning", source="self_preservation")
                except Exception:
                    pass
                logger.warning(f"⚖️ 资源模式变更: {old_mode.value}→{new_mode.value}, 已通知用户")
            elif new_sev < old_sev:
                logger.info(f"⚖️ 资源恢复中: {old_mode.value}→{new_mode.value}, 冷却缓冲30秒后恢复")
        except Exception as e:
            logger.warning(f"资源模式变更回调异常: {e}")

    def register_job(self, name: str, interval_seconds: float, callback: Optional[Callable] = None):
        with self._lock:
            self._jobs[name] = ScheduledJob(
                name=name,
                interval_seconds=interval_seconds,
                callback=callback,
            )
        logger.warning(f"定时任务已注册: {name} (间隔{interval_seconds}s)")

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
            logger.warning("操作降级跳过")

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
            logger.warning(f"自检跳过: {e}")

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
            logger.warning(f"定时学习跳过: {e}")

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
            logger.warning(f"每日报告跳过: {e}")

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
            logger.warning(f"记忆衰减跳过: {e}")

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
            logger.warning(f"分层记忆同步跳过: {e}")

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
            logger.warning(f"慢循环进化跳过: {e}")

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
                    logger.warning("操作降级跳过")
                try:
                    _notify(
                        decision.content,
                        level="proactivity",
                        action_type=decision.action_type.value if decision.action_type else "unknown",
                        reason=decision.reason,
                        confidence=decision.confidence,
                    )
                except Exception:
                    logger.warning("操作降级跳过")
                try:
                    db = DatabaseManager.get("data/experience_pool.db")
                    db.execute(
                        "INSERT INTO experiences (raw_input, response, quality_score, intent_type, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
                        (f"[主动性:{decision.action_type.value if decision.action_type else 'unknown'}] {decision.reason}",
                         decision.content, int(decision.confidence * 50), "proactivity"),
                        commit=True
                    )
                except Exception:
                    logger.warning("操作降级跳过")
                try:
                    from core.knowledge_graph import get_knowledge_graph, NodeType as _NT
                    _kg = get_knowledge_graph()
                    _node = _kg.add_node(
                        f"主动性:{decision.action_type.value if decision.action_type else 'unknown'} - {decision.reason}",
                        node_type=_NT.EXPERIENCE, importance=decision.confidence * 0.6
                    )
                except Exception:
                    logger.warning("操作降级跳过")
            else:
                logger.warning(f"主动性检查: 暂无行动 (silence={silence:.0f}s)")
        except Exception as e:
            logger.warning(f"主动性检查跳过: {e}")

        # 好奇心驱动的主动提问
        try:
            from core.presence.curiosity_engine import get_curiosity_engine
            curiosity = get_curiosity_engine()
            action = curiosity.generate_question()
            if action and action.action_type == "ask_user":
                logger.info(f"🤔 好奇心提问: {action.content[:60]}")
                try:
                    _notify(action.content, level="curiosity", reason=action.reason, source="curiosity_engine")
                except Exception:
                    pass
        except Exception:
            pass

        # L5自触发回路：好奇心驱动的自我代码改进
        try:
            from core.self_modification.loop import self_modification_loop
            if self_modification_loop.can_run():
                from core.presence.curiosity_engine import get_curiosity_engine
                _curiosity = get_curiosity_engine()
                _gaps = _curiosity.perceive_gaps()
                _reflect_gaps = [g for g in _gaps if g.learning_strategy == "reflect_internal"]
                if _reflect_gaps:
                    _mod_result = self_modification_loop.run_from_lessons()
                    if _mod_result.triggered:
                        logger.info(
                            f"🔧 L5自触发(proactivity): "
                            f"缺陷={_mod_result.defects_found}, "
                            f"补丁={_mod_result.patches_generated}, "
                            f"提案={_mod_result.proposals_created}"
                        )
        except Exception:
            pass

        # L4善意延伸：资源状态感知的主动告知
        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            _hm = get_health_monitor()
            _mode = _hm.get_operating_mode()
            from core.resource_awareness.health_monitor import OperatingMode
            if _mode in (OperatingMode.CONSERVATIVE, OperatingMode.EMERGENCY):
                try:
                    from infrastructure.hardware_monitor import get_gpu_stats
                    _gs = get_gpu_stats()
                    _gpu_temp = _gs.get("temperature", 0) if _gs.get("available") else 0
                except Exception:
                    _gpu_temp = 0

                if _mode == OperatingMode.EMERGENCY:
                    _msg = f"系统资源紧张中（GPU {_gpu_temp}°C），我正在精简运行路径以保证稳定响应，回答可能稍简。"
                else:
                    _msg = f"我注意到GPU温度偏高（{_gpu_temp}°C），已自动降低并行度，不影响回答但速度可能稍慢。"

                try:
                    _notify(_msg, level="warning", source="self_preservation")
                except Exception:
                    pass
        except Exception:
            pass

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
                    logger.warning("操作降级跳过")
                try:
                    _notify(
                        f"系统异常: 健康={report.overall_health:.1%}, 严重={report.critical_count}, 主要={report.major_count}",
                        level="system_anomaly",
                        health=report.overall_health,
                        critical=report.critical_count,
                        major=report.major_count,
                    )
                except Exception:
                    logger.warning("操作降级跳过")
                self._auto_repair(report)
        except Exception as e:
            logger.warning(f"内省检查跳过: {e}")

    def _auto_repair(self, report):
        try:
            from core.perception_snapshot import get_snapshot
            snap = get_snapshot()
            for anomaly in report.anomalies[:5]:
                if isinstance(anomaly, dict):
                    category = anomaly.get("category", "")
                    title = anomaly.get("title", str(anomaly))
                else:
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
                        logger.warning("操作降级跳过")

                elif category == "DATA_LOOP" and "规则" in title:
                    try:
                        db = DatabaseManager.get("data/learning_rules.db")
                        db.execute("DELETE FROM rules WHERE apply_count = 0 AND created_at < datetime('now', '-7 days')", commit=True)
                        logger.info("自动修复: 清理7天未使用的trial规则")
                    except Exception:
                        logger.warning("操作降级跳过")

                elif category == "SUBSYSTEM" and "任务" in title:
                    try:
                        paused = [j for j in self._jobs if not j.enabled]
                        for j in paused[:2]:
                            j.enabled = True
                            logger.info(f"自动修复: 重新启用任务 {j.name}")
                    except Exception:
                        logger.warning("操作降级跳过")

                elif category == "PERFORMANCE":
                    try:
                        from core.resource_awareness.background_controller import get_background_controller
                        bc = get_background_controller()
                        if hasattr(bc, 'set_mode'):
                            bc.set_mode("conservative")
                            logger.info("自动修复: 性能异常，切换到conservative模式")
                    except Exception:
                        logger.warning("操作降级跳过")

                elif category == "ALIGNMENT":
                    logger.warning(f"自动修复: 思想对齐异常需人工审查 - {title}")
        except Exception as e:
            logger.warning(f"自动修复跳过: {e}")

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
                        logger.error(f"延迟输入存入经验池失败: {e}")

                    try:
                        from core.knowledge_graph import get_knowledge_graph, NodeType
                        kg = get_knowledge_graph()
                        for entity in skeleton.get("entities", [])[:3]:
                            existing = kg.search(entity, top_k=1)
                            if not existing:
                                new_node = kg.add_node(entity, node_type=NodeType.CONCEPT)
                                kg.auto_connect(new_node.id)
                    except Exception:
                        logger.warning("操作降级跳过")

                    if item in deferred:
                        processor.remove_deferred_input(item)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"延迟输入处理失败: {e}")

            if processed_count > 0:
                logger.info(f"延迟深度处理: 处理了{processed_count}条学习型输入，剩余{len(processor._deferred_inputs)}条")
        except Exception as e:
            logger.warning(f"延迟深度处理跳过: {e}")

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
                logger.info(f"睡眠巩固: {high_value_count}条高价值经验, 强化{consolidated}条, 遗忘{forgotten}条低质量经验, 清理{rules_forgotten}条无用规则")
        except Exception as e:
            logger.warning(f"睡眠巩固跳过: {e}")

    def _job_metabolism(self):
        try:
            from core.instinct.metabolism import metabolism_orchestrator
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(metabolism_orchestrator.tick())
            finally:
                loop.close()
            status = metabolism_orchestrator.get_status()
            logger.debug(
                f"⏰ 代谢: 阶段={status['phase']}, "
                f"完整循环={status['stats']['full_cycles']}, "
                f"快速摄入={status['stats']['quick_ingests']}, "
                f"跳过峰值={status['stats']['skipped_peak']}"
            )
        except Exception as e:
            logger.warning(f"代谢跳过: {e}")

    def _job_capability_assessment(self):
        """
        闭环3：能力自我提升
        定期评估SelfModel能力画像，检测短板并自动触发能力创造回路。
        链路：SelfModel.evaluate_and_act() → capability_gaps → capability_creation_loop
        """
        try:
            from core.self.model import get_self_model
            sm = get_self_model()

            try:
                from core.services.cognitive_planner import get_cognitive_planner
                cp = get_cognitive_planner()
                if cp:
                    sm.sync_from_cognitive_planner(cp)
            except Exception:
                pass

            actions = sm.evaluate_and_act()

            gap_actions = [a for a in actions if a.get("action") == "capability_gap_learning"]
            if gap_actions:
                logger.info(f"🧠 闭环3：检测到能力缺口，触发能力创造回路")
                try:
                    from infrastructure.database_manager import DatabaseManager
                    db = DatabaseManager.get("data/capability_gaps.db")
                    rows = db.query(
                        "SELECT query, gap_type, failed_paths FROM capability_gaps WHERE resolved=0 ORDER BY attempts DESC LIMIT 3"
                    )
                    for row in rows:
                        query, gap_type, failed_paths = row[0], row[1], row[2] or ""
                        try:
                            from core.capability_creation_loop import capability_creation_loop
                            loop = asyncio.new_event_loop()
                            try:
                                result = loop.run_until_complete(
                                    capability_creation_loop.handle(query, context={"intent_type": gap_type, "trigger": "capability_assessment"})
                                )
                                if result and result.get("handled"):
                                    logger.info(f"🧠 闭环3：能力创造成功 query={query[:40]} method={result.get('method', '?')}")
                                else:
                                    logger.debug(f"🧠 闭环3：能力创造未解决 query={query[:40]}")
                            finally:
                                loop.close()
                        except Exception as e:
                            logger.warning(f"闭环3能力创造跳过 [{gap_type}]: {e}")
                except Exception as e:
                    logger.warning(f"闭环3缺口查询跳过: {e}")

            profile = sm.snapshot().get("capability_profile", {})
            strength = profile.get("overall_strength", 0)
            gaps = profile.get("gaps", [])
            logger.info(
                f"🧠 闭环3能力评估: strength={strength:.2f}, gaps={len(gaps)}, "
                f"actions={len(actions)}, gap_actions={len(gap_actions)}"
            )
        except Exception as e:
            logger.warning(f"能力评估跳过: {e}")

    def _job_self_modification_check(self):
        """L5自修改循环：定期检查代码缺陷并生成修复提案"""
        try:
            from core.self_modification.loop import self_modification_loop
            if not self_modification_loop.can_run():
                return

            target_files = [
                "core/cognitive_dispatcher.py",
                "core/truth_accumulator.py",
                "core/skill_emergence.py",
                "core/presence/curiosity_engine.py",
                "core/presence/gap_growth.py",
                "core/presence/existence_layer.py",
                "core/task_queue.py",
                "infrastructure/scheduled_tasks.py",
            ]

            total_defects = 0
            total_proposals = 0
            for f in target_files:
                try:
                    result = self_modification_loop.run_from_file(f)
                    if result.triggered:
                        total_defects += result.defects_found
                        total_proposals += result.proposals_created
                except Exception as e:
                    logger.debug(f"L5检查{f}跳过: {e}")

            if total_defects > 0:
                logger.info(f"🔧 L5自修改检查: 发现{total_defects}个缺陷, 生成{total_proposals}个提案")
            else:
                logger.debug("🔧 L5自修改检查: 未发现缺陷")

        except Exception as e:
            logger.warning(f"L5自修改检查跳过: {e}")

    def _job_system_diagnostics(self):
        """系统自诊断：通过安全的CMD/PowerShell命令检测系统健康"""
        try:
            from core.system_diagnostician import system_diagnostician
            results = system_diagnostician.run_quick()
            report = system_diagnostician.get_diagnostic_report()

            if report["error_count"] > 0:
                logger.warning(f"🏥 系统诊断: {report['error_count']}个错误, "
                              f"{report['warning_count']}个警告")
                for err in report.get("errors", []):
                    logger.warning(f"  ❌ {err['probe']}: {err['summary']}")
                    if err.get("fix"):
                        logger.info(f"     💡 建议: {err['fix']}")
            elif report["warning_count"] > 0:
                logger.info(f"🏥 系统诊断: {report['warning_count']}个警告, "
                           f"{report['ok_count']}项正常")
            else:
                logger.debug(f"🏥 系统诊断: 全部{report['ok_count']}项正常")

        except Exception as e:
            logger.warning(f"系统诊断跳过: {e}")

    def _job_l5_rollback_monitor(self):
        """L5回滚监控：检查最近部署的补丁是否导致系统退化"""
        try:
            from core.self_modification.patch_sandbox_deployer import patch_deployer
            rollbacks = patch_deployer.monitor_deployed()
            if rollbacks:
                for rb in rollbacks:
                    logger.warning(f"🔄 L5自动回滚: {rb['proposal_id']} ({rb['file']}) — {rb['reason']}")
            else:
                logger.debug("🔄 L5回滚监控: 所有补丁运行正常")
        except Exception as e:
            logger.debug(f"L5回滚监控跳过: {e}")

    def _job_trial_rule_timeout(self):
        """规则闭环：处理超时trial规则，自动激活/过期/桥接条件格式"""
        try:
            from infrastructure.rule_trial_manager import rule_trial_manager
            result = rule_trial_manager.process_timeout_trials(timeout_days=30)
            if any(v > 0 for v in result.values()):
                logger.info(
                    f"⏰ 规则闭环: 激活={result['activated']}, 过期={result['expired']}, "
                    f"提升置信={result['promoted']}, 条件桥接={result['bridged']}"
                )
            else:
                logger.debug("⏰ 规则闭环: 无超时trial需处理")
        except Exception as e:
            logger.warning(f"规则闭环处理跳过: {e}")

    def _job_reality_check(self):
        """现实校验：对比系统自报告与运行时实际数据，检测叙事-现实鸿沟"""
        try:
            from core.self.reality_check import reality_check
            result = reality_check.run_check()
            gaps = result.get("gaps", [])
            alignment = result.get("alignment_score", 1.0)
            if gaps:
                logger.warning(
                    f"🔍 现实校验: 对齐度={alignment:.2f}, "
                    f"发现{len(gaps)}个叙事-现实差距"
                )
            else:
                logger.debug(f"🔍 现实校验: 叙事与现实对齐 (score={alignment:.2f})")
        except Exception as e:
            logger.warning(f"现实校验跳过: {e}")


scheduled_task_manager = ScheduledTaskManager()
