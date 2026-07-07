"""
进化与认知路由 — genes/skills/truths/evolution/cbnr/presence/memory/relationship/agent/tools/perception
"""
import sqlite3
import asyncio
import json
from pathlib import Path
from fastapi import APIRouter
from loguru import logger

router = APIRouter()

ROOT_DIR = Path(__file__).parent.parent.parent


@router.get("/genes")
async def get_genes():
    try:
        from core.task_queue import gene_pool
        profile = gene_pool.get_expression_profile()
        profile["mutation_history"] = gene_pool.get_mutation_history(10)
        return profile
    except Exception:
        return {"genes": {}, "mutation_history": [], "radar": {}, "personality": "unknown"}


@router.get("/skills")
async def get_skills():
    try:
        from core.skill_emergence import skill_emergence
        return skill_emergence.get_skill_stats()
    except Exception:
        return {"total_skills": 0, "mature_skills": 0, "top_skills": []}


@router.get("/truths")
async def get_truths():
    try:
        from core.truth_accumulator import truth_accumulator
        stats = truth_accumulator.get_stats()
        stats["entropy"] = truth_accumulator.get_cognitive_entropy()
        stats["reorganization_candidates"] = len(truth_accumulator.get_reorganization_candidates())
        return stats
    except Exception:
        return {"total_truths": 0, "by_level": {}, "top_truths": [], "entropy": {}, "reorganization_candidates": 0}


@router.get("/truths/entropy")
async def get_cognitive_entropy():
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.get_cognitive_entropy()
    except Exception:
        return {"entropy_score": 0, "status": "unknown"}


@router.post("/truths/reorganization/propose")
async def propose_reorganization():
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.propose_reorganization()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/truths/reorganization/approve")
async def approve_reorganization(request: dict):
    proposal_id = request.get("proposal_id", "")
    approver = request.get("approver", "human")
    if not proposal_id:
        return {"status": "error", "message": "缺少proposal_id"}
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.approve_reorganization(proposal_id, approver)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/truths/reorganization/execute")
async def execute_reorganization_step(request: dict):
    proposal_id = request.get("proposal_id", "")
    step = request.get("step", "")
    if not proposal_id or not step:
        return {"status": "error", "message": "缺少proposal_id或step"}
    try:
        from core.truth_accumulator import truth_accumulator
        return truth_accumulator.execute_reorganization_step(proposal_id, step)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/evolution/run")
async def run_evolution(request: dict):
    num_agents = request.get("num_agents", 8)
    generations = request.get("generations", 20)
    try:
        from core.active_scheduler import ActiveScheduler
        scheduler = ActiveScheduler(interval_seconds=300)
        result = scheduler.run_evolution_sandbox(num_agents=num_agents, generations=generations)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"进化岛运行失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/cbnr/process")
async def cbnr_process(request: dict):
    try:
        from core.cbnr.hub import get_cbnr_hub
        hub = get_cbnr_hub()
        result = hub.process(
            input_stream={"user_input": request.get("input", ""), "intent": request.get("intent", "")},
            context={"resource_mode": request.get("resource_mode", "normal")}
        )
        return {
            "l1": {
                "uncertainty": result.l1_normalization.uncertainty if result.l1_normalization else 0,
                "strength": result.l1_normalization.normalization_strength if result.l1_normalization else 0,
                "biases_cleared": result.l1_normalization.bias_cleared if result.l1_normalization else [],
                "principles": result.l1_normalization.principles_anchored if result.l1_normalization else [],
                "predictions": len(result.l1_normalization.predictions) if result.l1_normalization else 0,
            },
            "l2": {
                "compression_ratio": result.l2_bottleneck.compression_ratio if result.l2_bottleneck else 0,
                "conflict_delta": result.l2_bottleneck.conflict_delta if result.l2_bottleneck else 0,
                "conflict_mode": result.l2_bottleneck.conflict_mode.value if result.l2_bottleneck else "unknown",
                "topic": result.l2_bottleneck.core_essence.get("topic", "") if result.l2_bottleneck else "",
            },
            "l3": {
                "reuse_rate": result.l3_residual.state_reuse_rate if result.l3_residual else 0,
                "search_tree_size": result.l3_residual.search_tree_size if result.l3_residual else 0,
                "fallback_used": result.l3_residual.fallback_used if result.l3_residual else False,
            },
            "processing_time_ms": result.processing_time_ms,
            "questions": result.questions_asked,
            "final_output": result.final_output,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/cbnr/stats")
async def cbnr_stats():
    try:
        from core.cbnr.hub import get_cbnr_hub
        hub = get_cbnr_hub()
        return hub.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/memory/search")
async def search_memory(q: str = "", limit: int = 10):
    try:
        from core.memory.stereo_memory import get_stereo_memory
        sm = get_stereo_memory()
        if q:
            results = sm.search(query=q, limit=limit)
        else:
            results = sm.get_recent(limit=limit)
        return {
            "count": len(results),
            "memories": [
                {
                    "id": m.memory_id,
                    "content": str(m.content)[:200],
                    "type": m.memory_type.value,
                    "importance": m.importance,
                    "emotion": m.self_dimension.emotional_state,
                    "confidence": m.self_dimension.confidence,
                    "accessed": m.time_dimension.access_count,
                }
                for m in results
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/memory/stats")
async def memory_stats():
    try:
        from core.memory.stereo_memory import get_stereo_memory
        sm = get_stereo_memory()
        return sm.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/relationship/summary")
async def relationship_summary():
    try:
        from core.relationship.model import get_relationship_model
        rm = get_relationship_model()
        return rm.get_relationship_summary()
    except Exception as e:
        return {"error": str(e)}


@router.get("/relationship/metrics")
async def relationship_metrics():
    try:
        from core.relationship.model import get_relationship_model
        rm = get_relationship_model()
        return rm.get_metrics()
    except Exception as e:
        return {"error": str(e)}


@router.get("/presence/status")
async def presence_status():
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        return el.get_status()
    except Exception as e:
        return {"error": str(e)}


@router.post("/presence/signal")
async def send_presence_signal(request: dict):
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el.receive_signal(request)
        return {"status": "received"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/presence/force-state")
async def force_presence_state(request: dict):
    try:
        from core.presence.existence_layer import get_existence_layer, PresenceState
        el = get_existence_layer()
        state = PresenceState(request.get("state", "awake"))
        el.force_state(state)
        return {"status": "forced", "state": state.value}
    except Exception as e:
        return {"error": str(e)}


@router.get("/perception/snapshot")
async def get_perception_snapshot(force: bool = False):
    try:
        from core.perception_snapshot import get_snapshot
        snap = get_snapshot(force_refresh=force)
        return {
            "timestamp": snap.timestamp,
            "age_seconds": snap.age_seconds(),
            "resource": snap.resource,
            "knowledge": snap.knowledge,
            "interaction": snap.interaction,
            "existence": snap.existence,
            "health": snap.health,
            "identity": snap.identity,
            "action_trace": snap.action_trace,
            "summary": snap.summary(),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/tools")
async def list_tools(category: str = ""):
    try:
        from core.tool_registry import tool_registry
        tools = tool_registry.list_tools(category=category or None)
        return {"tools": tools, "total": len(tools)}
    except Exception as e:
        return {"tools": [], "total": 0, "error": str(e)}


@router.post("/tools/execute")
async def execute_tool(request: dict):
    tool_name = request.get("tool", "")
    params = request.get("params", {})
    if not tool_name:
        return {"success": False, "error": "缺少tool参数"}
    try:
        from core.tool_registry import tool_executor
        result = await tool_executor.execute(tool_name, params)
        return {
            "success": result.success,
            "data": result.data if result.success else None,
            "error": result.error if not result.success else None,
            "source": result.source,
            "quality": result.quality,
            "duration_ms": result.duration_ms,
            "from_cache": result.from_cache,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/tools/stats")
async def get_tool_stats():
    try:
        from core.tool_registry import tool_executor, tool_registry
        return {
            "tools": tool_registry.list_tools(),
            "stats": tool_executor.get_stats(),
            "total_tools": tool_registry.tool_count,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/tools/history")
async def get_tool_history(limit: int = 20):
    try:
        db_path = str(ROOT_DIR / "data" / "tool_cache.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT tool_name, params_hash, created_at, quality_score, hit_count FROM tool_cache ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        records = []
        for row in cursor.fetchall():
            records.append({
                "tool_name": row[0],
                "params_hash": (row[1] or "")[:8],
                "created_at": row[2],
                "quality": row[3],
                "hits": row[4] or 0,
            })
        conn.close()
        return {"history": records, "total": len(records)}
    except Exception as e:
        return {"error": str(e), "history": []}


@router.get("/proactivity/evaluate")
async def evaluate_proactivity():
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
            last_proactivity_time=datetime.now(),
            user_engagement_level=0.5,
        )

        decision = engine.evaluate(ctx)
        return {
            "should_act": decision.should_act,
            "action_type": decision.action_type.value if decision.action_type else None,
            "content": decision.content,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "timing_score": decision.timing_score,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/closed-loop/orchestrate")
async def closed_loop_orchestrate(request: dict):
    try:
        from core.closed_loop_orchestrator import closed_loop_orchestrator
        ctx = await closed_loop_orchestrator.orchestrate(
            query=request.get("query", ""),
            conversation_context=request.get("context", ""),
        )
        return {
            "response": ctx.final_response,
            "iterations": ctx.iteration + 1,
            "passed": ctx.evaluation_passed,
            "confidence": ctx.confidence,
            "attempts": [(a[0], a[1]) for a in ctx.attempts],
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/agent/collaborate")
async def agent_collaborate(request: dict):
    query = request.get("message", "")
    if not query:
        return {"success": False, "error": "消息不能为空"}
    try:
        from core.agents.coordinator import agent_coordinator
        result = await asyncio.wait_for(
            agent_coordinator.collaborate(query),
            timeout=90,
        )
        return {
            "success": result.get("success", True),
            "response": result.get("response", ""),
            "source": result.get("source", ""),
            "quality": result.get("quality", 0),
            "iterations": result.get("iterations", 0),
            "plan_id": result.get("plan_id", ""),
            "duration_ms": result.get("duration_ms", 0),
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": "Agent协作超时(90s)", "response": "处理超时，请使用/api/chat接口"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/agent/status")
async def agent_status():
    try:
        from core.agents.coordinator import agent_coordinator
        return agent_coordinator.get_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    try:
        from core.persistent_tasks import persistent_task_system
        status = await persistent_task_system.get_task_status(task_id)
        return status
    except Exception as e:
        return {"error": str(e)}