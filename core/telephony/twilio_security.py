"""MATRIX Twilio Security & Signature Verification.
Validates Twilio webhook authenticity using HMAC-SHA1 signature verification
per official Twilio Security specifications:
https://www.twilio.com/docs/usage/security#validating-requests
"""
import hmac
import hashlib
import base64
import os
from typing import Dict, Any, Optional
from config.logging_config import get_logger

logger = get_logger("telephony.security")


def compute_twilio_signature(url: str, params: Dict[str, Any], auth_token: str) -> str:
    """Compute Twilio HMAC-SHA1 signature for a webhook URL and form parameters."""
    s = url
    if params:
        # Sort params alphabetically by key
        for key in sorted(params.keys()):
            val = params[key]
            # Convert bool/none to string
            val_str = "" if val is None else str(val)
            s += f"{key}{val_str}"

    computed = hmac.new(
        auth_token.encode("utf-8"),
        s.encode("utf-8"),
        hashlib.sha1
    ).digest()
    return base64.b64encode(computed).decode("utf-8")


def verify_twilio_request(url: str, params: Dict[str, Any], signature: Optional[str], auth_token: Optional[str] = None) -> bool:
    """Verify that an incoming webhook was genuinely sent by Twilio."""
    token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
    if not token:
        # If no Twilio auth token is configured, request cannot be validated
        return False
    if not signature:
        return False

    expected_sig = compute_twilio_signature(url, params, token)
    return hmac.compare_digest(signature, expected_sig)
