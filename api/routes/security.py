"""MATRIX Security & 4-Tier Autonomy Policy API Route.
Exposes autonomy levels, pending Level 4 approval gates, approval/rejection endpoints,
and security scopes.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from security.permissions.manager import security_manager, AutonomyLevel
from config.logging_config import get_logger

logger = get_logger("api.security")
router = APIRouter(prefix="/security", tags=["Security & Autonomy Policy"])


class AutonomyLevelPayload(BaseModel):
    level: int  # 1 to 4


class ApprovalActionPayload(BaseModel):
    confirmed_by: str = "user"
    reason: Optional[str] = None


@router.get("/autonomy")
async def get_autonomy_status():
    """Retrieve current system-wide autonomy level, description, and pending gates."""
    return security_manager.get_dashboard_summary()


@router.post("/autonomy")
async def set_autonomy_level(payload: AutonomyLevelPayload):
    """Update active system-wide autonomy policy (1=Observe, 2=Assist, 3=Autonomous, 4=Supervised)."""
    if payload.level not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Autonomy level must be 1, 2, 3, or 4.")
    new_lvl = security_manager.set_global_autonomy_level(payload.level)
    return {
        "status": "UPDATED",
        "active_level": new_lvl.value,
        "level_name": new_lvl.name
    }


@router.get("/pending-gates")
async def list_pending_approval_gates():
    """List pending Level 4 supervised confirmation requests requiring human approval."""
    pending = security_manager.list_pending_requests()
    return {
        "pending_count": len(pending),
        "requests": pending
    }


@router.post("/approve/{request_id}")
async def approve_gate(request_id: str, payload: Optional[ApprovalActionPayload] = None):
    """Approve a pending Level 4 critical action."""
    confirmed_by = payload.confirmed_by if payload else "user"
    success = security_manager.confirm_request(request_id, confirmed_by=confirmed_by)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found, already resolved, or expired.")
    return {"status": "APPROVED", "request_id": request_id}


@router.post("/reject/{request_id}")
async def reject_gate(request_id: str, payload: Optional[ApprovalActionPayload] = None):
    """Reject a pending Level 4 critical action."""
    reason = payload.reason if payload and payload.reason else "User rejected"
    success = security_manager.reject_request(request_id, reason=reason)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or already resolved.")
    return {"status": "REJECTED", "request_id": request_id}


# =============================================================================
# PART 2: ONE-TIME AUTHORIZATION CENTER & DPAPI ENCRYPTED VAULT ENDPOINTS
# =============================================================================

from security.permissions.authorization_center import authorization_center
from security.vault.dpapi_vault import dpapi_vault


class SetupWizardPayload(BaseModel):
    template: str = "JARVIS_AUTONOMOUS"  # JARVIS_AUTONOMOUS, CONSERVATIVE, STRICT
    overrides: Optional[Dict[str, str]] = None


class ScopeUpdatePayload(BaseModel):
    category: str
    scope_id: str
    profile: str  # AUTOMATIC, RESTRICTED, CONFIRMATION_REQUIRED


class StoreSecretPayload(BaseModel):
    key: str
    value: str


@router.get("/authorization-center")
async def get_authorization_center_status():
    """Retrieve complete overview of permission profiles, categories, and connected service states."""
    return authorization_center.get_authorization_overview()


@router.post("/setup-wizard")
async def run_setup_wizard(payload: SetupWizardPayload):
    """Execute the One-Time Setup Wizard to configure approved baseline permissions."""
    result = authorization_center.execute_first_run_wizard(
        grant_template=payload.template,
        user_overrides=payload.overrides
    )
    return {
        "status": "SETUP_COMPLETED",
        "overview": result
    }


@router.post("/scopes/update")
async def update_permission_scope(payload: ScopeUpdatePayload):
    """Update or customize the authorization profile for a specific permission scope."""
    success = authorization_center.update_scope_profile(
        category=payload.category,
        scope_id=payload.scope_id,
        new_profile=payload.profile
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to update scope '{payload.scope_id}'.")
    return {
        "status": "UPDATED",
        "scope_id": payload.scope_id,
        "new_profile": payload.profile.upper()
    }


@router.post("/scopes/revoke")
async def revoke_permission_scope(payload: ScopeUpdatePayload):
    """Revoke a permission scope (transitions to CONFIRMATION_REQUIRED)."""
    success = authorization_center.revoke_scope(
        category=payload.category,
        scope_id=payload.scope_id
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to revoke scope '{payload.scope_id}'.")
    return {
        "status": "REVOKED",
        "scope_id": payload.scope_id
    }


@router.get("/vault/catalog")
async def get_vault_catalog():
    """List secret key identifiers stored in the encrypted DPAPI vault (masked values)."""
    return {
        "total_secrets": len(dpapi_vault.list_keys()),
        "keys": dpapi_vault.list_keys(),
        "catalog": dpapi_vault.get_masked_catalog()
    }


@router.post("/vault/secret")
async def store_vault_secret(payload: StoreSecretPayload):
    """Store an API key or credential securely in the native Windows DPAPI encrypted vault."""
    if not payload.key or not payload.value:
        raise HTTPException(status_code=400, detail="Key and value are required.")
    dpapi_vault.store_secret(payload.key, payload.value)
    return {
        "status": "STORED_ENCRYPTED",
        "key": payload.key.upper()
    }


@router.delete("/vault/secret/{key}")
async def delete_vault_secret(key: str):
    """Delete a secret from the encrypted DPAPI vault."""
    success = dpapi_vault.delete_secret(key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Secret '{key}' not found in vault.")
    return {
        "status": "DELETED",
        "key": key.upper()
    }

