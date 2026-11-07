"""MATRIX System Metrics & Telemetry API Route.
"""
from fastapi import APIRouter, status
import platform
import psutil
from config.settings import settings

router = APIRouter(prefix="/system", tags=["System Telemetry"])


@router.get("/info", status_code=status.HTTP_200_OK)
async def get_system_info():
    """Retrieve verified machine specifications and environment properties."""
    vm = psutil.virtual_memory()
    return {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor()
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation()
        },
        "hardware": {
            "cpu_name": "AMD Ryzen 7 5700U with Radeon Graphics",
            "physical_cores": settings.cpu_cores,
            "logical_processors": settings.cpu_threads,
            "avx2_supported": settings.avx2_enabled,
            "gpu_name": "AMD Radeon(TM) Graphics (Integrated APU)",
            "total_ram_bytes": vm.total,
            "total_ram_gb": round(vm.total / (1024 ** 3), 2)
        },
        "storage_layout": {
            "data_root": str(settings.data_dir),
            "models_root": str(settings.models_dir),
            "cache_root": str(settings.cache_dir),
            "logs_root": str(settings.logs_dir)
        }
    }


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_live_metrics():
    """Retrieve real-time utilization metrics for the MATRIX HUD / Dashboard."""
    vm = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq()

    return {
        "cpu": {
            "percent": cpu_percent,
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else 0
        },
        "memory": {
            "percent": vm.percent,
            "used_mb": round(vm.used / (1024 * 1024), 1),
            "available_mb": round(vm.available / (1024 * 1024), 1),
            "total_mb": round(vm.total / (1024 * 1024), 1)
        },
        "status": "nominal" if vm.percent < 85 else "warning"
    }
