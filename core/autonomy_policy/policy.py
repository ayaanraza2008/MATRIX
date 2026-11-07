"""MATRIX Autonomy Policy Engine.
Enforces the 3-tier autonomy model for repository intelligence, tool selection, installation, and execution:
  - LEVEL 1: Automatic execution (no user confirmation required for low-risk, internal, or preapproved operations)
  - LEVEL 2: Policy-controlled automation (proceeds independently if within allowlist, budget, and provenance rules)
  - LEVEL 3: User authorization required (strict gate for destructive, financial, private, or untrusted actions)
"""
from enum import Enum, IntEnum
from typing import Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from config.logging_config import get_logger

logger = get_logger("core.autonomy_policy")


class AutonomyLevel(IntEnum):
    LEVEL_1_AUTOMATIC = 1
    LEVEL_2_POLICY_CONTROLLED = 2
    LEVEL_3_USER_AUTHORIZATION = 3


class ActionCategory(str, Enum):
    # Level 1 Actions
    SEARCH_INVENTORY = "search_inventory"
    READ_DOCUMENTATION = "read_documentation"
    COMPARE_LIBRARIES = "compare_libraries"
    SELECT_INSTALLED_TOOL = "select_installed_tool"
    RUN_APPROVED_TOOL = "run_approved_tool"
    CREATE_WORKSPACE_TEMP = "create_workspace_temp"
    CREATE_ISOLATED_ENV = "create_isolated_env"
    INSTALL_PREAPPROVED_DEP = "install_preapproved_dep"
    REGISTER_CAPABILITY = "register_capability"
    RETRY_RECOVERABLE = "retry_recoverable"

    # Level 2 Actions
    INSTALL_NEW_REPOSITORY = "install_new_repository"
    DOWNLOAD_MODEL = "download_model"
    UPDATE_DEPENDENCIES = "update_dependencies"
    START_BACKGROUND_SERVICE = "start_background_service"
    OUTBOUND_NETWORK_REQUEST = "outbound_network_request"
    USE_EXTERNAL_API = "use_external_api"
    MODIFY_PROJECT_CONFIG = "modify_project_config"

    # Level 3 Actions (Mandatory Human Authorization)
    DELETE_USER_DATA = "delete_user_data"
    FORMAT_DRIVE = "format_drive"
    ACCESS_CREDENTIALS = "access_credentials"
    SEND_PRIVATE_DATA_EXTERNALLY = "send_private_data_externally"
    PUBLISH_EXTERNAL_MESSAGE = "publish_external_message"
    FINANCIAL_TRANSACTION = "financial_transaction"
    CHANGE_SECURITY_SETTINGS = "change_security_settings"
    INSTALL_UNTRUSTED_SOFTWARE = "install_untrusted_software"
    DESTRUCTIVE_SYSTEM_COMMAND = "destructive_system_command"


class PolicyVerdict(BaseModel):
    allowed: bool
    required_level: AutonomyLevel
    requires_user_confirmation: bool
    reason: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutonomyPolicyEngine:
    """Evaluates proposed actions against MATRIX's 3-level safety and autonomy matrix."""

    def __init__(self, active_level: AutonomyLevel = AutonomyLevel.LEVEL_2_POLICY_CONTROLLED):
        self.active_level = active_level
        
        # Pre-approved Python libraries that Level 1/2 can install automatically
        self.approved_packages: Set[str] = {
            "beautifulsoup4", "requests", "httpx", "aiohttp", "pydantic", "fastapi",
            "uvicorn", "playwright", "sounddevice", "numpy", "scipy", "pillow",
            "opencv-python", "pyyaml", "rich", "typer", "gitpython", "psutil",
            "jinja2", "markdown", "openwakeword", "faster-whisper", "edge-tts",
            "pyttsx3", "llama-cpp-python", "onnxruntime", "sympy", "networkx",
            "pypdf", "docx2txt", "openpyxl", "pandas"
        }

        # Pre-approved repository sources
        self.trusted_repo_owners: Set[str] = {
            "jixserver", "udaysharmadev", "0x4m4", "citrolabs", "mobile-next",
            "resemble-ai", "penpot", "immich-app", "tashfeenahmed", "mnfst",
            "google-research", "codecrafters-io", "NousResearch", "browser-use",
            "cjpais", "volcengine", "mukul975", "cathrynlavery", "K-Dense-AI",
            "rohitg00", "public-apis", "debpalash", "k2-fsa", "AbuZar-Ansarii"
        }

        # Destructive command tokens that trigger Level 3 immediately
        self.destructive_tokens = [
            "del /", "rmdir /s", "rm -rf", "format ", "mkfs", "drop table",
            "drop database", "shutdown", "diskpart", "fdisk", "reg delete",
            "password", "secret", "private_key", "credentials", "id_rsa"
        ]

    def evaluate(
        self,
        action: ActionCategory | str,
        details: Optional[Dict[str, Any]] = None,
        is_user_confirmed: bool = False
    ) -> PolicyVerdict:
        """Evaluate action against policy rules and return a PolicyVerdict."""
        details = details or {}
        act_str = action.value if isinstance(action, ActionCategory) else str(action)
        
        # 1. Check for explicit destructive / credential patterns
        payload_str = str(details).lower()
        if any(token in payload_str for token in self.destructive_tokens):
            if not is_user_confirmed:
                logger.warning(f"Level 3 Security Gate: Destructive token detected in action '{act_str}'")
                return PolicyVerdict(
                    allowed=False,
                    required_level=AutonomyLevel.LEVEL_3_USER_AUTHORIZATION,
                    requires_user_confirmation=True,
                    reason="Destructive command, drive modification, or credential access detected.",
                    action=act_str,
                    details=details
                )

        # 2. Level 3 Actions: Always require explicit human authorization
        level_3_actions = {
            ActionCategory.DELETE_USER_DATA.value,
            ActionCategory.FORMAT_DRIVE.value,
            ActionCategory.ACCESS_CREDENTIALS.value,
            ActionCategory.SEND_PRIVATE_DATA_EXTERNALLY.value,
            ActionCategory.PUBLISH_EXTERNAL_MESSAGE.value,
            ActionCategory.FINANCIAL_TRANSACTION.value,
            ActionCategory.CHANGE_SECURITY_SETTINGS.value,
            ActionCategory.INSTALL_UNTRUSTED_SOFTWARE.value,
            ActionCategory.DESTRUCTIVE_SYSTEM_COMMAND.value,
        }

        if act_str in level_3_actions:
            if is_user_confirmed:
                return PolicyVerdict(
                    allowed=True,
                    required_level=AutonomyLevel.LEVEL_3_USER_AUTHORIZATION,
                    requires_user_confirmation=False,
                    reason="User explicitly authorized Level 3 operation.",
                    action=act_str,
                    details=details
                )
            return PolicyVerdict(
                allowed=False,
                required_level=AutonomyLevel.LEVEL_3_USER_AUTHORIZATION,
                requires_user_confirmation=True,
                reason=f"Action '{act_str}' requires explicit user authorization under Level 3 policy.",
                action=act_str,
                details=details
            )

        # 3. Level 2 Actions: Policy-controlled automation
        level_2_actions = {
            ActionCategory.INSTALL_NEW_REPOSITORY.value,
            ActionCategory.DOWNLOAD_MODEL.value,
            ActionCategory.UPDATE_DEPENDENCIES.value,
            ActionCategory.START_BACKGROUND_SERVICE.value,
            ActionCategory.OUTBOUND_NETWORK_REQUEST.value,
            ActionCategory.USE_EXTERNAL_API.value,
            ActionCategory.MODIFY_PROJECT_CONFIG.value,
        }

        if act_str in level_2_actions:
            # Check repository provenance if installing
            repo_name = details.get("repo", "") or details.get("full_name", "")
            if repo_name:
                owner = repo_name.split("/")[0] if "/" in repo_name else repo_name
                if owner not in self.trusted_repo_owners and not is_user_confirmed:
                    return PolicyVerdict(
                        allowed=False,
                        required_level=AutonomyLevel.LEVEL_3_USER_AUTHORIZATION,
                        requires_user_confirmation=True,
                        reason=f"Repository owner '{owner}' is not in the trusted inventory allowlist.",
                        action=act_str,
                        details=details
                    )

            # Check download file size / resource budget
            est_size_mb = details.get("size_mb", 0)
            if est_size_mb > 5000 and not is_user_confirmed:
                return PolicyVerdict(
                    allowed=False,
                    required_level=AutonomyLevel.LEVEL_3_USER_AUTHORIZATION,
                    requires_user_confirmation=True,
                    reason=f"Download size ({est_size_mb} MB) exceeds automated Level 2 threshold (5GB).",
                    action=act_str,
                    details=details
                )

            return PolicyVerdict(
                allowed=True,
                required_level=AutonomyLevel.LEVEL_2_POLICY_CONTROLLED,
                requires_user_confirmation=False,
                reason="Pre-approved under Level 2 Policy-Controlled Automation.",
                action=act_str,
                details=details
            )

        # 4. Level 1 Actions: Automatic Execution
        return PolicyVerdict(
            allowed=True,
            required_level=AutonomyLevel.LEVEL_1_AUTOMATIC,
            requires_user_confirmation=False,
            reason="Fully authorized under Level 1 Automatic Policy.",
            action=act_str,
            details=details
        )


# Global policy engine instance
autonomy_policy = AutonomyPolicyEngine()
