"""MATRIX Device Authentication & Remote Access Security Layer.
Enforces cryptographic token generation, SHA-256 hash storage, TTL expiration,
token rotation, and FastAPI authentication dependencies for remote companion devices.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import uuid
from typing import Optional, Tuple
from fastapi import Header, Query, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.models import Device as DeviceModel
from config.logging_config import get_logger

logger = get_logger("device_auth")

DEFAULT_TOKEN_LIFETIME_DAYS = 30


def hash_token(token: str) -> str:
    """Compute SHA-256 digest of a raw authentication token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_auth_token(lifetime_days: int = DEFAULT_TOKEN_LIFETIME_DAYS) -> Tuple[str, str, datetime]:
    """Generate a high-entropy authentication token, its SHA-256 hash, and expiration timestamp.
    Returns: (raw_token, token_hash, expires_at)
    """
    raw_token = f"mtx_auth_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=lifetime_days)
    return raw_token, token_hash, expires_at


async def get_authenticated_device(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None, alias="token"),
    db: AsyncSession = Depends(get_db)
) -> DeviceModel:
    """FastAPI dependency: Authenticates requests from remote companion devices.
    Checks 'Authorization: Bearer <token>' header or '?token=<token>' query parameter.
    Validates token presence, active pairing, non-revoked state, and TTL expiration.
    """
    raw_token = None
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]
        elif len(parts) == 1:
            raw_token = parts[0]
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials missing. Provide 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    t_hash = hash_token(raw_token)
    stmt = select(DeviceModel).where(
        DeviceModel.auth_token_hash == t_hash,
        DeviceModel.is_paired == True
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if not device:
        logger.warning(f"Rejected unauthorized request with invalid or revoked token hash: {t_hash[:12]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authorization revoked or invalid.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate token expiration
    if device.token_expires_at:
        exp = device.token_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            logger.warning(f"Rejected request from device '{device.device_id}': Token expired at {exp.isoformat()}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token expired. Please rotate token or re-pair.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # Touch last_seen_at
    device.last_seen_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except Exception:
        pass

    return device


async def validate_token_raw(raw_token: str, db: AsyncSession) -> Optional[DeviceModel]:
    """Validate token programmatically without raising HTTP exceptions (for WebSockets/internal checks)."""
    if not raw_token:
        return None
    t_hash = hash_token(raw_token.strip())
    stmt = select(DeviceModel).where(
        DeviceModel.auth_token_hash == t_hash,
        DeviceModel.is_paired == True
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if not device:
        return None

    if device.token_expires_at:
        exp = device.token_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            return None

    return device
