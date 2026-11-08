"""MATRIX Account Operations Models.
Defines schemas for authorized external service connectors, authentication types,
permission grants, and audit trails.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    SOCIAL_MEDIA = "social_media"
    CLOUD_STORAGE = "cloud_storage"
    PROJECT_MANAGEMENT = "project_management"
    DEVELOPER_PLATFORM = "developer_platform"
    CUSTOM_WEB = "custom_web"


class AuthType(str, Enum):
    OAUTH2 = "oauth2"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"
    API_KEY = "api_key"
    APP_PASSWORD = "app_password"
    SESSION_TOKEN = "session_token"


class AccountStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PENDING_AUTHORIZATION = "pending_authorization"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ConnectedAccount(BaseModel):
    account_id: str
    service_name: str
    service_type: ServiceType
    account_identifier: str  # e.g. "user@example.com" or "github_username" (never secret)
    auth_type: AuthType
    status: AccountStatus = AccountStatus.CONNECTED
    permissions_granted: List[str] = Field(default_factory=list)
    credential_ref: str  # Reference key in secure credential store (never raw token in logs)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_synced_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccountOperationRecord(BaseModel):
    operation_id: str
    account_id: str
    service_name: str
    action_type: str  # e.g. "draft_email", "search_issues", "read_profile"
    status: str       # "SUCCESS", "BLOCKED", "PENDING_CONFIRMATION", "FAILED"
    requires_level3_approval: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
    changed_items: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
