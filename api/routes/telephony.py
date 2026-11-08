"""MATRIX Telephony API Routes.
Provides endpoints for:
- Outbound calling on demand or on schedule ("call me in 10 minutes")
- Twilio Inbound Webhook (<Gather input="speech">)
- Twilio Speech Recognition & JARVIS Response
- In-App WebRTC/WebSocket zero-cost peer calling
- Call history and policy management
"""
from fastapi import APIRouter, HTTPException, Request, Form, Response, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time
from core.telephony.engine import telephony_engine, OutboundCallingPolicy
from core.brain import brain
from voice.text_to_speech.engine import tts_engine
from config.logging_config import get_logger

logger = get_logger("api.telephony")
router = APIRouter(prefix="/telephony", tags=["Telephony & Phone Calling"])


class CallMeRequest(BaseModel):
    reason: Optional[str] = "EXPLICIT_REQUEST"
    message: Optional[str] = "Greetings, this is MATRIX calling as requested."
    phone_number: Optional[str] = None


class ScheduleCallRequest(BaseModel):
    delay_minutes: float
    reason: Optional[str] = "EXPLICIT_REQUEST"
    message: Optional[str] = None


class PolicyUpdateRequest(BaseModel):
    verified_phone_number: Optional[str] = None
    pstn_calling_enabled: Optional[bool] = None
    max_calls_per_hour: Optional[int] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None


@router.post("/call-me")
async def call_user_phone(payload: CallMeRequest):
    """Trigger an immediate outbound call to the user's verified phone number or in-app client."""
    res = await telephony_engine.initiate_outbound_call(
        trigger_reason=payload.reason or "EXPLICIT_REQUEST",
        initial_message=payload.message,
        phone_override=payload.phone_number
    )
    return res


@router.post("/schedule-call")
async def schedule_call(payload: ScheduleCallRequest):
    """Schedule MATRIX to initiate a phone call in X minutes (e.g. 'call me in 10 minutes')."""
    delay_sec = max(1.0, payload.delay_minutes * 60)
    res = await telephony_engine.schedule_outbound_call(
        delay_seconds=delay_sec,
        reason=payload.reason or "EXPLICIT_REQUEST",
        message=payload.message
    )
    return res


@router.get("/policy")
async def get_calling_policy():
    """Retrieve active outbound calling policy and limits."""
    policy = telephony_engine.get_policy()
    return {
        "status": "OK",
        "policy": policy.model_dump(),
        "is_quiet_hours": telephony_engine.is_quiet_hours()
    }


@router.post("/policy")
async def update_calling_policy(payload: PolicyUpdateRequest):
    """Update verified phone number, quiet hours, and calling limits."""
    current = telephony_engine.get_policy()
    data = current.model_dump()

    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            data[k] = v

    new_policy = OutboundCallingPolicy(**data)
    telephony_engine.save_policy(new_policy)
    return {"status": "UPDATED", "policy": new_policy.model_dump()}


@router.get("/history")
async def get_call_history(limit: int = 20):
    """List recent inbound and outbound call logs."""
    history = telephony_engine.list_call_history(limit=limit)
    return {"status": "OK", "total": len(history), "calls": history}


# --- Twilio PSTN Webhook Endpoints ---

@router.post("/twilio/incoming")
async def twilio_incoming_call():
    """Twilio Voice Webhook: Answer incoming PSTN calls to the dedicated MATRIX number."""
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        '    <Say voice="Polly.Matthew">Greetings. This is MATRIX. How may I assist you today?</Say>\n'
        '    <Gather input="speech" action="/api/v1/telephony/twilio/speech" method="POST" timeout="4" speechTimeout="auto">\n'
        '        <Say voice="Polly.Matthew">Please state your directive or question.</Say>\n'
        '    </Gather>\n'
        '    <Say voice="Polly.Matthew">No speech detected. Call terminating. Standing by.</Say>\n'
        '</Response>'
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/speech")
async def twilio_speech_result(SpeechResult: Optional[str] = Form(None)):
    """Twilio Speech Gather Callback: Transcribes speech, processes via MATRIX Brain, speaks response."""
    user_speech = SpeechResult or ""
    logger.info(f"Twilio call speech recognized: '{user_speech}'")

    if not user_speech.strip():
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response>\n'
            '    <Say voice="Polly.Matthew">I did not catch that. Please repeat your instruction.</Say>\n'
            '    <Gather input="speech" action="/api/v1/telephony/twilio/speech" method="POST">\n'
            '    </Gather>\n'
            '</Response>'
        )
        return Response(content=twiml, media_type="application/xml")

    # Process through central Brain
    brain_res = await brain.process_user_request(session_id="sess_twilio_phone", user_prompt=user_speech)
    reply_text = brain_res.get("response", "Directive processed successfully, sir.")

    # Escape XML characters in response
    safe_reply = reply_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n'
        f'    <Say voice="Polly.Matthew">{safe_reply}</Say>\n'
        f'    <Gather input="speech" action="/api/v1/telephony/twilio/speech" method="POST" timeout="3" speechTimeout="auto">\n'
        f'        <Say voice="Polly.Matthew">Anything else, sir?</Say>\n'
        f'    </Gather>\n'
        f'    <Say voice="Polly.Matthew">Ending call. Standing by on all channels.</Say>\n'
        f'</Response>'
    )
    return Response(content=twiml, media_type="application/xml")
