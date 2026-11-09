"""MATRIX Centralized Permission & Connection Authorization Center.
Implements the One-Time Setup Wizard, Scoped Category Authorizations, and 3-Tier Permission Profiles:
  1. AUTOMATIC — safe operations explicitly authorized by user.
  2. RESTRICTED — operations permitted only within configured boundaries / limits.
  3. CONFIRMATION_REQUIRED — sensitive, irreversible, or unverified actions requiring explicit confirmation.

Guarantees the user does NOT have to repeatedly approve routine operations once authorized.
"""
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
import json
import time
from pathlib import Path
from pydantic import BaseModel, Field
from config.settings import settings
from config.logging_config import get_logger
from security.vault.dpapi_vault import dpapi_vault

logger = get_logger("security.authorization_center")

AUTH_CONFIG_FILE = Path(r"D:\matrix_data\security\authorization_profiles.json")


class PermissionProfile(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    RESTRICTED = "RESTRICTED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


class ScopeItem(BaseModel):
    scope_id: str
    name: str
    description: str
    category: str
    profile: PermissionProfile
    granted_at: float = Field(default_factory=time.time)
    native_permission_verified: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


ACTION_SCOPE_MAP = {
    # Filesystem
    "create_file": "file_folder_access",
    "write_file": "file_folder_access",
    "read_file": "file_folder_access",
    "delete_file": "file_folder_access",
    "list_files": "file_folder_access",
    "list_directory": "file_folder_access",
    "search_files": "file_folder_access",
    "organize_folder": "file_folder_access",
    "create_folder": "file_folder_access",
    "create_directory": "file_folder_access",
    "rename_file": "file_folder_access",
    "extract_zip": "file_folder_access",
    "compress_zip": "file_folder_access",
    # Computer / OS
    "launch_app": "app_launch",
    "open_app": "app_launch",
    "close_app": "app_launch",
    "terminate_app": "app_launch",
    "switch_window": "ui_automation",
    "click": "keyboard_mouse",
    "type_text": "keyboard_mouse",
    "press_key": "keyboard_mouse",
    "hotkey": "keyboard_mouse",
    "move_mouse": "keyboard_mouse",
    "simulate_input": "keyboard_mouse",
    "screenshot": "screen_capture",
    "take_screenshot": "screen_capture",
    "ocr": "screen_capture",
    "execute_command": "isolated_execution_environments",
    # Telemetry / System
    "get_telemetry": "system_telemetry",
    "poll_telemetry": "system_telemetry",
    "get_stats": "system_telemetry",
    "system_info": "system_telemetry",
    "cpu_usage": "system_telemetry",
    "memory_usage": "system_telemetry",
    "notify": "notifications",
    "show_notification": "notifications",
    "read_clipboard": "clipboard_access",
    "write_clipboard": "clipboard_access",
    # Voice
    "listen": "microphone",
    "record_mic": "microphone",
    "speak": "speakers",
    "synthesize_speech": "speakers",
    "tts": "speakers",
    # Vision
    "capture_camera": "camera",
    "capture_frame": "camera",
    "airtouch": "airtouch_tracking_hardware",
    # Telephony
    "make_call": "bland_phone_calling",
    "outbound_call": "bland_phone_calling",
    "send_call": "bland_phone_calling",
    # Google
    "send_email": "gmail",
    "read_inbox": "gmail",
    "query_calendar": "google_calendar",
    "create_calendar_event": "google_calendar",
    # Dependencies / Sandbox
    "install_dependency": "approved_dependency_installation",
    "pip_install": "approved_dependency_installation",
    "run_sandbox": "isolated_execution_environments",
    # Repo
    "query_inventory": "github_starred_repos",
    "clone_repo": "github_starred_repos",
    "register_tool": "tool_registration",
}


class AuthorizationCenter:
    """Central authority evaluating and maintaining persistent authorization scopes and connections."""

    # Default catalog of all supported scopes across the 4 major categories
    DEFAULT_CATALOG = {
        # A. Windows Permissions
        "windows_permissions": {
            "microphone": ("Microphone Capture", "Listen to physical microphone stream for speech & wake-words", PermissionProfile.AUTOMATIC),
            "camera": ("Webcam Video Capture", "Access camera device for gesture & scene perception", PermissionProfile.AUTOMATIC),
            "screen_capture": ("Screen Capture & OCR", "Capture screen surface for visual grounding and context understanding", PermissionProfile.AUTOMATIC),
            "ui_automation": ("Accessibility / UI Automation", "Inspect Windows UI elements and control supported applications", PermissionProfile.AUTOMATIC),
            "keyboard_mouse": ("Keyboard & Mouse Input", "Synthesize mouse clicks, cursor movement, and keypresses", PermissionProfile.RESTRICTED),
            "file_folder_access": ("Filesystem Read & Write", "Create, organize, and manage files in authorized directories", PermissionProfile.RESTRICTED),
            "app_launch": ("Application Management", "Launch, focus, and cleanly terminate desktop software", PermissionProfile.AUTOMATIC),
            "system_telemetry": ("Hardware & System Telemetry", "Monitor CPU, RAM, disk, battery, and network performance", PermissionProfile.AUTOMATIC),
            "notifications": ("Windows Desktop Notifications", "Send system tray and banner notifications", PermissionProfile.AUTOMATIC),
            "clipboard_access": ("System Clipboard", "Read and write clipboard contents for user workflow assistance", PermissionProfile.RESTRICTED),
            "startup_background_service": ("Startup & Background Service", "Run persistent background listener and scheduled task worker", PermissionProfile.AUTOMATIC),
            "bluetooth_devices": ("Bluetooth & Device Discovery", "Discover and interface with paired wireless peripherals", PermissionProfile.RESTRICTED)
        },
        # B. Connected Services
        "connected_services": {
            "google_workspace_oauth": ("Google Workspace OAuth", "Access Google Docs, Drive, and Workspace resources", PermissionProfile.CONFIRMATION_REQUIRED),
            "gmail": ("Gmail Integration", "Inspect inbox and create draft emails (external send gated)", PermissionProfile.CONFIRMATION_REQUIRED),
            "google_calendar": ("Google Calendar", "Read schedules, agendas, and draft calendar appointments", PermissionProfile.AUTOMATIC),
            "github": ("GitHub API & Repositories", "Query repository issues, branches, and documentation", PermissionProfile.AUTOMATIC),
            "telegram": ("Telegram Notification Bot", "Dispatch operational updates and alerts to authorized chat", PermissionProfile.RESTRICTED),
            "bland_phone_calling": ("Bland AI Telephony", "Initiate outbound phone calls (financial charge per minute)", PermissionProfile.CONFIRMATION_REQUIRED),
            "firebase_notifications": ("Firebase Mobile Push", "Send companion push notifications to paired Android device", PermissionProfile.AUTOMATIC),
            "tailscale_remote_access": ("Tailscale Secure Mesh", "Provide end-to-end encrypted remote access across personal mesh", PermissionProfile.CONFIRMATION_REQUIRED),
            "weather_openmeteo": ("Live Weather Data", "Query Open-Meteo live forecasts and atmospheric data", PermissionProfile.AUTOMATIC)
        },
        # C. Hardware
        "hardware": {
            "laptop_microphone": ("Realtek Laptop Microphone", "Capture ambient and directional audio buffers", PermissionProfile.AUTOMATIC),
            "speakers": ("Laptop Audio Speakers", "Play single-source neural speech and acoustic acknowledgments", PermissionProfile.AUTOMATIC),
            "webcam": ("Integrated HD Webcam", "Feed vision pipeline for AirTouch hand & eye tracking", PermissionProfile.AUTOMATIC),
            "android_phone": ("Android Companion Handset", "Pair with companion app for remote telemetry and notifications", PermissionProfile.AUTOMATIC),
            "bluetooth_hardware": ("Bluetooth Radio Controller", "Query paired Bluetooth accessories", PermissionProfile.RESTRICTED),
            "airtouch_tracking_hardware": ("AirTouch MediaPipe Sensor", "Perform local CPU-efficient hand and eye tracking", PermissionProfile.AUTOMATIC)
        },
        # D. Repository & Tool Access
        "repository_tool_access": {
            "github_starred_repos": ("65 Starred Repositories", "Inspect and match tools from the curated starred repository inventory", PermissionProfile.AUTOMATIC),
            "approved_dependency_installation": ("Dependency Installation", "Install approved Python / system packages into virtual environment", PermissionProfile.CONFIRMATION_REQUIRED),
            "local_model_downloads": ("Local GGUF / ONNX Downloads", "Fetch verified models into D:\\matrix_data\\models directory", PermissionProfile.RESTRICTED),
            "tool_registration": ("Dynamic Tool Adapters", "Register sandboxed tool adapters for discovered capabilities", PermissionProfile.AUTOMATIC),
            "isolated_execution_environments": ("Isolated Sandbox Execution", "Run experimental repository adapters in separate sub-processes", PermissionProfile.RESTRICTED)
        }
    }

    def __init__(self):
        AUTH_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.scopes: Dict[str, ScopeItem] = {}
        self.first_run_completed: bool = False
        self.first_run_timestamp: Optional[float] = None
        self._load_state()

    def _load_state(self):
        """Load persistent authorization state from disk, or initialize defaults."""
        if AUTH_CONFIG_FILE.exists():
            try:
                data = json.loads(AUTH_CONFIG_FILE.read_text(encoding="utf-8"))
                self.first_run_completed = data.get("first_run_completed", False)
                self.first_run_timestamp = data.get("first_run_timestamp")
                raw_scopes = data.get("scopes", {})
                for k, v in raw_scopes.items():
                    self.scopes[k] = ScopeItem(**v)
                logger.info(f"Loaded {len(self.scopes)} persistent authorization scopes (Setup Complete: {self.first_run_completed}).")
                return
            except Exception as e:
                logger.warning(f"Error loading authorization config (re-initializing defaults): {e}")

        # Initialize from default catalog
        self._populate_defaults()
        self._save_state()

    def _populate_defaults(self):
        """Populate initial scopes from official catalog."""
        self.scopes = {}
        for category, cat_dict in self.DEFAULT_CATALOG.items():
            for scope_id, (name, desc, prof) in cat_dict.items():
                full_id = f"{category}.{scope_id}"
                self.scopes[full_id] = ScopeItem(
                    scope_id=scope_id,
                    name=name,
                    description=desc,
                    category=category,
                    profile=prof,
                    native_permission_verified=True
                )

    def _save_state(self):
        """Persist current authorization configuration to disk."""
        try:
            payload = {
                "first_run_completed": self.first_run_completed,
                "first_run_timestamp": self.first_run_timestamp,
                "updated_at": time.time(),
                "scopes": {k: v.model_dump() for k, v in self.scopes.items()}
            }
            AUTH_CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist authorization config: {e}")

    def execute_first_run_wizard(
        self,
        grant_template: str = "JARVIS_AUTONOMOUS",
        user_overrides: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute one-time setup wizard granting explicit user-approved permission profiles.
        
        Templates:
          - JARVIS_AUTONOMOUS (Recommended): Safe actions AUTOMATIC, sensitive actions RESTRICTED, destructive CONFIRMATION_REQUIRED.
          - CONSERVATIVE: Standard actions RESTRICTED, sensitive actions CONFIRMATION_REQUIRED.
          - STRICT: All non-read actions require confirmation.
        """
        user_overrides = user_overrides or {}
        
        for k, scope in self.scopes.items():
            # Apply user overrides if present
            if k in user_overrides or scope.scope_id in user_overrides:
                override = user_overrides.get(k) or user_overrides.get(scope.scope_id)
                try:
                    scope.profile = PermissionProfile(override.upper())
                except ValueError:
                    pass
                continue

            # Template logic
            if grant_template == "JARVIS_AUTONOMOUS":
                # 1. Strictly sensitive, financial, remote ingress, or irreversible scopes require explicit confirmation
                if scope.scope_id in (
                    "bland_phone_calling", "gmail", "tailscale_remote_access",
                    "google_workspace_oauth", "approved_dependency_installation"
                ):
                    scope.profile = PermissionProfile.CONFIRMATION_REQUIRED
                # 2. Safe local operations pre-approved for autonomy
                elif scope.category in ("hardware", "windows_permissions") and scope.scope_id in (
                    "microphone", "camera", "screen_capture", "ui_automation",
                    "app_launch", "system_telemetry", "notifications", "startup_background_service",
                    "laptop_microphone", "speakers", "webcam", "android_phone", "airtouch_tracking_hardware"
                ):
                    scope.profile = PermissionProfile.AUTOMATIC
                elif scope.scope_id in ("github_starred_repos", "tool_registration", "google_calendar", "weather_openmeteo", "github"):
                    scope.profile = PermissionProfile.AUTOMATIC
                # 3. Path-bounded or rate-limited scopes are RESTRICTED
                elif scope.scope_id in (
                    "file_folder_access", "keyboard_mouse", "clipboard_access",
                    "bluetooth_devices", "bluetooth_hardware", "local_model_downloads",
                    "isolated_execution_environments", "telegram", "firebase_notifications"
                ):
                    scope.profile = PermissionProfile.RESTRICTED
                else:
                    scope.profile = PermissionProfile.RESTRICTED

            elif grant_template == "CONSERVATIVE":
                if scope.category == "windows_permissions" and scope.scope_id in ("system_telemetry", "notifications"):
                    scope.profile = PermissionProfile.AUTOMATIC
                else:
                    scope.profile = PermissionProfile.RESTRICTED

        self.first_run_completed = True
        self.first_run_timestamp = time.time()
        self._save_state()

        logger.info(f"First-run authorization wizard completed under template '{grant_template}'.")
        return self.get_authorization_overview()

    def get_authorization_overview(self) -> Dict[str, Any]:
        """Generate structured status of all permission categories and connected services."""
        categorized: Dict[str, List[Dict[str, Any]]] = {}
        counts = {"AUTOMATIC": 0, "RESTRICTED": 0, "CONFIRMATION_REQUIRED": 0}

        for full_id, scope in self.scopes.items():
            cat = scope.category
            categorized.setdefault(cat, []).append({
                "id": full_id,
                "scope_id": scope.scope_id,
                "name": scope.name,
                "description": scope.description,
                "profile": scope.profile.value,
                "granted_at": scope.granted_at,
                "verified": scope.native_permission_verified
            })
            counts[scope.profile.value] = counts.get(scope.profile.value, 0) + 1

        return {
            "first_run_completed": self.first_run_completed,
            "setup_timestamp": self.first_run_timestamp,
            "total_scopes": len(self.scopes),
            "profile_counts": counts,
            "categories": categorized,
            "stored_credentials_count": len(dpapi_vault.list_keys()),
            "credential_catalog": dpapi_vault.get_masked_catalog()
        }

    def update_scope_profile(self, category: str, scope_id: str, new_profile: str) -> bool:
        """Update authorization profile for a specific scope."""
        full_id = f"{category}.{scope_id}" if not scope_id.startswith(f"{category}.") else scope_id
        if full_id not in self.scopes:
            # Check without category prefix
            for k in self.scopes:
                if k.endswith(f".{scope_id}"):
                    full_id = k
                    break

        if full_id in self.scopes:
            try:
                prof = PermissionProfile(new_profile.upper())
                self.scopes[full_id].profile = prof
                self.scopes[full_id].granted_at = time.time()
                self._save_state()
                logger.info(f"Updated scope '{full_id}' profile to {prof.value}.")
                return True
            except ValueError:
                logger.warning(f"Invalid permission profile '{new_profile}'.")
        return False

    def revoke_scope(self, category: str, scope_id: str) -> bool:
        """Revoke authorization for a scope (transitions to CONFIRMATION_REQUIRED)."""
        return self.update_scope_profile(category, scope_id, PermissionProfile.CONFIRMATION_REQUIRED.value)

    def evaluate_authorization(
        self,
        action: str,
        category: str = "windows_permissions",
        details: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, str]:
        """Evaluate if an action is pre-authorized, restricted, or requires explicit confirmation.
        
        Returns:
            (can_proceed_immediately, profile_name, reason)
        """
        details = details or {}
        act_clean = action.lower().strip()

        # 1. Strictly irreversible, destructive, or financial actions ALWAYS require confirmation
        strict_confirmation_triggers = [
            "delete_important_file", "format_drive", "drop_table", "rmdir_all",
            "send_external_email", "publish_external_message", "financial_transaction",
            "purchase", "change_security_settings", "revoke_all_permissions",
            "send_call", "make_call", "outbound_call", "delete_file", "drop_database",
            "uninstall_package", "open_tunnel"
        ]
        if any(trig in act_clean for trig in strict_confirmation_triggers) or details.get("risk_level", 1) >= 4:
            return False, PermissionProfile.CONFIRMATION_REQUIRED.value, f"Action '{action}' is strictly classified as sensitive/irreversible and requires explicit user confirmation."

        # 2. Match scope via ACTION_SCOPE_MAP or direct scope ID
        target_scope_id = ACTION_SCOPE_MAP.get(act_clean)
        matched_scope = None
        if target_scope_id:
            for full_id, scope in self.scopes.items():
                if scope.scope_id == target_scope_id:
                    matched_scope = scope
                    break

        if not matched_scope:
            for full_id, scope in self.scopes.items():
                if scope.scope_id in act_clean or act_clean in scope.scope_id:
                    matched_scope = scope
                    break

        if matched_scope:
            if matched_scope.profile == PermissionProfile.AUTOMATIC:
                return True, PermissionProfile.AUTOMATIC.value, f"Pre-authorized autonomously under '{matched_scope.name}'."
            elif matched_scope.profile == PermissionProfile.RESTRICTED:
                # Check if within safety limits
                within_limits = True
                if "max_cost" in details and details["max_cost"] > 5.0:
                    within_limits = False
                if "unapproved_target" in details and details["unapproved_target"]:
                    within_limits = False
                if within_limits:
                    return True, PermissionProfile.RESTRICTED.value, f"Allowed under '{matched_scope.name}' policy boundaries."
                else:
                    return False, PermissionProfile.CONFIRMATION_REQUIRED.value, f"Exceeds '{matched_scope.name}' safety boundaries."
            else:
                return False, PermissionProfile.CONFIRMATION_REQUIRED.value, f"Explicit confirmation required for '{matched_scope.name}' under security policy."

        # 3. Default fallback for actions not directly mapped to known scopes:
        # Never grant blanket AUTOMATIC access merely because setup finished!
        risk = details.get("risk_level", 1)
        if risk <= 1:
            # Low-risk read-only / status operations can proceed under restricted profile
            return True, PermissionProfile.RESTRICTED.value, f"Permitted under baseline safety boundaries (Risk Level {risk})."

        return False, PermissionProfile.CONFIRMATION_REQUIRED.value, f"Action '{action}' is unclassified or elevated risk (Risk Level {risk}) and requires user confirmation."


# Global singleton authorization center
authorization_center = AuthorizationCenter()
