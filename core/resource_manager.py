"""MATRIX Autonomous Resource & Service Lifecycle Manager.
Coordinates dynamic service startup, idle process shutdown, memory headroom preservation,
dependency isolation, and CPU/GPU resource monitoring.
"""
from typing import Dict, Any, List, Optional
import time
import subprocess
import asyncio
import psutil
from pydantic import BaseModel
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.resource_manager")


class ServiceProcessRecord(BaseModel):
    service_id: str
    name: str
    pid: Optional[int] = None
    started_at: float
    last_active_at: float
    command: str
    status: str = "RUNNING"  # RUNNING, IDLE, STOPPED, FAILED
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    idle_timeout_seconds: float = 300.0  # 5 minutes default
    is_persistent: bool = False


class AutonomousResourceManager:
    """Manages adapter background services, memory headroom, and automatic idle process reaping."""

    def __init__(self, memory_emergency_threshold_mb: float = 500.0):
        self._services: Dict[str, ServiceProcessRecord] = {}
        self._process_handles: Dict[str, subprocess.Popen] = {}
        self.emergency_threshold_mb = memory_emergency_threshold_mb
        self._reaper_task: Optional[asyncio.Task] = None

    def start_service(
        self,
        service_id: str,
        command: List[str] | str,
        name: Optional[str] = None,
        idle_timeout_seconds: float = 300.0,
        is_persistent: bool = False,
        **kwargs
    ) -> ServiceProcessRecord:
        """Start a managed service on-demand with automatic tracking."""
        name = name or service_id
        if service_id in self._services and self.is_service_running(service_id):
            logger.info(f"Service '{service_id}' already running. Updating activity timestamp.")
            rec = self._services[service_id]
            rec.last_active_at = time.time()
            rec.status = "RUNNING"
            return rec

        # Check memory headroom before spawning new process
        vm = psutil.virtual_memory()
        avail_mb = vm.available / (1024 * 1024)
        if avail_mb < self.emergency_threshold_mb:
            logger.warning(f"Low system memory ({avail_mb:.1f} MB available). Attempting idle cleanup before launch.")
            self.reap_idle_services(force_all_idle=True)

        try:
            cmd_str = " ".join(command) if isinstance(command, list) else command
            proc = subprocess.Popen(
                command,
                shell=isinstance(command, str),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self._process_handles[service_id] = proc
            now = time.time()
            record = ServiceProcessRecord(
                service_id=service_id,
                name=name,
                pid=proc.pid,
                started_at=now,
                last_active_at=now,
                command=cmd_str,
                status="RUNNING",
                idle_timeout_seconds=idle_timeout_seconds,
                is_persistent=is_persistent
            )
            self._services[service_id] = record
            logger.info(f"Started autonomous service '{name}' (PID: {proc.pid})")
            return record
        except Exception as e:
            logger.error(f"Failed to start service '{service_id}': {e}")
            now = time.time()
            record = ServiceProcessRecord(
                service_id=service_id,
                name=name,
                pid=None,
                started_at=now,
                last_active_at=now,
                command=str(command),
                status="FAILED",
                idle_timeout_seconds=idle_timeout_seconds
            )
            self._services[service_id] = record
            return record

    def touch_service(self, service_id: str):
        """Update last active timestamp to prevent premature idle reaping."""
        if service_id in self._services:
            self._services[service_id].last_active_at = time.time()
            self._services[service_id].status = "RUNNING"

    def stop_service(self, service_id: str) -> bool:
        """Gracefully terminate a running service."""
        proc = self._process_handles.get(service_id)
        if proc:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                logger.info(f"Terminated service '{service_id}' successfully.")
            except Exception as e:
                logger.warning(f"Error terminating service '{service_id}': {e}")

        if service_id in self._services:
            self._services[service_id].status = "STOPPED"
            self._services[service_id].pid = None
        self._process_handles.pop(service_id, None)
        return True

    def is_service_running(self, service_id: str) -> bool:
        proc = self._process_handles.get(service_id)
        if proc and proc.poll() is None:
            return True
        return False

    def reap_idle_services(self, force_all_idle: bool = False) -> int:
        """Scan running services and stop those exceeding their idle timeout."""
        reaped_count = 0
        now = time.time()

        for s_id, rec in list(self._services.items()):
            if rec.is_persistent or rec.status != "RUNNING":
                continue

            idle_time = now - rec.last_active_at
            if force_all_idle or idle_time > rec.idle_timeout_seconds:
                logger.info(f"Reaping idle service '{s_id}' (Idle for {idle_time:.1f}s > {rec.idle_timeout_seconds}s limit)")
                self.stop_service(s_id)
                reaped_count += 1

        return reaped_count

    def update_telemetry(self):
        """Update CPU and memory utilization metrics for active services."""
        for s_id, rec in self._services.items():
            if rec.pid and self.is_service_running(s_id):
                try:
                    p = psutil.Process(rec.pid)
                    rec.memory_mb = round(p.memory_info().rss / (1024 * 1024), 2)
                    rec.cpu_percent = round(p.cpu_percent(interval=None), 1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    rec.status = "STOPPED"
                    rec.pid = None

    def get_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive resource and service lifecycle status report."""
        self.update_telemetry()
        vm = psutil.virtual_memory()
        return {
            "timestamp": time.time(),
            "host_memory": {
                "total_mb": round(vm.total / (1024 * 1024), 1),
                "available_mb": round(vm.available / (1024 * 1024), 1),
                "used_percent": vm.percent,
                "low_ram_mode": settings.low_ram_mode
            },
            "active_services_count": len([s for s in self._services.values() if s.status == "RUNNING"]),
            "managed_services": {s_id: s.model_dump() for s_id, s in self._services.items()}
        }

    def cleanup_all(self):
        """Stop all managed services on shutdown."""
        logger.info("Cleaning up all managed adapter services...")
        for s_id in list(self._process_handles.keys()):
            self.stop_service(s_id)


# Global singleton
resource_manager = AutonomousResourceManager()
