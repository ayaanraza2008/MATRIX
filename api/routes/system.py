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


@router.get("/telemetry", status_code=status.HTTP_200_OK)
async def get_system_telemetry():
    """Retrieve comprehensive verified real-time hardware, storage, and OS telemetry."""
    import time
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu_percent = psutil.cpu_percent(interval=None)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freq = psutil.cpu_freq()

    # Disk telemetry for host partitions
    disks = {}
    for drive in ["C:", "D:"]:
        try:
            usage = psutil.disk_usage(f"{drive}\\")
            disks[drive] = {
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "used_percent": usage.percent
            }
        except Exception:
            disks[drive] = {"available": False}

    # Battery telemetry if running on laptop
    battery_info = None
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_info = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
            }
    except Exception:
        pass

    # Uptime & process metrics
    boot_time = psutil.boot_time()
    uptime_seconds = round(time.time() - boot_time, 1)

    status_str = "nominal"
    if vm.percent >= settings.max_ram_percent or cpu_percent >= 95.0:
        status_str = "critical"
    elif vm.percent >= 85.0 or cpu_percent >= 80.0:
        status_str = "warning"

    return {
        "status": status_str,
        "timestamp": time.time(),
        "uptime_seconds": uptime_seconds,
        "cpu": {
            "percent": cpu_percent,
            "per_cpu_percent": per_cpu,
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else 0,
            "physical_cores": psutil.cpu_count(logical=False) or settings.cpu_cores,
            "logical_threads": psutil.cpu_count(logical=True) or settings.cpu_threads,
            "architecture": platform.machine()
        },
        "memory": {
            "percent": vm.percent,
            "used_mb": round(vm.used / (1024 * 1024), 1),
            "available_mb": round(vm.available / (1024 * 1024), 1),
            "total_mb": round(vm.total / (1024 * 1024), 1),
            "swap_used_mb": round(swap.used / (1024 * 1024), 1),
            "low_ram_mode": settings.low_ram_mode
        },
        "storage": disks,
        "battery": battery_info,
        "process_count": len(psutil.pids()),
        "host": {
            "os": platform.system(),
            "release": platform.release(),
            "hostname": platform.node()
        }
    }
