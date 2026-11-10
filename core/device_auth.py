"""MATRIX Device Authentication & Remote Access Security Layer.
Enforces cryptographic token generation, SHA-256 hash storage, TTL expiration,
token rotation, rate limiting, anti-replay nonce tracking, and FastAPI authentication
dependencies for remote companion devices.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import uuid
import time
import threading
from typing import Optional, Tuple, Dict, List
from fastapi import Header, Query, Request, HTTPException, status, Depends
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


def mask_token(token: Optional[str]) -> str:
    """Mask token string for safe logging without exposing credentials."""
    if not token or len(token) < 12:
        return "***"
    return f"{token[:8]}...{token[-4:]}"


def generate_auth_token(lifetime_days: int = DEFAULT_TOKEN_LIFETIME_DAYS) -> Tuple[str, str, datetime]:
    """Generate a high-entropy authentication token, its SHA-256 hash, and expiration timestamp.
    Returns: (raw_token, token_hash, expires_at)
    """
    raw_token = f"mtx_auth_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=lifetime_days)
    return raw_token, token_hash, expires_at


class SecurityRateLimiter:
    """In-memory sliding window rate limiter and anti-replay nonce cache."""

    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}
        self._seen_nonces: Dict[str, float] = {}

    def check_rate_limit(self, key: str, max_requests: int = 15, window_seconds: int = 60) -> bool:
        """Check if request count for key within window is below threshold."""
        now = time.time()
        with self._lock:
            timestamps = self._requests.get(key, [])
            # Filter timestamps outside window
            valid_ts = [t for t in timestamps if (now - t) < window_seconds]
            if len(valid_ts) >= max_requests:
                self._requests[key] = valid_ts
                return False
            valid_ts.append(now)
            self._requests[key] = valid_ts
            return True

    def validate_nonce(self, nonce: str, timestamp_str: Optional[str], max_skew_seconds: int = 300) -> Tuple[bool, str]:
        """Validate anti-replay nonce and client timestamp skew."""
        now = time.time()
        if timestamp_str:
            try:
                # Handle ISO 8601 or float epoch
                if "T" in timestamp_str:
                    client_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    client_ts = client_dt.timestamp()
                else:
                    client_ts = float(timestamp_str)
                if abs(now - client_ts) > max_skew_seconds:
                    return False, f"Clock skew exceeded: timestamp differs by {abs(now - client_ts):.1f}s (max {max_skew_seconds}s)"
            except Exception as e:
                return False, f"Malformed timestamp format: {e}"

        with self._lock:
            # Clean expired nonces
            expired = [n for n, exp in self._seen_nonces.items() if now > exp]
            for n in expired:
                del self._seen_nonces[n]

            if nonce in self._seen_nonces:
                return False, "Replay attack detected: Nonce has already been consumed."

            # Store nonce with TTL
            self._seen_nonces[nonce] = now + max_skew_seconds
            return True, "Nonce valid"


security_rate_limiter = SecurityRateLimiter()


async def get_authenticated_device(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None, alias="token"),
    x_matrix_nonce: Optional[str] = Header(None, alias="X-Matrix-Nonce"),
    x_matrix_timestamp: Optional[str] = Header(None, alias="X-Matrix-Timestamp"),
    db: AsyncSession = Depends(get_db)
) -> DeviceModel:
    """FastAPI dependency: Authenticates requests from remote companion devices.
    Checks 'Authorization: Bearer <token>' header or '?token=<token>' query parameter.
    Enforces rate limits, validates token existence, non-revoked state, and TTL expiration.
    Optionally evaluates anti-replay headers.
    """
    client_ip = request.client.host if request.client else "unknown"

    # 1. Rate Limiting Check
    if not security_rate_limiter.check_rate_limit(f"auth_{client_ip}", max_requests=120, window_seconds=60):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Too many requests from this address."
        )

    # 2. Anti-Replay Nonce Check (if client provides headers)
    if x_matrix_nonce:
        nonce_valid, nonce_msg = security_rate_limiter.validate_nonce(x_matrix_nonce, x_matrix_timestamp)
        if not nonce_valid:
            logger.warning(f"Rejected request from {client_ip}: {nonce_msg}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Security rejection: {nonce_msg}"
            )

    # 3. Token Extraction
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
        logger.warning(f"Rejected unauthorized request from {client_ip} with token {mask_token(raw_token)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authorization revoked or invalid.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 4. Token Expiration Validation
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

    # 5. Touch device metadata
    device.last_seen_at = datetime.now(timezone.utc)
    device.last_ip = client_ip
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
