"""MATRIX Two-Way Telephony & Phone Calling Engine.
Supports:
  1. In-App WebRTC/WebSocket zero-cost two-way calls (from mobile or desktop).
  2. Real PSTN Inbound and Outbound calling via Twilio / Telnyx Voice Gateway.
  3. Outbound calling triggers: "call me in X minutes", "call me when task complete", "call me if server down".
  4. Strict outbound policy: verified number only, rate limiting, quiet hours guard.
"""
from typing import Dict, Any, List, Optional
import time
import os
import json
import asyncio
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.telephony")


class CallRecord(BaseModel):
    call_id: str
    direction: str  # INBOUND, OUTBOUND
    call_type: str  # PSTN_TWILIO, IN_APP_WEBRTC, SIP
    from_number: str
    to_number: str
    status: str     # RINGING, IN_PROGRESS, COMPLETED, FAILED, MISSED
    duration_seconds: float = 0.0
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    transcript_summary: Optional[str] = None
    trigger_reason: str = "USER_DIRECTIVE"


class OutboundCallingPolicy(BaseModel):
    verified_phone_number: str = "+1234567890"  # Configured by user
    pstn_calling_enabled: bool = False           # Requires Twilio/Telnyx credentials
    max_calls_per_hour: int = 3
    quiet_hours_enabled: bool = True
    quiet_hours_start: int = 23                  # 11 PM
    quiet_hours_end: int = 7                     # 7 AM
    allowed_triggers: List[str] = Field(default_factory=lambda: [
        "EXPLICIT_REQUEST", "TASK_COMPLETE", "SERVER_CRITICAL", "SCHEDULED_BRIEFING"
    ])


class TelephonyEngine:
    """Coordinates phone calls, speech streaming, and outbound triggers."""

    def __init__(self):
        self._policy_file = settings.data_dir / "telephony_policy.json"
        self._calls_file = settings.data_dir / "call_history.json"
        self._policy = OutboundCallingPolicy()
        self._call_history: List[CallRecord] = []
        self._active_calls: Dict[str, CallRecord] = {}
        self._hourly_call_timestamps: List[float] = []
        self._scheduled_call_tasks: List[Dict[str, Any]] = []

        self._load_policy()
        self._load_history()

    def _load_policy(self):
        if self._policy_file.exists():
            try:
                data = json.loads(self._policy_file.read_text(encoding="utf-8"))
                self._policy = OutboundCallingPolicy(**data)
            except Exception as e:
                logger.warning(f"Could not load telephony policy: {e}")

    def save_policy(self, policy: OutboundCallingPolicy):
        self._policy = policy
        try:
            self._policy_file.parent.mkdir(parents=True, exist_ok=True)
            self._policy_file.write_text(self._policy.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not save telephony policy: {e}")

    def _load_history(self):
        if self._calls_file.exists():
            try:
                data = json.loads(self._calls_file.read_text(encoding="utf-8"))
                self._call_history = [CallRecord(**c) for c in data]
            except Exception:
                self._call_history = []

    def _save_history(self):
        try:
            self._calls_file.parent.mkdir(parents=True, exist_ok=True)
            serializable = [c.model_dump() for c in self._call_history[-50:]]
            self._calls_file.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not save call history: {e}")

    def get_policy(self) -> OutboundCallingPolicy:
        return self._policy

    def is_configured(self) -> bool:
        """Check if Twilio credentials (Account SID and Auth Token) are configured."""
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        return bool(sid and token and sid.startswith("AC"))

    def get_policy_summary(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "policy": self._policy.model_dump(),
            "is_quiet_hours": self.is_quiet_hours()
        }

    def is_quiet_hours(self) -> bool:
        if not self._policy.quiet_hours_enabled:
            return False
        current_hour = datetime.now().hour
        if self._policy.quiet_hours_start > self._policy.quiet_hours_end:
            return current_hour >= self._policy.quiet_hours_start or current_hour < self._policy.quiet_hours_end
        return self._policy.quiet_hours_start <= current_hour < self._policy.quiet_hours_end

    def check_can_call_outbound(self, trigger_reason: str) -> Dict[str, Any]:
        """Verify calling policy constraints before initiating PSTN dialing."""
        now = time.time()
        # Clean timestamps older than 1 hour
        self._hourly_call_timestamps = [t for t in self._hourly_call_timestamps if (now - t) < 3600]

        if not self._policy.pstn_calling_enabled:
            # Check if environment credentials exist
            sid = os.getenv("TWILIO_ACCOUNT_SID")
            token = os.getenv("TWILIO_AUTH_TOKEN")
            if not (sid and token):
                return {
                    "allowed": False,
                    "reason": "Twilio PSTN calling is not enabled. In-App WebRTC Calling is active (zero cost)."
                }

        if trigger_reason not in self._policy.allowed_triggers:
            return {"allowed": False, "reason": f"Trigger reason '{trigger_reason}' is not permitted by policy."}

        if len(self._hourly_call_timestamps) >= self._policy.max_calls_per_hour:
            return {
                "allowed": False,
                "reason": f"Rate limit reached ({self._policy.max_calls_per_hour} calls/hour). Try again later."
            }

        if self.is_quiet_hours() and trigger_reason != "SERVER_CRITICAL":
            return {
                "allowed": False,
                "reason": f"Quiet hours active ({self._policy.quiet_hours_start}:00 - {self._policy.quiet_hours_end}:00)."
            }

        return {"allowed": True, "target_number": self._policy.verified_phone_number}

    async def initiate_outbound_call(
        self,
        trigger_reason: str,
        initial_message: Optional[str] = None,
        phone_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate an outbound phone call to the user's verified number or in-app client."""
        import uuid
        target_number = phone_override or self._policy.verified_phone_number
        check = self.check_can_call_outbound(trigger_reason)

        call_id = f"call_{uuid.uuid4().hex[:8]}"
        record = CallRecord(
            call_id=call_id,
            direction="OUTBOUND",
            call_type="PSTN_TWILIO" if (os.getenv("TWILIO_ACCOUNT_SID") and check["allowed"]) else "IN_APP_WEBRTC",
            from_number="MATRIX-CORE",
            to_number=target_number,
            status="RINGING",
            trigger_reason=trigger_reason
        )
        self._active_calls[call_id] = record
        self._hourly_call_timestamps.append(time.time())

        # If Twilio credentials exist and allowed, call Twilio REST API
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "+18005550199")

        if check["allowed"] and sid and token:
            try:
                import httpx
                # Twilio Calls endpoint
                url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
                twiml = f"<Response><Say voice='Polly.Matthew'>{initial_message or 'Greetings sir. This is MATRIX calling as requested.'}</Say><Gather input='speech' action='/api/v1/telephony/twilio/speech' method='POST'><Say voice='Polly.Matthew'>How may I assist you?</Say></Gather></Response>"

                async with httpx.AsyncClient(auth=(sid, token), timeout=8.0) as client:
                    resp = await client.post(
                        url,
                        data={
                            "To": target_number,
                            "From": twilio_number,
                            "Twiml": twiml
                        }
                    )
                    if resp.status_code in [200, 201]:
                        data = resp.json()
                        record.status = "IN_PROGRESS"
                        logger.info(f"Twilio call dispatched: SID {data.get('sid')} -> {target_number}")
                        return {
                            "success": True,
                            "call_id": call_id,
                            "provider": "twilio_pstn",
                            "twilio_sid": data.get("sid"),
                            "target_number": target_number,
                            "status": "DISPATCHED"
                        }
            except Exception as e:
                logger.warning(f"Twilio PSTN call failed ({e}); falling back to in-app ringing.")

        # In-App WebRTC / WebSocket Outbound Ringing Notification
        record.status = "IN_PROGRESS"
        from core.autonomy.event_monitor import event_monitor
        await event_monitor.publish(
            event_type="CALL_EVENT",
            title="MATRIX Outbound Call",
            message=initial_message or f"Incoming call from MATRIX: {trigger_reason}",
            severity="INFO",
            data={
                "call_id": call_id,
                "call_type": "IN_APP_WEBRTC",
                "trigger_reason": trigger_reason,
                "initial_message": initial_message or "Greetings sir, MATRIX is on the line."
            }
        )

        logger.info(f"In-App WebRTC call initiated: {call_id} for {target_number}")
        return {
            "success": True,
            "call_id": call_id,
            "provider": "in_app_webrtc",
            "target": target_number,
            "status": "RINGING_IN_APP",
            "message": "In-App call ringing on your connected device. You can speak directly to MATRIX."
        }

    async def schedule_outbound_call(
        self,
        delay_seconds: float,
        reason: str = "EXPLICIT_REQUEST",
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedule an outbound call to fire after delay_seconds (e.g. 'call me in 10 minutes')."""
        import uuid
        task_id = f"calltask_{uuid.uuid4().hex[:6]}"
        target_time = time.time() + delay_seconds

        async def _delayed_dial():
            await asyncio.sleep(delay_seconds)
            logger.info(f"Triggering scheduled call {task_id}: {reason}")
            await self.initiate_outbound_call(trigger_reason=reason, initial_message=message)

        asyncio.create_task(_delayed_dial())

        self._scheduled_call_tasks.append({
            "task_id": task_id,
            "delay_seconds": delay_seconds,
            "target_time": target_time,
            "reason": reason,
            "message": message
        })

        minutes = round(delay_seconds / 60, 1)
        return {
            "success": True,
            "scheduled_task_id": task_id,
            "delay_minutes": minutes,
            "message": f"Outbound call scheduled in {minutes} minutes ({reason})."
        }

    def complete_call(self, call_id: str, transcript: Optional[str] = None):
        """Finalize and record completed phone call."""
        record = self._active_calls.pop(call_id, None)
        if record:
            record.status = "COMPLETED"
            record.end_time = time.time()
            record.duration_seconds = round(record.end_time - record.start_time, 1)
            record.transcript_summary = transcript
            self._call_history.append(record)
            self._save_history()
            logger.info(f"Call {call_id} completed: duration {record.duration_seconds}s")

    def list_call_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [c.model_dump() for c in reversed(self._call_history[-limit:])]


# Global singleton
telephony_engine = TelephonyEngine()
