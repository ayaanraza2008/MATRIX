"""MATRIX Resource Guard.
Monitors host memory, CPU, and disk headroom on AMD Ryzen 7 5700U / 8GB RAM.
Prevents system exhaustion before activating new adapters or models.
"""
import psutil
import shutil
import gc
from typing import Dict, Any, Tuple
from config.logging_config import get_logger

logger = get_logger("core.repo_intel.resource_guard")


class ResourceGuard:
    """Enforces hardware budgets and safety margins for autonomous tool execution."""

    def __init__(self, min_ram_free_mb: int = 80, max_ram_percent: float = 98.0):
        self.min_ram_free_mb = min_ram_free_mb
        self.max_ram_percent = max_ram_percent

    def check_headroom(self, required_ram_mb: int = 250) -> Tuple[bool, str, Dict[str, Any]]:
        """Verify if host has enough RAM and disk capacity to run a proposed tool."""
        mem = psutil.virtual_memory()
        ram_avail_mb = mem.available / (1024 * 1024)
        ram_percent = mem.percent

        cpu_percent = psutil.cpu_percent(interval=None)

        # Check disk space on D: drive where matrix_data resides
        disk_usage = shutil.disk_usage("D:\\") if shutil.os.path.exists("D:\\") else shutil.disk_usage("C:\\")
        disk_free_gb = disk_usage.free / (1024 * 1024 * 1024)

        metrics = {
            "ram_available_mb": round(ram_avail_mb, 1),
            "ram_percent": ram_percent,
            "cpu_percent": cpu_percent,
            "disk_free_gb": round(disk_free_gb, 2),
            "required_ram_mb": required_ram_mb
        }

        # Safety Check 1: Critically low RAM
        if ram_avail_mb < (self.min_ram_free_mb + required_ram_mb) or ram_percent >= self.max_ram_percent:
            # Trigger garbage collection attempt
            gc.collect()
            mem_after = psutil.virtual_memory()
            if mem_after.available / (1024 * 1024) < (self.min_ram_free_mb + required_ram_mb):
                msg = (
                    f"Resource Guard Block: Host RAM ({ram_avail_mb:.1f} MB available, {ram_percent}% used) "
                    f"insufficient for tool requiring {required_ram_mb} MB. Minimum safe threshold is {self.min_ram_free_mb} MB."
                )
                logger.warning(msg)
                return False, msg, metrics

        # Safety Check 2: Disk space exhaustion (<2 GB free)
        if disk_free_gb < 2.0:
            msg = f"Resource Guard Block: Low disk space ({disk_free_gb:.1f} GB free). Minimum 2.0 GB required."
            logger.warning(msg)
            return False, msg, metrics

        return True, "Resource headroom verified. Safe to proceed.", metrics

    def optimize_memory(self) -> Dict[str, Any]:
        """Free unreferenced memory and force garbage collection."""
        before = psutil.virtual_memory().available / (1024 * 1024)
        collected = gc.collect()
        after = psutil.virtual_memory().available / (1024 * 1024)
        freed = max(0.0, after - before)
        logger.info(f"Memory optimization collected {collected} objects, freed {freed:.1f} MB.")
        return {
            "objects_collected": collected,
            "freed_mb": round(freed, 1),
            "current_available_mb": round(after, 1)
        }


resource_guard = ResourceGuard()
