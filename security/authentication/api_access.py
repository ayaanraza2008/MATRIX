"""Request-level access control for MATRIX HTTP endpoints.

Threat model
------------
MATRIX binds to localhost by default but is *intended* to be reached from an Android
companion over the LAN. Without a gate, any host on that LAN (or a malicious web page
performing a request against ``127.0.0.1``) could drive privileged endpoints such as
``/api/v1/developer/execute``.

Policy
------
* Loopback / configured trusted hosts are always allowed (the local user is the owner).
* Remote clients must present either ``MATRIX_API_TOKEN`` as a bearer token or a valid,
  unexpired, paired device token (created by the device pairing flow).
* Destructive or code-executing surfaces additionally require ``MATRIX_DEVELOPER_MODE``.
"""
from __future__ import annotations

import hmac
import ipaddress
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.logging_config import get_logger
from config.settings import settings
from core.device_auth import validate_token_raw
from database.session import get_db

logger = get_logger("security.api_access")


def is_trusted_client(host: Optional[str]) -> bool:
    """Return True for loopback addresses and explicitly configured trusted hosts."""
    if not host:
        return False
    if host in settings.trusted_hosts:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if address.is_loopback:
        return True
    # IPv4-mapped IPv6 loopback, e.g. ::ffff:127.0.0.1
    mapped = getattr(address, "ipv4_mapped", None)
    return bool(mapped and mapped.is_loopback)


def extract_bearer(authorization: Optional[str]) -> Optional[str]:
    """Extract a bearer token from an ``Authorization`` header value."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    if len(parts) == 1:
        return parts[0].strip()
    return None


def matches_api_token(token: str) -> bool:
    """Constant-time comparison against the configured shared API token."""
    expected = settings.api_token
    if not expected:
        return False
    return hmac.compare_digest(token, expected)


async def require_authenticated_client(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """FastAPI dependency: allow trusted local clients, token-holding remote clients."""
    host = request.client.host if request.client else None
    if is_trusted_client(host):
        return

    token = extract_bearer(authorization)
    if token and matches_api_token(token):
        return
    if token and await validate_token_raw(token, db):
        return

    logger.warning(
        "Rejected privileged request from %s to %s (no valid credentials).",
        host or "unknown",
        request.url.path,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Authentication required for non-local clients. Provide "
            "'Authorization: Bearer <MATRIX_API_TOKEN>' or pair this device."
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_developer_mode() -> None:
    """FastAPI dependency: keep code-execution endpoints disabled unless opted in."""
    if not settings.developer_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Developer Studio execution is disabled. Set MATRIX_DEVELOPER_MODE=true "
                "to enable code execution endpoints on this machine."
            ),
        )
