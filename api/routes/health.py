"""MATRIX Health and Diagnostics API Route.
Provides real-time system, database, and operational health telemetry.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import psutil
import time
from database.session import get_db, check_db_health
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("api.health")
router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_health(db: AsyncSession = Depends(get_db)):
    """Health check endpoint delivering real verified hardware and DB telemetry."""
    start_time = time.perf_counter()
    db_healthy = await check_db_health()
    db_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Memory telemetry
    vm = psutil.virtual_memory()
    total_ram_mb = round(vm.total / (1024 * 1024), 2)
    available_ram_mb = round(vm.available / (1024 * 1024), 2)
    used_ram_mb = round(vm.used / (1024 * 1024), 2)

    # Storage telemetry
    disks = {}
    for drive in ["C:", "D:"]:
        try:
            usage = psutil.disk_usage(f"{drive}\\")
            disks[drive] = {
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "used_percent": usage.percent
            }
        except Exception:
            disks[drive] = {"available": False}

    # CPU telemetry
    cpu_percent = psutil.cpu_percent(interval=None)

    overall_status = "healthy" if db_healthy and vm.percent < settings.max_ram_percent else "degraded"

    return {
        "status": overall_status,
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.env,
        "database": {
            "connected": db_healthy,
            "type": "SQLite (Async aiosqlite)",
            "path": str(settings.data_dir / "matrix.db"),
            "latency_ms": db_latency_ms
        },
        "system": {
            "cpu_percent": cpu_percent,
            "cpu_cores_physical": settings.cpu_cores,
            "cpu_threads_logical": settings.cpu_threads,
            "ram_total_mb": total_ram_mb,
            "ram_available_mb": available_ram_mb,
            "ram_used_mb": used_ram_mb,
            "ram_percent": vm.percent,
            "low_ram_mode": settings.low_ram_mode
        },
        "storage": disks,
        "models": {
            "candidate_local": settings.local_model_name,
            "model_path": str(settings.local_model_path),
            "model_installed": settings.local_model_path.exists(),
            "cloud_enabled": bool(settings.gemini_api_key or settings.openai_api_key or settings.free_llm_api_endpoint)
        },
        "active_autonomy_level": settings.security_level
    }
