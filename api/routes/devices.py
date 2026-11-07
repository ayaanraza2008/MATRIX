"""MATRIX Device Pairing & Synchronization API Route.
Handles secure token pairing between Windows 11 PC and the Android companion app.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional
import uuid
import hashlib
from datetime import datetime, timezone

from database.session import get_db
from database.models import Device as DeviceModel
from config.logging_config import get_logger

logger = get_logger("api.devices")
router = APIRouter(prefix="/devices", tags=["Device Pairing & Synchronization"])


class PairRequest(BaseModel):
    device_id: str
    name: str
    platform: str  # 'android', 'windows', 'web'
    pairing_token: str


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    name: str
    platform: str
    is_paired: bool
    last_seen_at: datetime
    created_at: datetime


@router.post("/pair", status_code=status.HTTP_200_OK)
async def pair_device(payload: PairRequest, db: AsyncSession = Depends(get_db)):
    """Authorize and pair a new client device (such as the Android app)."""
    # Verify pairing token format
    if not payload.pairing_token.startswith("mtx_pair_"):
        raise HTTPException(status_code=400, detail="Invalid pairing token format.")

    stmt = select(DeviceModel).where(DeviceModel.device_id == payload.device_id)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    auth_token = f"mtx_auth_{uuid.uuid4().hex}"
    token_hash = hashlib.sha256(auth_token.encode()).hexdigest()

    if existing:
        existing.is_paired = True
        existing.auth_token_hash = token_hash
        existing.last_seen_at = datetime.now(timezone.utc)
    else:
        new_device = DeviceModel(
            device_id=payload.device_id,
            name=payload.name,
            platform=payload.platform,
            is_paired=True,
            auth_token_hash=token_hash
        )
        db.add(new_device)

    await db.commit()
    logger.info(f"Paired device '{payload.name}' ({payload.device_id}) successfully.")

    return {
        "status": "PAIRED",
        "device_id": payload.device_id,
        "auth_token": auth_token,
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all registered and paired devices."""
    stmt = select(DeviceModel).order_by(DeviceModel.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.delete("/{device_id}", status_code=status.HTTP_200_OK)
async def revoke_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Revoke authorization for a device."""
    stmt = delete(DeviceModel).where(DeviceModel.device_id == device_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found.")
    logger.info(f"Revoked authorization for device '{device_id}'")
    return {"status": "REVOKED", "device_id": device_id}
