"""MATRIX Bland AI Telephony Integration Client.
Provides outbound conversational AI phone calling, live two-way voice agent orchestration,
call lifecycle monitoring, transcription retrieval, and termination using Bland AI API.

Bland AI Documentation: https://docs.bland.ai
Dashboard: https://v2.app.bland.ai
API Base: https://api.bland.ai (REST v1 endpoints with v2 Organization Key)
"""
import os
import re
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import httpx
from pydantic import BaseModel, Field

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("telephony.bland")

DEFAULT_MATRIX_PHONE_TASK = (
    "You are MATRIX, an advanced personal AI operating system and intelligent digital companion created for your operator. "
    "You speak in a calm, confident, polite, and sophisticated tone (similar to JARVIS). "
    "Opening objective: You are placing a test call to verify two-way audio communication and speech latency. "
    "Rules of engagement: "
    "1. Address the user with respect ('sir' or their name). "
    "2. Listen actively to what the user says and respond intelligently. "
    "3. If the user asks how you are doing or asks about your capabilities, explain that you are MATRIX running with real-time neural voice, local LLM intelligence, computer vision, and autonomous desktop control. "
    "4. If the user asks about the status of the telephony test, confirm that audio transmission, speech transcription, and neural synthesis are fully operational. "
    "5. Keep responses concise, natural, conversational, and direct (1-3 sentences per turn). Do not ramble. "
    "6. When the user signals that the test is complete or says goodbye, respond with a polite closing statement such as 'Understood, sir. Terminating test call now. Standing by on all local and mobile channels.' and end the call gracefully."
)

DEFAULT_OPENING_SENTENCE = (
    "Hello! This is MATRIX, your personal AI assistant. I'm calling to test our new phone communication system."
)


class BlandAccountInfo(BaseModel):
    status: str
    current_balance: float = 0.0
    total_calls: int = 0
    plan_name: Optional[str] = None
    allowed_countries: Optional[List[str]] = None
    sms_enabled: bool = False


class BlandTelephonyClient:
    """Manages Bland AI API communication, call dispatching, status checks, and call termination."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "bland_api_key", "") or os.getenv("BLAND_API_KEY", "")
        raw_url = base_url or getattr(settings, "bland_api_base_url", "") or os.getenv("BLAND_API_BASE_URL", "https://api.bland.ai")
        # Normalize base URL (strip trailing /v2 or /v1 to ensure standard routing)
        self._base_url = raw_url.rstrip("/").removesuffix("/v2").removesuffix("/v1")
        if not self._base_url:
            self._base_url = "https://api.bland.ai"

    @property
    def api_key(self) -> str:
        return self._api_key or os.getenv("BLAND_API_KEY", "")

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_configured(self) -> bool:
        """Check if Bland AI API key is configured and valid."""
        k = self.api_key
        return bool(k and (k.startswith("org_") or len(k) > 30))

    def get_masked_api_key(self) -> Optional[str]:
        k = self.api_key
        if not k:
            return None
        return k[:7] + "..." + k[-4:]

    def _get_headers(self) -> Dict[str, str]:
        return {
            "authorization": self.api_key,
            "Content-Type": "application/json"
        }

    async def get_account_info(self) -> Dict[str, Any]:
        """Fetch current Bland AI account details, wallet credits, and plan status."""
        if not self.is_configured():
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "error": "BLAND_API_KEY is not configured in .env."
            }

        url = f"{self._base_url}/v1/me"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=self._get_headers())
                if r.status_code == 200:
                    data = r.json()
                    billing = data.get("billing", {})
                    plan = data.get("plan", {})
                    return {
                        "success": True,
                        "status": data.get("status", "active"),
                        "current_balance": billing.get("current_balance", 0.0),
                        "refill_to": billing.get("refill_to"),
                        "total_calls": data.get("total_calls", 0),
                        "plan_name": plan.get("name") or "Pay-as-you-go / Trial",
                        "allowed_countries": plan.get("allowed_countries"),
                        "sms_enabled": plan.get("sms_enabled", False),
                        "raw": data
                    }
                else:
                    return {
                        "success": False,
                        "status": f"HTTP_{r.status_code}",
                        "error": r.text
                    }
        except Exception as e:
            logger.error(f"Error querying Bland AI account info: {e}")
            return {
                "success": False,
                "status": "ERROR",
                "error": str(e)
            }

    def parse_country_code(self, phone: str) -> Dict[str, Any]:
        """Inspect destination phone number format and country code."""
        clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
        is_e164 = bool(re.match(r"^\+[1-9]\d{8,14}$", clean))
        country_name = "Unknown"
        is_international = True

        if clean.startswith("+1"):
            country_name = "United States / Canada"
            is_international = False
        elif clean.startswith("+91"):
            country_name = "India"
            is_international = True
        elif clean.startswith("+44"):
            country_name = "United Kingdom"
            is_international = True
        elif clean.startswith("+61"):
            country_name = "Australia"
            is_international = True

        return {
            "clean_number": clean,
            "is_valid_e164": is_e164,
            "country_name": country_name,
            "is_international": is_international
        }

    async def verify_target_capabilities(self, phone_number: str) -> Dict[str, Any]:
        """Pre-flight check: Verify if target number is callable and if account has necessary permissions/credits."""
        parsed = self.parse_country_code(phone_number)
        if not parsed["is_valid_e164"]:
            return {
                "callable": False,
                "reason": f"Phone number '{phone_number}' is not in valid E.164 format (+[country_code][number]).",
                "parsed": parsed
            }

        account = await self.get_account_info()
        if not account.get("success"):
            return {
                "callable": False,
                "reason": f"Could not authenticate with Bland AI API: {account.get('error')}",
                "account": account,
                "parsed": parsed
            }

        balance = account.get("current_balance", 0.0)
        # Bland AI international calling requirement:
        # Accounts require at least $5 of purchased credits or auto-recharge for international calls outside US/CA.
        warnings = []
        if parsed["is_international"]:
            if balance < 0.20:
                return {
                    "callable": False,
                    "reason": f"Insufficient Bland AI credits (Current balance: ${balance:.2f}). International calls require credits.",
                    "balance": balance,
                    "parsed": parsed
                }
            if balance < 5.0:
                warnings.append(
                    f"Account balance is ${balance:.2f}. Bland AI international policy specifies: 'To place international calls, you must buy at least $5 of credits in your dashboard under Billing or have auto-recharge turned on.'"
                )

        return {
            "callable": True,
            "balance": balance,
            "parsed": parsed,
            "account_status": account.get("status"),
            "warnings": warnings
        }

    async def send_call(
        self,
        phone_number: str,
        task: Optional[str] = None,
        first_sentence: Optional[str] = None,
        voice: Optional[str] = None,
        webhook_url: Optional[str] = None,
        max_duration: int = 5,
        record: bool = True,
        wait_for_greeting: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatch an outbound AI phone call via Bland AI API."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Bland AI API key not configured. Set BLAND_API_KEY in .env."
            }

        clean_number = re.sub(r"[\s\-\(\)]", "", phone_number.strip())
        task_prompt = task or DEFAULT_MATRIX_PHONE_TASK
        opening = first_sentence or DEFAULT_OPENING_SENTENCE

        payload: Dict[str, Any] = {
            "phone_number": clean_number,
            "task": task_prompt,
            "first_sentence": opening,
            "voice": voice or "ryan",
            "model": "enhanced",
            "record": record,
            "reduce_latency": True,
            "max_duration": max_duration,
            "wait_for_greeting": wait_for_greeting,
            "metadata": metadata or {}
        }

        if webhook_url:
            payload["webhook"] = webhook_url

        url = f"{self._base_url}/v1/calls"
        logger.info(f"Dispatching Bland AI call to {clean_number} (voice: {payload['voice']})...")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                resp_json = resp.json() if resp.status_code in [200, 201, 400, 402, 403, 404, 429] else {}

                if resp.status_code in [200, 201] and resp_json.get("status") == "success":
                    call_id = resp_json.get("call_id")
                    logger.info(f"Bland AI call successfully dispatched: call_id={call_id}")
                    return {
                        "success": True,
                        "call_id": call_id,
                        "status": "DISPATCHED",
                        "provider": "bland_ai",
                        "phone_number": clean_number,
                        "message": resp_json.get("message", "Call dispatched successfully."),
                        "details": resp_json
                    }
                else:
                    err_msg = resp_json.get("message") or resp.text
                    logger.warning(f"Bland AI call dispatch failed (HTTP {resp.status_code}): {err_msg}")
                    return {
                        "success": False,
                        "status": f"HTTP_{resp.status_code}",
                        "error": err_msg,
                        "details": resp_json
                    }
        except Exception as e:
            logger.error(f"Error calling Bland AI endpoint: {e}")
            return {
                "success": False,
                "status": "CONNECTION_ERROR",
                "error": str(e)
            }

    async def get_call_details(self, call_id: str) -> Dict[str, Any]:
        """Query status, live transcript, duration, and recording for a specific call."""
        if not self.is_configured():
            return {"success": False, "error": "Bland AI API key not configured."}

        url = f"{self._base_url}/v1/calls/{call_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "call_id": call_id,
                        "status": data.get("status"),
                        "call_length": data.get("call_length", 0.0),
                        "completed": data.get("completed", False),
                        "answered_by": data.get("answered_by"),
                        "recording_url": data.get("recording_url"),
                        "summary": data.get("summary"),
                        "transcripts": data.get("transcripts", []),
                        "concatenated_transcript": data.get("concatenated_transcript", ""),
                        "raw": data
                    }
                else:
                    return {
                        "success": False,
                        "status": f"HTTP_{resp.status_code}",
                        "error": resp.text
                    }
        except Exception as e:
            return {"success": False, "status": "ERROR", "error": str(e)}

    async def stop_call(self, call_id: str) -> Dict[str, Any]:
        """Terminate an ongoing phone call immediately."""
        if not self.is_configured():
            return {"success": False, "error": "Bland AI API key not configured."}

        url = f"{self._base_url}/v1/calls/{call_id}/stop"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._get_headers(), json={})
                data = resp.json() if resp.status_code in [200, 201, 400] else {}
                return {
                    "success": resp.status_code in [200, 201],
                    "call_id": call_id,
                    "status": "STOPPED" if resp.status_code in [200, 201] else f"HTTP_{resp.status_code}",
                    "message": data.get("message", resp.text)
                }
        except Exception as e:
            return {"success": False, "status": "ERROR", "error": str(e)}

    async def list_recent_calls(self, limit: int = 15) -> List[Dict[str, Any]]:
        """List call logs from Bland AI."""
        if not self.is_configured():
            return []

        url = f"{self._base_url}/v1/calls"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    calls = data.get("calls", [])
                    return calls[:limit]
        except Exception as e:
            logger.warning(f"Error fetching Bland calls: {e}")
        return []

    async def list_voices(self, limit: int = 25) -> List[Dict[str, Any]]:
        """List available Bland AI voices."""
        if not self.is_configured():
            return []

        url = f"{self._base_url}/v1/voices"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("voices", [])[:limit]
        except Exception as e:
            logger.warning(f"Error fetching Bland voices: {e}")
        return []


# Global singleton instance
bland_client = BlandTelephonyClient()
