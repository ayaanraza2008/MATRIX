"""Host hardware detection helpers.

These functions report what the machine actually is. Nothing here fabricates a CPU
model, GPU, or disk list: when a value cannot be detected the caller receives
``"unreported"`` so the UI and reports stay truthful.
"""
from __future__ import annotations

import platform
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict

import psutil


@lru_cache(maxsize=1)
def cpu_name() -> str:
    """Return the detected CPU model string, or ``"unreported"``."""
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if str(value).strip():
                    return str(value).strip()
        elif sys.platform.startswith("linux"):
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        elif sys.platform == "darwin":
            out = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if out.stdout.strip():
                return out.stdout.strip()
    except Exception:
        pass

    detected = platform.processor() or platform.machine()
    return detected.strip() or "unreported"


def physical_cores() -> int:
    """Physical CPU core count (falls back to logical count)."""
    return psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True) or 1


def logical_threads() -> int:
    """Logical CPU thread count."""
    return psutil.cpu_count(logical=True) or 1


def _disk_label(mountpoint: str) -> str:
    """Normalise a mountpoint into a stable key (``C:\\`` -> ``C:``)."""
    if sys.platform == "win32" and len(mountpoint) >= 2 and mountpoint[1] == ":":
        return mountpoint[:2]
    return mountpoint or "/"


def storage_snapshot(free_only: bool = True) -> Dict[str, dict]:
    """Report real mounted filesystems with capacity and usage."""
    disks: Dict[str, dict] = {}
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (PermissionError, OSError):
            continue
        disks[_disk_label(partition.mountpoint)] = {
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "used_percent": usage.percent,
            "mountpoint": partition.mountpoint,
            "filesystem": partition.fstype or "unknown",
        }
    if not disks:
        # Last resort: the filesystem that hosts the project itself.
        usage = psutil.disk_usage(Path.cwd().anchor or "/")
        disks[_disk_label(Path.cwd().anchor or "/")] = {
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "used_percent": usage.percent,
            "mountpoint": Path.cwd().anchor or "/",
            "filesystem": "unknown",
        }
    return disks


def gpu_name() -> str:
    """Best-effort GPU description; returns ``"unreported"`` when undetectable."""
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "DriverDesc")
                if str(value).strip():
                    return str(value).strip()
        elif sys.platform.startswith("linux"):
            drm = Path("/sys/class/drm")
            if drm.exists():
                for card in sorted(drm.glob("card*/device/uevent")):
                    for line in card.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.startswith("DRIVER="):
                            return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "unreported"
