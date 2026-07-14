"""
健康检查路由 — /api/health, /api/resource-status, /api/hardware/status
"""
from fastapi import APIRouter, Request
from loguru import logger

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """健康检查 — 仅在所有子系统初始化完成后返回 ready: true"""
    initialized = getattr(request.app.state, "initialized", False)
    return {
        "status": "ok" if initialized else "starting",
        "ready": initialized,
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
