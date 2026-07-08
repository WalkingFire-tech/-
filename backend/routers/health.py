"""
健康检查路由 — /api/health, /api/resource-status, /api/hardware/status
"""
from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "version": "3.8.0"}


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