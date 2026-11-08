"""MATRIX Self-Diagnostics Engine.
Performs periodic and on-demand health inspections of dependencies, memory,
disk space, database latency, and service connectivity.
"""
from typing import Dict, Any, List
import time
import os
import psutil
import shutil
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.self_maintenance.diagnostics")


class DiagnosticCheckResult:
    def __init__(self, name: str, passed: bool, details: str, latency_ms: float = 0.0):
        self.name = name
        self.passed = passed
        self.details = details
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "status": "HEALTHY" if self.passed else "DEGRADED",
            "details": self.details,
            "latency_ms": round(self.latency_ms, 2)
        }


class SelfDiagnosticsEngine:
    """Evaluates runtime integrity across system, memory, dependencies, and storage."""

    def __init__(self):
        self._last_report: Dict[str, Any] = {}
        self._last_run_time: float = 0.0

    async def run_full_diagnostics(self) -> Dict[str, Any]:
        """Execute complete suite of operational health checks."""
        t0 = time.perf_counter()
        checks: List[Dict[str, Any]] = []

        # 1. Memory Health Check
        vm = psutil.virtual_memory()
        avail_mb = vm.available / (1024 * 1024)
        mem_ok = avail_mb > 500
        checks.append(DiagnosticCheckResult(
            "Memory Threshold",
            mem_ok,
            f"Available RAM: {avail_mb:.1f} MB ({vm.percent}% used). Threshold: >500 MB."
        ).to_dict())

        # 2. Database Integrity Check
        db_path = settings.data_dir / "matrix.db"
        t_db = time.perf_counter()
        db_ok = False
        db_detail = ""
        try:
            from database.session import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                res = await session.execute(text("SELECT 1"))
                row = res.scalar()
                db_ok = (row == 1)
                db_lat = (time.perf_counter() - t_db) * 1000
                db_detail = f"SQLite operational at {db_path.name} (Latency: {db_lat:.1f}ms)"
        except Exception as e:
            db_detail = f"Database query failed: {e}"
            db_lat = (time.perf_counter() - t_db) * 1000

        checks.append(DiagnosticCheckResult("SQLite Database", db_ok, db_detail, db_lat).to_dict())

        # 3. Storage Partitions Health Check
        c_free = shutil.disk_usage("C:").free / (1024**3)
        d_free = shutil.disk_usage("D:").free / (1024**3) if Path("D:").exists() else 0
        disk_ok = c_free > 5.0 and d_free > 10.0
        checks.append(DiagnosticCheckResult(
            "Disk Partitions",
            disk_ok,
            f"Drive C: {c_free:.1f} GB free, Drive D: {d_free:.1f} GB free (Threshold: C>5GB, D>10GB)"
        ).to_dict())

        # 4. Critical Python Dependencies Check
        missing_deps = []
        for mod in ["psutil", "sounddevice", "cv2", "pycaw", "onnxruntime", "fastapi"]:
            try:
                __import__(mod)
            except ImportError:
                missing_deps.append(mod)

        checks.append(DiagnosticCheckResult(
            "Runtime Dependencies",
            len(missing_deps) == 0,
            "All core Python libraries installed." if not missing_deps else f"Missing: {missing_deps}"
        ).to_dict())

        # 5. Local AI Model Weights Check
        from core.model_manager import model_manager
        model_avail = model_manager.is_local_model_available()
        model_p = model_manager.find_local_gguf_model()
        checks.append(DiagnosticCheckResult(
            "Local Model Storage",
            model_avail,
            f"GGUF model present: {model_p.name if model_p else 'None'}"
        ).to_dict())

        total_lat = (time.perf_counter() - t0) * 1000
        all_passed = all(c["passed"] for c in checks)

        report = {
            "overall_status": "HEALTHY" if all_passed else "ATTENTION_REQUIRED",
            "passed_checks": sum(1 for c in checks if c["passed"]),
            "total_checks": len(checks),
            "execution_time_ms": round(total_lat, 2),
            "timestamp": time.time(),
            "checks": checks
        }

        self._last_report = report
        self._last_run_time = time.time()
        return report

    def get_latest_report(self) -> Dict[str, Any]:
        return self._last_report or {
            "overall_status": "PENDING",
            "message": "Diagnostics not yet executed in this session."
        }


# Global singleton
diagnostics_engine = SelfDiagnosticsEngine()
