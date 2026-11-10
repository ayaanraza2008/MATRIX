"""MATRIX 4-Tier Autonomy Policy & Security Permissions Manager.
Implements:
  LEVEL 1 — OBSERVE: Read-only observation, telemetry polling, status queries, suggestions.
  LEVEL 2 — ASSIST: Reversible, low-risk tasks (launching approved apps, volume, draft emails, screenshot).
  LEVEL 3 — AUTONOMOUS: Independent routine execution, scheduled background tasks, safe self-recovery, file organization.
  LEVEL 4 — SUPERVISED HIGH-IMPACT ACTIONS: Strict confirmation gate for external messaging, financial operations,
            elevated software installation, destructive deletion, privacy exports, and telephony outside configured rules.
"""
from enum import IntEnum
from typing import Dict, Any, List, Optional, Set
import time
import uuid
from pydantic import BaseModel, Field
from config.logging_config import get_logger

logger = get_logger("security.permissions")


class AutonomyLevel(IntEnum):
    LEVEL_1_OBSERVE = 1
    LEVEL_2_ASSIST = 2
    LEVEL_3_AUTONOMOUS = 3
    LEVEL_4_SUPERVISED = 4


class PermissionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"perm_{uuid.uuid4().hex[:8]}")
    action: str
    target: str
    required_level: AutonomyLevel
    risk_score: int  # 1 to 10
    reason: str
    status: str = "PENDING"  # PENDING, GRANTED, REJECTED, EXPIRED
    created_at: float = Field(default_factory=time.time)
    expires_at: float = Field(default_factory=lambda: time.time() + 300)  # 5 min TTL
    confirmed_by: Optional[str] = None


class AutonomySecurityManager:
    """Central policy engine evaluating authorization, confirmation gates, and capabilities."""

    def __init__(self, current_level: AutonomyLevel = AutonomyLevel.LEVEL_3_AUTONOMOUS):
        self.current_level = current_level
        self._pending_approvals: Dict[str, PermissionRequest] = {}
        self._preauthorized_scopes: Set[str] = {
            "os.read_telemetry",
            "os.launch_approved_app",
            "os.adjust_volume",
            "os.take_screenshot",
            "web.read_url",
            "weather.read_forecast",
            "files.create_safe_folder",
            "files.organize_downloads",
            "voice.synthesize_speech",
            "vision.airtouch_stream",
            "background.run_scheduled_health"
        }

    def set_global_autonomy_level(self, level: int) -> AutonomyLevel:
        """Update system-wide active autonomy policy."""
        try:
            self.current_level = AutonomyLevel(level)
            logger.info(f"System Autonomy Level set to: {self.current_level.name}")
            return self.current_level
        except ValueError:
            logger.warning(f"Invalid autonomy level {level}; retaining {self.current_level.name}")
            return self.current_level

    def evaluate_action(
        self,
        action: str,
        target: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate if an action can execute under the current autonomy level or needs Level 4 gate."""
        action_clean = action.lower().strip()
        details = details or {}

        # 1. Level 4 Critical Supervised Actions (MANDATORY APPROVAL GATE)
        level_4_triggers = [
            "delete_important_file", "format_drive", "drop_table", "rmdir_all",
            "send_external_email", "publish_external_message", "financial_transaction",
            "purchase", "install_elevated_software", "change_security_settings",
            "revoke_all_permissions", "outbound_call_unverified", "export_private_keys"
        ]
        is_level_4 = any(trig in action_clean for trig in level_4_triggers) or \
                     details.get("requires_confirmation", False) or \
                     details.get("risk_level", 1) >= 4

        if is_level_4:
            req = PermissionRequest(
                action=action,
                target=target,
                required_level=AutonomyLevel.LEVEL_4_SUPERVISED,
                risk_score=9,
                reason=f"Action '{action}' requires explicit confirmation under Level 4 Supervised Policy."
            )
            self._pending_approvals[req.request_id] = req
            return {
                "authorized": False,
                "requires_confirmation": True,
                "autonomy_level": AutonomyLevel.LEVEL_4_SUPERVISED.value,
                "request_id": req.request_id,
                "reason": req.reason
            }

        # 2. Level 3 Autonomous Tasks
        level_3_triggers = [
            "schedule_background_task", "organize_folder", "clean_cache",
            "auto_recover_service", "download_gguf_model", "sync_integration"
        ]
        is_level_3 = any(trig in action_clean for trig in level_3_triggers)

        if is_level_3:
            can_run = self.current_level >= AutonomyLevel.LEVEL_3_AUTONOMOUS
            return {
                "authorized": can_run,
                "requires_confirmation": not can_run,
                "autonomy_level": AutonomyLevel.LEVEL_3_AUTONOMOUS.value,
                "reason": "Permitted autonomously under Level 3+" if can_run else "Requires Level 3 Autonomy"
            }

        # 3. Level 2 Assist Tasks (Reversible OS Actions)
        level_2_triggers = [
            "launch_application", "close_application", "set_volume", "open_url",
            "capture_screenshot", "create_folder", "draft_message", "search_web"
        ]
        is_level_2 = any(trig in action_clean for trig in level_2_triggers)

        if is_level_2:
            can_run = self.current_level >= AutonomyLevel.LEVEL_2_ASSIST
            return {
                "authorized": can_run,
                "requires_confirmation": not can_run,
                "autonomy_level": AutonomyLevel.LEVEL_2_ASSIST.value,
                "reason": "Permitted under Level 2 Assist" if can_run else "Requires Level 2 Autonomy"
            }

        # 4. Level 1 Observe (Read-only, telemetry, time, status)
        return {
            "authorized": True,
            "requires_confirmation": False,
            "autonomy_level": AutonomyLevel.LEVEL_1_OBSERVE.value,
            "reason": "Permitted as safe read-only observation"
        }

    def confirm_request(self, request_id: str, confirmed_by: str = "user") -> bool:
        """Grant approval to a pending Level 4 request."""
        req = self._pending_approvals.get(request_id)
        if not req or req.status != "PENDING" or time.time() > req.expires_at:
            return False
        req.status = "GRANTED"
        req.confirmed_by = confirmed_by
        logger.info(f"Permission request {request_id} for '{req.action}' GRANTED by {confirmed_by}.")
        return True

    def reject_request(self, request_id: str, reason: str = "User denied") -> bool:
        """Deny approval for a pending Level 4 request."""
        req = self._pending_approvals.get(request_id)
        if not req:
            return False
        req.status = "REJECTED"
        req.reason = reason
        logger.warning(f"Permission request {request_id} for '{req.action}' REJECTED.")
        return True

    def list_pending_requests(self) -> List[Dict[str, Any]]:
        """List active pending approval requests."""
        now = time.time()
        active = []
        for rid, req in list(self._pending_approvals.items()):
            if req.status == "PENDING" and now <= req.expires_at:
                active.append(req.model_dump())
            elif req.status == "PENDING" and now > req.expires_at:
                req.status = "EXPIRED"
        return active

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Summary of active autonomy level, permission gates, and pending actions."""
        return {
            "active_level": self.current_level.value,
            "level_name": self.current_level.name,
            "level_description": {
                1: "LEVEL 1 — OBSERVE: Read-only, status, telemetry, suggestions",
                2: "LEVEL 2 — ASSIST: Reversible low-risk actions (apps, audio, folders)",
                3: "LEVEL 3 — AUTONOMOUS: Independent background tasks & self-recovery",
                4: "LEVEL 4 — SUPERVISED: High-impact actions require explicit confirmation"
            }.get(self.current_level.value, ""),
            "pending_count": len(self.list_pending_requests()),
            "preauthorized_scopes_count": len(self._preauthorized_scopes)
        }


# Global singleton instance
security_manager = AutonomySecurityManager()
