"""MATRIX Telephony API Routes.
Provides endpoints for:
- Outbound calling on demand or on schedule ("call me in 10 minutes")
- Twilio Inbound Webhook (<Gather input="speech">)
- Twilio Speech Recognition & JARVIS Response
- In-App WebRTC/WebSocket zero-cost peer calling
- Call history and policy management
"""
from fastapi import APIRouter, HTTPException, Request, Form, Response, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time
import os
import hmac
from config.settings import settings
from core.telephony.engine import telephony_engine, OutboundCallingPolicy, is_valid_phone
from core.telephony.twilio_security import verify_twilio_request
from core.telephony.bland_client import bland_client, DEFAULT_MATRIX_PHONE_TASK, DEFAULT_OPENING_SENTENCE
from core.brain import brain
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


@router.get("/setup-wizard")
async def telephony_setup_wizard():
    """Twilio setup wizard, verification status, and configuration checklist."""
    return telephony_engine.get_setup_wizard()


@router.post("/policy")
async def update_calling_policy(payload: PolicyUpdateRequest):
    """Update verified phone number, quiet hours, and calling limits."""
    if payload.verified_phone_number is not None:
        if not is_valid_phone(payload.verified_phone_number):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phone number '{payload.verified_phone_number}'. Must be valid international E.164 format (e.g. +14155552671) and cannot be a dummy number."
            )

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
async def twilio_incoming_call(request: Request):
    """Twilio Voice Webhook: Answer incoming PSTN calls to the dedicated MATRIX number."""
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    if twilio_token:
        sig = request.headers.get("X-Twilio-Signature")
        url = str(request.url)
        form_data = await request.form()
        if not verify_twilio_request(url, dict(form_data), sig, twilio_token):
            logger.warning(f"Twilio webhook signature verification failed for incoming call from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

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
async def twilio_speech_result(request: Request, SpeechResult: Optional[str] = Form(None)):
    """Twilio Speech Gather Callback: Transcribes speech, processes via MATRIX Brain, speaks response."""
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    if twilio_token:
        sig = request.headers.get("X-Twilio-Signature")
        url = str(request.url)
        form_data = await request.form()
        if not verify_twilio_request(url, dict(form_data), sig, twilio_token):
            logger.warning("Twilio webhook signature verification failed for speech result")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

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


@router.post("/twilio/status")
async def twilio_call_status(
    request: Request,
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    CallDuration: Optional[str] = Form(None)
):
    """Twilio Call Status Callback: Updates call lifecycle status and duration."""
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    if twilio_token:
        sig = request.headers.get("X-Twilio-Signature")
        url = str(request.url)
        form_data = await request.form()
        if not verify_twilio_request(url, dict(form_data), sig, twilio_token):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    if CallSid and CallStatus:
        duration = float(CallDuration) if CallDuration and CallDuration.isdigit() else None
        telephony_engine.update_call_status(CallSid, CallStatus, duration)
        logger.info(f"Twilio call status callback: SID {CallSid} -> {CallStatus} ({duration}s)")

    return Response(content="<Response/>", media_type="application/xml")


class TwilioValidateRequest(BaseModel):
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    twilio_number: Optional[str] = None


class TwilioTestCallRequest(BaseModel):
    target_number: str
    confirm_destination: bool = False


@router.post("/twilio/validate-credentials")
async def validate_twilio_creds(payload: TwilioValidateRequest):
    """Validate Twilio account SID, auth token, and phone number without placing a call."""
    return telephony_engine.validate_twilio_credentials(
        account_sid=payload.account_sid,
        auth_token=payload.auth_token,
        twilio_number=payload.twilio_number
    )


@router.post("/twilio/test-call")
async def execute_twilio_test_call(payload: TwilioTestCallRequest):
    """Initiate a test call via Twilio with explicit destination confirmation."""
    return await telephony_engine.initiate_twilio_test_call(
        target_number=payload.target_number,
        confirm_destination=payload.confirm_destination
    )


@router.get("/twilio/usage")
async def get_twilio_usage():
    """Retrieve Twilio call usage metrics, estimated costs, and spending limits."""
    return telephony_engine.get_twilio_usage()


@router.post("/twilio/calls/{call_sid}/terminate")
async def terminate_twilio_call_endpoint(call_sid: str):
    """Terminate an in-progress Twilio call."""
    return await telephony_engine.terminate_twilio_call(call_sid)


# --- Bland AI Telephony Endpoints ---

class BlandCallRequest(BaseModel):
    phone_number: Optional[str] = "+919193002500"
    task: Optional[str] = None
    first_sentence: Optional[str] = None
    voice: Optional[str] = "ryan"
    max_duration: Optional[int] = 5
    wait_for_greeting: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


@router.get("/bland/account")
async def get_bland_account():
    """Retrieve Bland AI account status, wallet credits balance, and active plan details."""
    res = await bland_client.get_account_info()
    return res


@router.get("/bland/capabilities")
async def check_bland_capabilities(phone_number: str = "+919193002500"):
    """Verify Bland AI calling capabilities and balance requirements for a destination number."""
    res = await bland_client.verify_target_capabilities(phone_number)
    return res


@router.get("/bland/voices")
async def list_bland_voices(limit: int = 25):
    """List available Bland AI conversational voice models."""
    voices = await bland_client.list_voices(limit=limit)
    return {"total": len(voices), "voices": voices}


@router.get("/bland/calls")
async def list_bland_calls(limit: int = 15):
    """Retrieve recent call records dispatched via Bland AI."""
    calls = await bland_client.list_recent_calls(limit=limit)
    return {"total": len(calls), "calls": calls}


@router.get("/bland/calls/{call_id}")
async def get_bland_call_details(call_id: str):
    """Query live call status, transcript, recording, and duration."""
    res = await bland_client.get_call_details(call_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Call not found"))
    return res


@router.post("/bland/calls/{call_id}/stop")
async def stop_bland_call(call_id: str):
    """Immediately terminate an active Bland AI phone call."""
    res = await bland_client.stop_call(call_id)
    return res


@router.post("/bland/call")
async def dispatch_bland_call(payload: BlandCallRequest):
    """Initiate an outbound AI phone call to destination number via Bland AI."""
    target_number = payload.phone_number or "+919193002500"
    if not is_valid_phone(target_number):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phone number '{target_number}'. Must be in international E.164 format (e.g. +919193002500)."
        )

    # Check capabilities and balance
    caps = await bland_client.verify_target_capabilities(target_number)
    if not caps.get("callable"):
        raise HTTPException(status_code=400, detail=caps.get("reason", "Target number not callable."))

    # Dispatch call
    res = await bland_client.send_call(
        phone_number=target_number,
        task=payload.task or DEFAULT_MATRIX_PHONE_TASK,
        first_sentence=payload.first_sentence or DEFAULT_OPENING_SENTENCE,
        voice=payload.voice or "ryan",
        max_duration=payload.max_duration or 5,
        wait_for_greeting=payload.wait_for_greeting or False,
        metadata=payload.metadata or {"source": "matrix_api"}
    )

    if not res.get("success"):
        raise HTTPException(status_code=502, detail=res.get("error", "Bland AI call dispatch failed."))

    # Record in telephony engine
    call_id = f"bland_{res.get('call_id')}"
    from core.telephony.engine import CallRecord
    record = CallRecord(
        call_id=call_id,
        direction="OUTBOUND",
        call_type="AI_BLAND",
        from_number="MATRIX-BLAND",
        to_number=target_number,
        status="DISPATCHED",
        trigger_reason="EXPLICIT_BLAND_REQUEST",
        bland_call_id=res.get("call_id")
    )
    telephony_engine._active_calls[call_id] = record
    telephony_engine._hourly_call_timestamps.append(time.time())

    return res


@router.post("/bland/webhook")
async def bland_call_webhook(request: Request):
    """Webhook callback endpoint for Bland AI call completed and status events.

    Bland does not sign its callbacks, so a shared secret is required. When
    MATRIX_BLAND_WEBHOOK_SECRET is unset the endpoint refuses all events (503)
    instead of trusting unauthenticated callers.
    """
    expected_secret = settings.bland_webhook_secret
    if not expected_secret:
        logger.error("Bland webhook rejected: MATRIX_BLAND_WEBHOOK_SECRET is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bland webhook authentication is not configured (set MATRIX_BLAND_WEBHOOK_SECRET).",
        )

    supplied_secret = (
        request.headers.get("X-Matrix-Webhook-Secret")
        or request.query_params.get("secret")
        or ""
    )
    if not hmac.compare_digest(supplied_secret, expected_secret):
        logger.warning("Bland webhook rejected: invalid shared secret.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")

    try:
        data = await request.json()
    except Exception:
        data = {}

    call_id = data.get("call_id")
    call_status = str(data.get("status", "completed")).upper()
    duration = data.get("call_length")
    transcript = data.get("concatenated_transcript") or data.get("summary")
    recording_url = data.get("recording_url")

    logger.info(f"Bland AI Webhook: Call {call_id} -> {call_status} (duration: {duration}s)")

    if call_id:
        telephony_engine.update_call_status(call_id, call_status, duration)
        for record in telephony_engine._call_history:
            if record.bland_call_id == call_id or record.call_id == f"bland_{call_id}":
                record.transcript_summary = transcript
                record.recording_url = recording_url
                telephony_engine._save_history()
                break

    return {"status": "RECEIVED", "call_id": call_id}

