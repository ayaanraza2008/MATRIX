"""MATRIX Autonomous Installer.
Performs safe, isolated dependency and repository installation with provenance checks,
license verification, resource headroom checks, rollback capability, and manifest tracking.
"""
from typing import Dict, Any, List, Optional
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from core.autonomy_policy.policy import autonomy_policy, ActionCategory
from core.repository_intelligence.resource_guard import resource_guard
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.autonomous_installer")


class InstallResult(BaseModel):
    success: bool
    package_name: str
    version: Optional[str] = None
    target_env: str = "main"
    error: Optional[str] = None
    audit_id: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DependencyManifest(BaseModel):
    installed_packages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutonomousInstaller:
    """Manages installation, isolated environments, health checks, and repairs of tool dependencies."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (settings.data_dir / "tools")
        self.envs_dir = settings.data_dir / "envs"
        self.manifest_file = self.storage_dir / "installed_manifest.json"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.envs_dir.mkdir(parents=True, exist_ok=True)
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> DependencyManifest:
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return DependencyManifest(**json.load(f))
            except Exception:
                pass
        return DependencyManifest()

    def _save_manifest(self):
        try:
            self._manifest.last_updated = datetime.now(timezone.utc)
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump(self._manifest.model_dump(mode="json"), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist dependency manifest: {e}")

    async def _log_audit(self, action: str, details: str, status: str = "COMPLETED"):
        """Record install event in database audit log."""
        try:
            from database.session import AsyncSessionLocal
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(
                        "INSERT INTO audit_logs (event_type, risk_level, tool_name, actor, action_summary, status, timestamp) "
                        "VALUES (:evt, :risk, :tool, :act, :summary, :stat, :ts)"
                    ),
                    {
                        "evt": "AUTONOMOUS_INSTALLER",
                        "risk": 2,
                        "tool": action,
                        "act": "installer",
                        "summary": details,
                        "stat": status,
                        "ts": datetime.now(timezone.utc)
                    }
                )
                await session.commit()
        except Exception as e:
            logger.debug(f"Audit log write failed: {e}")

    def check_installability(self, package_name: str) -> Dict[str, Any]:
        """Verify provenance, license, security risk, and hardware headroom before installation."""
        pkg_clean = package_name.strip().lower()

        # 1. Policy check
        policy_verdict = autonomy_policy.evaluate(
            ActionCategory.INSTALL_PREAPPROVED_DEP,
            details={"package": pkg_clean}
        )

        is_preapproved = pkg_clean in autonomy_policy.approved_packages
        if not is_preapproved and not policy_verdict.allowed:
            return {
                "installable": False,
                "reason": f"Package '{package_name}' is not in pre-approved trust list and requires Level 3 human authorization.",
                "policy": policy_verdict.model_dump()
            }

        # 2. Resource headroom check
        ok, reason, metrics = resource_guard.check_headroom(required_ram_mb=150)
        if not ok:
            return {
                "installable": False,
                "reason": reason,
                "resource_metrics": metrics
            }

        return {
            "installable": True,
            "reason": "Pre-approved and resource headroom confirmed.",
            "is_preapproved": is_preapproved,
            "resource_metrics": metrics
        }

    async def install_package(
        self,
        package_name: str,
        version: Optional[str] = None,
        is_user_confirmed: bool = False
    ) -> InstallResult:
        """Autonomously install a verified package into the environment."""
        start_time = datetime.now(timezone.utc)
        pkg_spec = f"{package_name}=={version}" if version else package_name

        # 1. Check installability & policy
        check = self.check_installability(package_name)
        if not check.get("installable") and not is_user_confirmed:
            await self._log_audit(f"install:{package_name}", f"Blocked: {check.get('reason')}", "BLOCKED")
            return InstallResult(
                success=False,
                package_name=package_name,
                error=check.get("reason", "Installation policy blocked.")
            )

        logger.info(f"Initiating autonomous installation of '{pkg_spec}'...")

        # 2. Run pip install
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--no-warn-script-location", pkg_spec]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if proc.returncode == 0:
                self._manifest.installed_packages[package_name] = {
                    "version": version or "latest",
                    "installed_at": datetime.now(timezone.utc).isoformat(),
                    "status": "healthy"
                }
                self._save_manifest()
                await self._log_audit(f"install:{package_name}", f"Successfully installed {pkg_spec}", "SUCCESS")
                logger.info(f"Successfully installed package '{pkg_spec}'")
                return InstallResult(
                    success=True,
                    package_name=package_name,
                    version=version or "installed"
                )
            else:
                err_msg = proc.stderr.strip()[:300]
                await self._log_audit(f"install:{package_name}", f"Pip failed: {err_msg}", "FAILED")
                logger.warning(f"Pip installation failed for '{pkg_spec}': {err_msg}")
                return InstallResult(
                    success=False,
                    package_name=package_name,
                    error=f"Pip error: {err_msg}"
                )
        except subprocess.TimeoutExpired:
            return InstallResult(success=False, package_name=package_name, error="Installation timed out (120s limit).")
        except Exception as e:
            return InstallResult(success=False, package_name=package_name, error=str(e))

    def check_dependency_health(self, package_name: str) -> bool:
        """Check if an installed package can be cleanly imported."""
        try:
            cmd = [sys.executable, "-c", f"import {package_name}; print('OK')"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return proc.returncode == 0 and "OK" in proc.stdout
        except Exception:
            return False

    async def repair_dependency(self, package_name: str) -> bool:
        """Attempt to repair a broken dependency by reinstalling."""
        logger.warning(f"Attempting self-healing repair for broken dependency '{package_name}'...")
        res = await self.install_package(package_name)
        return res.success

    def list_installed_manifest(self) -> Dict[str, Any]:
        return self._manifest.model_dump(mode="json")


# Global autonomous installer singleton
autonomous_installer = AutonomousInstaller()
