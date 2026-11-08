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
