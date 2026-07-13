"""
生命周期管理 - 从main_fast.py抽离的启动/关闭序列

职责：
  1. 服务启动时初始化所有子系统
  2. 服务关闭时优雅地停止所有子系统
  3. 周期性自我评估与自动修复
  4. 事件总线订阅与主动性消息广播
"""

import asyncio
import gc
import json
from datetime import datetime
from contextlib import asynccontextmanager
from loguru import logger



def _inject_evolved_genome(genome: dict, fitness: float = 0.0):
    try:
        from infrastructure.config_manager import config_manager
        _flags = config_manager.get("feature_flags", {})
        if not _flags.get("evolution_safety_protocol", True):
            logger.info("进化岛安全协议已禁用(feature flag)，跳过基因组注入")
            return
    except Exception:
        pass
    from core.genome_evolver import genome_evolver
    proposal = genome_evolver.propose_evolution_injection(genome, fitness, source="evolution_island")
    if proposal.get("status") == "rejected":
        logger.warning(f"进化岛基因组注入被安全协议拒绝: {proposal.get('violations')}")
        return
    proposal_id = proposal["proposal_id"]
    steps = ["sandbox", "inject_1pct", "inject_20pct", "inject_100pct"]
    for step in steps:
        result = genome_evolver.execute_injection_step(proposal_id, step)
        if result.get("status") == "error":
            logger.error(f"进化注入步骤{step}失败: {result.get('message')}")
            genome_evolver.execute_injection_step(proposal_id, "rollback")
            return
    logger.info(f"进化岛基因组已通过安全协议注入: {proposal_id}")


def _import_evolved_skills(skills: list):
    from infrastructure.database_manager import DatabaseManager
    db = DatabaseManager.get("data/knowledge_store.db")
    for skill in skills:
        name = skill.get('name', f"evolved_skill_{hash(str(skill)) % 10000}")
        code = skill.get('code', '')
        trigger = skill.get('trigger', '')
        existing = db.query_one("SELECT 1 FROM tools WHERE name = ?", (name,))
        if existing:
            continue
        db.execute(
            "INSERT INTO tools (name, code, trigger_pattern, status) VALUES (?, ?, ?, 'active')",
            (name, code, trigger), commit=True
        )


# ========== 主动性SSE广播 ==========

_proactivity_subscribers: list = []


def _broadcast_proactivity(msg: dict):
    """向所有SSE订阅者广播主动性消息"""
    dead_qs = []
    for q in _proactivity_subscribers:
        try:
            q.put_nowait(json.dumps({"type": "proactivity", "data": msg}))
        except asyncio.QueueFull:
            dead_qs.append(q)
    for q in dead_qs:
        _proactivity_subscribers.remove(q)


def _enqueue_proactivity(msg: dict):
    """入队主动性消息（如果存在SSE订阅者）"""
    try:
        if not _proactivity_subscribers:
            logger.warning(f"无SSE订阅者，消息丢弃: type={msg.get('type')}")
            return
        _broadcast_proactivity(msg)
        logger.info(f"主动性消息已广播: type={msg.get('type')} subscribers={len(_proactivity_subscribers)}")
    except Exception as e:
        logger.warning(f"主动性消息广播失败: {e}")


# ========== 启动序列 ==========

async def _start_resource_awareness():
    """初始化资源感知系统"""
    try:
        from core.resource_awareness.health_monitor import get_health_monitor
        from core.resource_awareness.adaptive_governor import get_adaptive_governor
        from core.resource_awareness.background_controller import get_background_controller
        monitor = get_health_monitor()
        snap = monitor.check()
        logger.info(f"资源感知已启动: MEM={snap.memory_usage:.1%}, Threads={snap.thread_count}, Mode={snap.mode.value}")
        get_adaptive_governor()
        get_background_controller()
    except Exception as e:
        logger.warning(f"资源感知启动失败: {e}")


async def _start_vector_index():
    """加载向量检索索引"""
    try:
        from infrastructure.vector_retriever import vector_retriever
        vector_retriever.load_index()
        logger.info(f"向量检索索引已加载: {vector_retriever.current_id}条记录")
    except Exception as e:
        logger.warning(f"向量检索索引加载失败: {e}")


async def _start_task_queue():
    """启动持久化任务队列worker"""
    try:
        from core.task_queue import task_queue
        asyncio.create_task(task_queue.start_worker(interval=5.0))
        logger.info("持久化任务队列worker已启动")
    except Exception as e:
        logger.warning(f"任务队列启动失败: {e}")


async def _start_guardian():
    """启动SDRS系统守护者巡逻"""
    try:
        from core.defense.guardian import system_guardian
        asyncio.create_task(system_guardian.start_patrol(interval=60))
        logger.info("SDRS系统守护者已启动巡逻")
    except Exception as e:
        logger.warning(f"系统守护者启动失败: {e}")


async def _start_hardware_monitoring():
    """启动硬件监控定时记录（每30秒）"""
    async def _periodic_hardware_log():
        await asyncio.sleep(10)
        while True:
            try:
                from infrastructure.hardware_monitor import log_hardware_stats
                log_hardware_stats(force=True)
            except Exception:
                logger.warning("操作降级跳过")
            await asyncio.sleep(30)

    asyncio.create_task(_periodic_hardware_log())
    logger.info("硬件监控定时记录已启动(30秒间隔)")


async def _start_assessment_loop(app):
    """启动持续自我评估（每5分钟一次，评估→诊断→修复闭环）"""
    async def _assessment_driven_repair(report: dict):
        """评估驱动的自动修复"""
        score = report["overall"]["score"]

        # 闭环完整性低 → 触发低负载重组
        loop_score = report.get("loop_integrity", {}).get("score", 1.0)
        if loop_score < 0.5:
            try:
                from core.low_load_reorganization import low_load_reorganization
                result = low_load_reorganization.run()
                s = result.get("summary", {})
                if any(v > 0 for v in s.values()):
                    logger.info(f"评估驱动重组: 激活{s.get('rules_activated',0)} 合并{s.get('rules_merged',0)} 提取{s.get('rules_extracted',0)}")
            except Exception as e:
                logger.error(f"评估驱动重组失败: {e}")

        # 知识活力低 → 触发遗忘清理
        vitality_score = report.get("knowledge_vitality", {}).get("score", 1.0)
        if vitality_score < 0.5:
            try:
                from core.knowledge_forgetting import knowledge_forgetting
                result = knowledge_forgetting.execute_fading(dry_run=False)
                logger.info(f"评估驱动遗忘: 规则淡化{result['rules']['faded']}+清除{result['rules']['pruned']}, 经验淡化{result['experiences']['faded']}+清除{result['experiences']['pruned']}")
            except Exception as e:
                logger.error(f"评估驱动遗忘失败: {e}")

        # 行为偏差 → 触发认知自修复
        deviation = report.get("behavior_deviation", {})
        if deviation.get("deviations"):
            try:
                from core.defense.cognitive_self_repair import cognitive_self_repair
                result = cognitive_self_repair.run_full_repair()
                logger.info(f"评估驱动修复: {result['repairs']}")
            except Exception as e:
                logger.error(f"评估驱动修复失败: {e}")

    async def _periodic_assessment():
        await asyncio.sleep(120)
        while True:
            try:
                from core.self_assessment import self_assessment
                report = self_assessment.assess()
                level = report["overall"]["level"]
                score_val = report["overall"]["score"]
                logger.info(f"自我评估完成: {level} ({score_val:.2f})")
                if report["recommendations"]:
                    for rec in report["recommendations"][:3]:
                        logger.info(f"  → [{rec['priority']}] {rec['action']}")

                # 评估→修复闭环
                await _assessment_driven_repair(report)
            except Exception as e:
                logger.error(f"自我评估失败: {e}")
            await asyncio.sleep(300)

    asyncio.create_task(_periodic_assessment())
    logger.info("持续自我评估已启动")


async def _start_evolution_loop(app):
    """启动周期性进化循环 — 让进化岛持续在线运行"""
    app.state.evolution_running = False
    app.state.evolution_generation = 0

    async def _periodic_evolution():
        await asyncio.sleep(300)
        while True:
            try:
                from core.evolution.evolution_island import run_evolution_sandbox
                app.state.evolution_running = True
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: run_evolution_sandbox(
                        main_db_path="data/knowledge_store.db",
                        num_agents=4,
                        generations=5,
                    )
                )
                app.state.evolution_generation += result.get("stats", {}).get("generations", 0)
                best_fitness = result.get("stats", {}).get("final_best_fitness", 0)
                logger.info(f"进化岛周期运行完成: 最优适应度={best_fitness:.3f}, 累计代数={app.state.evolution_generation}")

                if result.get("best_genome") and best_fitness > 0.5:
                    try:
                        _inject_evolved_genome(result["best_genome"], fitness=best_fitness)
                        logger.info(f"进化岛基因组安全注入流程已启动 (适应度={best_fitness:.3f})")
                    except Exception as inj_e:
                        logger.warning(f"进化岛基因组注入失败: {inj_e}")

                if result.get("best_skills"):
                    try:
                        _import_evolved_skills(result["best_skills"])
                        logger.info(f"进化岛技能已自动导入 ({len(result['best_skills'])}个)")
                    except Exception as imp_e:
                        logger.warning(f"进化岛技能导入失败: {imp_e}")

                _sm = None
                try:
                    from core.self.model import get_self_model
                    _sm = get_self_model()
                except Exception:
                    logger.warning("操作降级跳过")
                if _sm:
                    _sm.update("evolution", {
                        "last_fitness": best_fitness,
                        "total_generations": app.state.evolution_generation,
                        "last_run": datetime.now().isoformat(),
                    })

                app.state.evolution_running = False
            except Exception as e:
                logger.error(f"进化岛周期运行失败: {e}")
                app.state.evolution_running = False
            await asyncio.sleep(600)

    asyncio.create_task(_periodic_evolution())
    logger.info("进化岛持续在线已启动（每10分钟运行一次）")


async def _register_builtin_tools():
    """注册系统级工具"""
    try:
        from core.tool_registry import register_builtin_tools
        register_builtin_tools()
        logger.info("工具调用框架已初始化")
    except Exception as e:
        logger.warning(f"工具调用框架初始化失败: {e}")


async def _start_existence_layer():
    """启动存在层"""
    try:
        from core.presence.existence_layer import get_existence_layer
        existence_layer = get_existence_layer()
        existence_layer.start()
        logger.info("存在层已启动（心跳/生长/休息/睡眠四阶段循环）")
    except Exception as e:
        logger.warning(f"存在层启动失败: {e}")


async def _init_cognitive_planner(app):
    """延迟初始化认知规划器（不阻塞启动）"""
    app.state.cognitive_planner = None

    async def _init():
        try:
            from core.services.cognitive_planner import get_cognitive_planner
            cp = get_cognitive_planner()
            status = cp.get_system_status()
            logger.info(f"认知规划器已初始化(延迟): 对话数={status.get('conversation_count', 0)}, 组件={list(status.get('components', {}).keys())}")
            app.state.cognitive_planner = cp
        except Exception as e:
            logger.warning(f"认知规划器延迟初始化失败: {e}")

    asyncio.create_task(_init())
    logger.info("认知规划器已标记为延迟初始化")


async def _start_scheduled_tasks():
    """启动定时任务调度器"""
    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        scheduled_task_manager.start()
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.warning(f"定时任务调度器启动失败: {e}")


async def _register_event_bus():
    """注册事件总线订阅"""
    try:
        from infrastructure.event_bus import bus, EventTypes
        from core.presence.proactivity import get_proactivity_engine, ProactivityContext
        from core.relationship.model import get_relationship_model
        from core.presence.existence_layer import get_existence_layer

        def _on_idle_period(data):
            try:
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
                    engine.execute(decision)
                    _enqueue_proactivity({
                        "type": "proactivity",
                        "action_type": decision.action_type.value if decision.action_type else "unknown",
                        "content": decision.content,
                        "reason": decision.reason,
                        "confidence": decision.confidence,
                    })
            except Exception:
                logger.warning("操作降级跳过")

        def _on_knowledge_update(data):
            try:
                from core.knowledge_graph import get_knowledge_graph, NodeType
                kg = get_knowledge_graph()
                if isinstance(data, dict) and data.get("content"):
                    kg.add_node(data["content"], node_type=NodeType.FACT, importance=0.6)
            except Exception:
                logger.warning("操作降级跳过")

        def _on_system_health(data):
            try:
                if isinstance(data, dict) and data.get("health", 1.0) < 0.5:
                    gc.collect()
                    logger.info("事件驱动: 系统健康度过低，执行gc.collect()")
            except Exception:
                logger.warning("操作降级跳过")

        bus.subscribe(EventTypes.IdlePeriod, _on_idle_period)
        bus.subscribe(EventTypes.KnowledgeUpdate, _on_knowledge_update)
        bus.subscribe(EventTypes.SystemHealth, _on_system_health)
        logger.info("事件总线订阅已注册（IdlePeriod/KnowledgeUpdate/SystemHealth）")
    except Exception as e:
        logger.warning(f"事件总线订阅注册失败: {e}")


# ========== 关闭序列 ==========

async def _stop_cognitive_planner(app):
    """关闭认知规划器"""
    try:
        if hasattr(app.state, 'cognitive_planner') and app.state.cognitive_planner:
            app.state.cognitive_planner.shutdown()
            logger.info("认知规划器已关闭")
    except Exception:
        logger.warning("操作降级跳过")


async def _stop_existence_layer():
    """停止存在层"""
    try:
        from core.presence.existence_layer import get_existence_layer
        existence_layer = get_existence_layer()
        existence_layer.stop()
    except Exception:
        logger.warning("操作降级跳过")


async def _stop_scheduled_tasks():
    """停止定时任务调度器"""
    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        scheduled_task_manager.stop()
    except Exception:
        logger.warning("操作降级跳过")


async def _stop_file_monitor(app):
    """停止文件变化感知"""
    try:
        if hasattr(app.state, 'directory_monitor') and app.state.directory_monitor:
            app.state.directory_monitor.stop()
    except Exception:
        logger.warning("操作降级跳过")


async def _stop_task_queue():
    """停止任务队列"""
    try:
        from core.task_queue import task_queue
        task_queue.stop_worker()
    except Exception:
        logger.warning("操作降级跳过")


# ========== 主生命周期 ==========

@asynccontextmanager
async def lifespan(app):
    """完整启动/关闭序列"""
    logger.info("启动后端服务...")

    # === 启动序列 ===
    await _start_resource_awareness()
    await _start_vector_index()
    await _start_task_queue()

    # 初始化反思管道（延迟到首次使用时初始化）
    app.state.reflection_pipeline = None
    logger.info("反思管道已标记为延迟初始化")

    await _start_guardian()
    await _start_hardware_monitoring()
    await _start_assessment_loop(app)
    await _start_evolution_loop(app)
    await _register_builtin_tools()
    await _start_existence_layer()
    try:
        from core.evolution.pattern_migrator import PatternMigrator
        PatternMigrator.bootstrap()
    except Exception as e:
        logger.warning(f"模式迁移器引导跳过: {e}")
    await _init_cognitive_planner(app)
    await _start_scheduled_tasks()
    await _register_event_bus()

    # 文件变化感知 — 因config_manager兼容性问题暂不自动启动
    logger.info("文件变化感知已标记为手动模式（config_manager兼容性问题）")

    # 让服务开始处理请求
    yield

    # === 关闭序列 ===
    await _stop_cognitive_planner(app)
    await _stop_existence_layer()
    await _stop_scheduled_tasks()
    await _stop_file_monitor(app)
    await _stop_task_queue()

    logger.info("后端服务关闭")
