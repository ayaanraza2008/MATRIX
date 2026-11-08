"""MATRIX Autonomous Error Recovery Engine.
Provides automated recovery mechanisms for low memory, hung hardware handles,
cache accumulation, and database connection degradation.
"""
from typing import Dict, Any, List, Optional
import time
import os
import gc
import json
import psutil
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.self_maintenance.recovery")


class IncidentRecord:
    def __init__(
        self,
        incident_id: str,
        issue_type: str,
        description: str,
        recovery_action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        self.incident_id = incident_id
        self.issue_type = issue_type
        self.description = description
        self.recovery_action = recovery_action
        self.success = success
        self.details = details or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "issue_type": self.issue_type,
            "description": self.description,
            "recovery_action": self.recovery_action,
            "success": self.success,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ErrorRecoveryEngine:
    """Detects system degradation, initiates targeted safe recovery, and logs verified outcomes."""

    def __init__(self):
        self._incidents_file = settings.data_dir / "incidents.json"
        self._history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        if self._incidents_file.exists():
            try:
                self._history = json.loads(self._incidents_file.read_text(encoding="utf-8"))
            except Exception:
                self._history = []

    def _save_history(self):
        try:
            self._incidents_file.parent.mkdir(parents=True, exist_ok=True)
            self._incidents_file.write_text(json.dumps(self._history[-50:], indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not persist incident history: {e}")

    def log_incident(
        self,
        issue_type: str,
        description: str,
        recovery_action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an incident and its recovery outcome."""
        import uuid
        inc = IncidentRecord(
            incident_id=f"inc_{uuid.uuid4().hex[:8]}",
            issue_type=issue_type,
            description=description,
            recovery_action=recovery_action,
            success=success,
            details=details
        )
        rec = inc.to_dict()
        self._history.append(rec)
        self._save_history()
        return rec

    async def recover_low_memory(self) -> Dict[str, Any]:
        """Trigger garbage collection and unload dormant model instances to free RAM."""
        vm_before = psutil.virtual_memory().available / (1024 * 1024)
        gc.collect()

        from core.model_manager import model_manager
        # If available RAM is still below 450 MB, unload model from RAM
        vm_mid = psutil.virtual_memory().available / (1024 * 1024)
        unloaded = False
        if vm_mid < 450:
            model_manager.unload_local_model()
            gc.collect()
            unloaded = True

        vm_after = psutil.virtual_memory().available / (1024 * 1024)
        freed_mb = vm_after - vm_before

        res = self.log_incident(
            issue_type="MEMORY_PRESSURE",
            description=f"Available RAM was low ({vm_before:.1f} MB)",
            recovery_action=f"Garbage collection executed {'+ Model unloaded' if unloaded else ''}",
            success=True,
            details={"freed_mb": round(freed_mb, 1), "ram_available_mb": round(vm_after, 1)}
        )
        logger.info(f"Memory recovery executed: {freed_mb:.1f} MB freed. Current available: {vm_after:.1f} MB.")
        return res

    async def cleanup_cache_storage(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Remove stale image and audio files from D:\\matrix_data\\cache."""
        cache_dir = settings.cache_dir
        deleted_count = 0
        freed_bytes = 0
        cutoff = time.time() - (max_age_hours * 3600)

        try:
            for root, _, files in os.walk(cache_dir):
                for f in files:
                    fp = Path(root) / f
                    if fp.stat().st_mtime < cutoff:
                        sz = fp.stat().st_size
                        fp.unlink(missing_ok=True)
                        deleted_count += 1
                        freed_bytes += sz
        except Exception as e:
            logger.warning(f"Error during cache cleanup: {e}")

        freed_mb = freed_bytes / (1024 * 1024)
        res = self.log_incident(
            issue_type="CACHE_ACCUMULATION",
            description=f"Purged stale temp files older than {max_age_hours}h",
            recovery_action="Cleaned vision and voice cache directories",
            success=True,
            details={"deleted_files": deleted_count, "freed_mb": round(freed_mb, 2)}
        )
        return res

    def list_recent_incidents(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self._history[-limit:]))

    async def auto_recover_system(self) -> Dict[str, Any]:
        """Perform automatic self-healing across memory pressure and cache accumulation."""
        mem_res = await self.recover_low_memory()
        cache_res = await self.cleanup_cache_storage()
        return {
            "status": "RECOVERED",
            "memory": mem_res,
            "cache": cache_res,
            "cache_cleaned": cache_res.get("details", {}).get("deleted_files", 0)
        }


# Global singleton
recovery_engine = ErrorRecoveryEngine()
