"""MATRIX Device Pairing & Remote Access API Route.
Handles secure token pairing, token rotation, token expiration, authenticated remote commands,
live CPU/RAM telemetry, connection-health heartbeats, and device revocation between Windows 11 PC
and the Android companion app or remote clients.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
from datetime import datetime, timezone
from pathlib import Path
import psutil

from database.session import get_db
from database.models import Device as DeviceModel
from config.settings import settings
from config.logging_config import get_logger
from core.pairing_manager import pairing_manager, get_lan_ip, get_tailscale_ip
from core.device_auth import get_authenticated_device, generate_auth_token, hash_token
from core.brain import brain
from voice.text_to_speech.engine import tts_engine
from voice.speech_to_text.engine import stt_engine
from api.websocket.manager import ws_manager

logger = get_logger("api.devices")
router = APIRouter(prefix="/devices", tags=["Device Pairing & Remote Synchronization"])


class PairRequest(BaseModel):
    device_id: str
    name: str
    platform: str  # 'android', 'windows', 'web'
    pairing_token: str


class CreateTokenRequest(BaseModel):
    ttl_seconds: int = 300
    port: int = 8000


class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = "sess_remote_companion"
    synthesize_voice: Optional[bool] = False


class RotateTokenRequest(BaseModel):
    lifetime_days: Optional[int] = 30


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    name: str
    platform: str
    is_paired: bool
    last_seen_at: datetime
    created_at: datetime
    token_expires_at: Optional[datetime] = None


@router.post("/token", status_code=status.HTTP_200_OK)
async def create_token(payload: Optional[CreateTokenRequest] = None):
    """Generate a fresh pairing token and QR code protocol URI with detected LAN and Tailscale IPs."""
    ttl = payload.ttl_seconds if payload else 300
    port = payload.port if payload else 8000
    return pairing_manager.create_token(ttl_seconds=ttl, port=port)


@router.get("/tokens", status_code=status.HTTP_200_OK)
async def list_tokens():
    """List currently active, unconsumed pairing tokens."""
    return pairing_manager.list_active_tokens()


@router.post("/pair", status_code=status.HTTP_200_OK)
async def pair_device(payload: PairRequest, db: AsyncSession = Depends(get_db)):
    """Authorize and pair a new client device (such as the Android app).
    Returns a cryptographically secure 30-day bearer authentication token.
    """
    valid, message = pairing_manager.validate_and_consume(payload.pairing_token, payload.device_id)
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    stmt = select(DeviceModel).where(DeviceModel.device_id == payload.device_id)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    raw_token, token_hash, expires_at = generate_auth_token(lifetime_days=30)

    if existing:
        existing.is_paired = True
        existing.name = payload.name
        existing.platform = payload.platform
        existing.auth_token_hash = token_hash
        existing.token_expires_at = expires_at
        existing.last_seen_at = datetime.now(timezone.utc)
    else:
        new_device = DeviceModel(
            device_id=payload.device_id,
            name=payload.name,
            platform=payload.platform,
            is_paired=True,
            auth_token_hash=token_hash,
            token_expires_at=expires_at,
            last_seen_at=datetime.now(timezone.utc)
        )
        db.add(new_device)

    await db.commit()
    logger.info(f"Paired device '{payload.name}' ({payload.device_id}) successfully. Token expires at {expires_at.isoformat()}")

    return {
        "status": "PAIRED",
        "device_id": payload.device_id,
        "auth_token": raw_token,
        "expires_at": expires_at.isoformat(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "connection_state": "CONNECTED"
    }


@router.post("/command", status_code=status.HTTP_200_OK)
async def execute_remote_command(
    payload: CommandRequest,
    device: DeviceModel = Depends(get_authenticated_device)
):
    """Execute a remote directive through MATRIX Brain on behalf of an authenticated device.
    Optionally synthesizes speech and returns the audio file URL.
    """
    start_time = time.perf_counter()
    prompt = payload.command.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Command content cannot be empty.")

    sess_id = payload.session_id or f"sess_dev_{device.device_id[:8]}"
    brain_res = await brain.process_user_request(sess_id, prompt, active_agent="android")
    reply_text = brain_res.get("response", "")

    audio_url = None
    if payload.synthesize_voice and reply_text:
        try:
            audio_path = await tts_engine.speak(reply_text[:250])
            if audio_path and audio_path.exists():
                audio_url = f"/api/v1/voice/audio/{audio_path.name}"
        except Exception as e:
            logger.warning(f"Voice synthesis for remote command failed: {e}")

    latency = (time.perf_counter() - start_time) * 1000

    return {
        "status": "SUCCESS",
        "device_id": device.device_id,
        "session_id": sess_id,
        "reply": reply_text,
        "audio_url": audio_url,
        "plan_status": brain_res.get("plan_status", "EXECUTED"),
        "latency_ms": round(latency, 2),
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_device_status(device: DeviceModel = Depends(get_authenticated_device)):
    """Retrieve verified host CPU, RAM, disk metrics and connection health for an authenticated device."""
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    cpu_percent = psutil.cpu_percent(interval=None)

    from automation.scheduler.engine import background_scheduler
    active_tasks = len(await background_scheduler.list_tasks())

    return {
        "connection_state": "CONNECTED",
        "device_id": device.device_id,
        "device_name": device.name,
        "system_status": "NOMINAL" if vm.percent < 85 else "WARNING",
        "cpu_percent": cpu_percent,
        "ram_used_percent": vm.percent,
        "ram_available_mb": round(vm.available / (1024 * 1024), 1),
        "ram_total_mb": round(vm.total / (1024 * 1024), 1),
        "disk_used_percent": disk.percent,
        "active_background_tasks": active_tasks,
        "lan_ip": get_lan_ip(),
        "tailscale_ip": get_tailscale_ip(),
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@router.post("/heartbeat", status_code=status.HTTP_200_OK)
async def device_heartbeat(device: DeviceModel = Depends(get_authenticated_device)):
    """Lightweight connection health heartbeat to keep session alive and verify token validity."""
    return {
        "status": "PONG",
        "connection_state": "CONNECTED",
        "device_id": device.device_id,
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@router.post("/rotate-token", status_code=status.HTTP_200_OK)
async def rotate_device_token(
    payload: Optional[RotateTokenRequest] = None,
    device: DeviceModel = Depends(get_authenticated_device),
    db: AsyncSession = Depends(get_db)
):
    """Rotate the authentication token for an existing paired device."""
    lifetime = payload.lifetime_days if payload and payload.lifetime_days else 30
    raw_token, token_hash, expires_at = generate_auth_token(lifetime_days=lifetime)

    device.auth_token_hash = token_hash
    device.token_expires_at = expires_at
    device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Rotated token for device '{device.device_id}'. New expiry: {expires_at.isoformat()}")

    return {
        "status": "TOKEN_ROTATED",
        "device_id": device.device_id,
        "auth_token": raw_token,
        "expires_at": expires_at.isoformat(),
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@router.post("/voice", status_code=status.HTTP_200_OK)
async def remote_voice_interaction(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form("sess_remote_voice"),
    language: Optional[str] = Form(None),
    device: DeviceModel = Depends(get_authenticated_device)
):
    """End-to-end authenticated voice interaction from remote phone or microphone:
    AUDIO UPLOAD -> STT -> BRAIN -> TTS -> REPLY AUDIO URL
    """
    start_time = time.perf_counter()
    upload_dir = settings.cache_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"remote_voice_{int(time.time() * 1000)}_{file.filename}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 1. Transcribe speech
    stt_res = await stt_engine.transcribe(temp_path, language=language)
    user_text = stt_res.get("text", "").strip()

    if not user_text:
        return {
            "status": "ERROR",
            "device_id": device.device_id,
            "error": "No speech detected in audio file",
            "user_text": "",
            "reply_text": "I could not hear any speech. Please try speaking again.",
            "audio_url": None
        }

    # 2. Process via MATRIX Brain
    brain_res = await brain.process_user_request(session_id=session_id, user_prompt=user_text, active_agent="android")
    reply_text = brain_res.get("response", "")

    # 3. Synthesize speech
    audio_path = await tts_engine.speak(reply_text[:250])
    audio_url = f"/api/v1/voice/audio/{audio_path.name}" if (audio_path and audio_path.exists()) else None
    latency = (time.perf_counter() - start_time) * 1000

    return {
        "status": "OK",
        "device_id": device.device_id,
        "user_text": user_text,
        "reply_text": reply_text,
        "audio_url": audio_url,
        "session_id": session_id,
        "latency_ms": round(latency, 2)
    }


@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all registered and paired devices."""
    stmt = select(DeviceModel).order_by(DeviceModel.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/{device_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Revoke authorization for a specific device, invalidating its auth token immediately."""
    stmt = select(DeviceModel).where(DeviceModel.device_id == device_id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    device.is_paired = False
    device.auth_token_hash = None
    device.token_expires_at = None
    await db.commit()

    await ws_manager.broadcast({
        "type": "device_revoked",
        "payload": {
            "device_id": device_id,
            "connection_state": "REVOKED",
            "message": "Device authorization has been revoked."
        }
    })

    logger.warning(f"Revoked authorization for device '{device_id}'")
    return {
        "status": "REVOKED",
        "device_id": device_id,
        "connection_state": "REVOKED",
        "message": "Device authorization and authentication token revoked."
    }


@router.delete("/{device_id}", status_code=status.HTTP_200_OK)
async def delete_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently delete and uncouple a device record from the registry."""
    await ws_manager.broadcast({
        "type": "device_revoked",
        "payload": {
            "device_id": device_id,
            "connection_state": "REVOKED",
            "message": "Device has been uncoupled and deleted."
        }
    })
    stmt = delete(DeviceModel).where(DeviceModel.device_id == device_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found.")
    logger.info(f"Deleted device record '{device_id}'")
    return {
        "status": "REVOKED",
        "device_id": device_id,
        "connection_state": "REVOKED",
        "message": "Device deleted and removed from registry."
    }


@router.post("/stop-remote", status_code=status.HTTP_200_OK)
async def stop_remote_access(db: AsyncSession = Depends(get_db)):
    """Emergency cut-off: Revoke all paired remote devices and invalidate all pairing tokens."""
    pairing_manager.clear()
    stmt = select(DeviceModel)
    res = await db.execute(stmt)
    devices = res.scalars().all()

    count = 0
    for d in devices:
        d.is_paired = False
        d.auth_token_hash = None
        d.token_expires_at = None
        count += 1
    await db.commit()

    await ws_manager.broadcast({
        "type": "all_devices_revoked",
        "payload": {
            "connection_state": "REVOKED",
            "message": "Emergency cutoff: all remote authorizations terminated."
        }
    })

    logger.warning(f"EMERGENCY: Stopped all remote access. Revoked {count} devices.")
    return {
        "status": "REMOTE_ACCESS_STOPPED",
        "revoked_devices": count,
        "connection_state": "REVOKED",
        "message": "All remote mobile/web device authorizations and active tokens have been terminated."
    }


@router.get("/remote-status", status_code=status.HTTP_200_OK)
async def get_remote_status(db: AsyncSession = Depends(get_db)):
    """Retrieve current remote connectivity, paired devices count, LAN IP, and Tailscale IP."""
    lan_ip = get_lan_ip()
    ts_ip = get_tailscale_ip()

    stmt = select(DeviceModel).where(DeviceModel.is_paired == True)
    res = await db.execute(stmt)
    devices = res.scalars().all()

    return {
        "lan_ip": lan_ip,
        "tailscale_ip": ts_ip,
        "port": 8000,
        "paired_device_count": len(devices),
        "active_tokens": len(pairing_manager.list_active_tokens()),
        "remote_access_enabled": True,
        "tailscale_active": bool(ts_ip),
        "devices": [
            {
                "device_id": d.device_id,
                "name": d.name,
                "platform": d.platform,
                "is_paired": d.is_paired,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "token_expires_at": d.token_expires_at.isoformat() if d.token_expires_at else None
            }
            for d in devices
        ]
    }
