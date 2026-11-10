"""MATRIX Security Audit Log API Route.
Surfaces the persistent, tamper-evident security audit log from SQLite.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database.session import get_db
from database.models import AuditLog

router = APIRouter(prefix="/audit", tags=["Security Audit Trail"])


class AuditResponse(BaseModel):
    id: int
    event_type: str
    risk_level: int
    tool_name: Optional[str]
    actor: str
    action_summary: str
    status: str
    timestamp: datetime


@router.get("", response_model=List[AuditResponse])
async def list_audit_logs(db: AsyncSession = Depends(get_db)):
    """Retrieve immutable audit trail entries in reverse chronological order."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
    res = await db.execute(stmt)
    return res.scalars().all()
