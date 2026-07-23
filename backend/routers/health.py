"""
健康检查路由 — /api/health, /api/resource-status, /api/hardware/status
"""
from fastapi import APIRouter, Request
from loguru import logger

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """健康检查 — 区分基础就绪和完全就绪"""
    initialized = getattr(request.app.state, "initialized", False)

    subsystems = {}
    cp = getattr(request.app.state, "cognitive_planner", None)
    subsystems["cognitive_planner"] = cp is not None

    try:
        from infrastructure.vector_retriever import vector_retriever
        subsystems["vector_index"] = len(vector_retriever._texts) > 0
    except Exception:
        subsystems["vector_index"] = False

    fully_ready = initialized and all(subsystems.values())

    return {
        "status": "ok" if fully_ready else ("degraded" if initialized else "starting"),
        "ready": initialized,
        "fully_ready": fully_ready,
        "subsystems": subsystems,
        "version": "4.0.0",
    }


@router.get("/resource-status")
async def resource_status():
    try:
        from core.resource_awareness.adaptive_governor import get_adaptive_governor
        governor = get_adaptive_governor()
        return governor.get_status()
    except Exception as e:
        return {"error": str(e), "mode": "unknown"}


@router.get("/hardware/status")
async def get_hardware_status():
    try:
        from infrastructure.hardware_monitor import get_all_hardware_stats, log_hardware_stats
        log_hardware_stats()
        return get_all_hardware_stats()
    except Exception as e:
        return {"error": str(e)}
