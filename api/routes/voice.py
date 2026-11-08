"""MATRIX Voice System API Route.
Provides endpoints for speech synthesis, microphone audio transcription,
hands-free autonomous conversation, wake-word sensitivity tuning,
audio file serving, device discovery, and immediate interruption controls.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import time
import asyncio
import numpy as np

from voice.text_to_speech.engine import tts_engine
from voice.speech_to_text.engine import stt_engine
from voice.wake_word.engine import wake_word_detector
from voice.snap_detector import snap_detector
from voice.mic_listener import mic_listener
from voice.vad.engine import vad_engine
from voice.conversation.manager import hands_free_manager, ConversationMode, HandsFreeState
from core.brain import brain
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("api.voice")
router = APIRouter(prefix="/voice", tags=["Voice System"])


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class ToggleListenRequest(BaseModel):
    enable: bool


class ModeRequest(BaseModel):
    mode: ConversationMode


class SensitivityRequest(BaseModel):
    sensitivity: float


class VADSensitivityRequest(BaseModel):
    silence_duration_ms: Optional[int] = 1000
    speech_threshold: Optional[float] = 0.5


class RecordRequest(BaseModel):
    duration_seconds: float = 3.0
    language: Optional[str] = None


class DeviceSelectRequest(BaseModel):
    device_index: int


class PlaybackTimingRequest(BaseModel):
    speech_rate: Optional[str] = "+0%"
    post_pause_ms: Optional[int] = 350


@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve a synthesized speech audio file to the frontend UI or Android client."""
    safe_name = Path(filename).name
    candidate_paths = [
        settings.cache_dir / "voice" / safe_name,
        settings.cache_dir / "audio" / safe_name,
    ]
    for p in candidate_paths:
        if p.exists() and p.is_file():
            media_type = "audio/mpeg" if p.suffix.lower() == ".mp3" else "audio/wav"
            return FileResponse(path=str(p), media_type=media_type, filename=safe_name)

    raise HTTPException(status_code=404, detail="Audio file not found.")


@router.post("/speak")
async def speak_text(payload: SpeakRequest):
    """Synthesize text to speech and return the generated audio file."""
    audio_path = await tts_engine.speak(payload.text, voice_override=payload.voice)
    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=500, detail="Speech synthesis failed or was stopped.")

    media_type = "audio/mpeg" if audio_path.suffix == ".mp3" else "audio/wav"
    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=audio_path.name
    )


@router.post("/stop")
async def stop_speaking():
    """Immediately abort speech synthesis and interrupt hands-free execution."""
    await hands_free_manager.interrupt()
    tts_engine.stop()
    return {"status": "OK", "stopped": True}


@router.get("/hands-free/status")
async def get_hands_free_status():
    """Retrieve live status of the continuous hands-free voice loop."""
    return {
        "status": "OK",
        "state": hands_free_manager.state.value,
        "mode": hands_free_manager.mode.value,
        "wake_words": ["matrix", "snap"],
        "wake_word_sensitivity": wake_word_detector.sensitivity,
        "silence_duration_ms": vad_engine.silence_duration_ms,
        "speech_threshold": vad_engine.speech_threshold,
        "is_speaking": tts_engine.is_speaking,
        "last_transcript": hands_free_manager.last_transcript,
        "last_response": hands_free_manager.last_response
    }


@router.post("/hands-free/mode")
async def set_hands_free_mode(payload: ModeRequest):
    """Update hands-free mode: 'continuous', 'wake_word_only', 'push_to_talk', or 'privacy_pause'."""
    hands_free_manager.set_mode(payload.mode)
    return {
        "status": "OK",
        "mode": hands_free_manager.mode.value,
        "state": hands_free_manager.state.value
    }


@router.post("/hands-free/interrupt")
async def interrupt_hands_free():
    """Immediately interrupt ongoing speech or task."""
    await hands_free_manager.interrupt()
    return {
        "status": "OK",
        "interrupted": True,
        "state": hands_free_manager.state.value
    }


@router.post("/wake-word/sensitivity")
async def set_wake_word_sensitivity(payload: SensitivityRequest):
    """Adjust wake-word detection sensitivity threshold (0.1 to 0.95)."""
    wake_word_detector.set_sensitivity(payload.sensitivity)
    return {
        "status": "OK",
        "sensitivity": wake_word_detector.sensitivity
    }


@router.post("/vad/sensitivity")
async def set_vad_sensitivity(payload: VADSensitivityRequest):
    """Adjust end-of-speech silence duration (ms) and speech probability threshold."""
    if payload.silence_duration_ms is not None:
        vad_engine.silence_duration_ms = max(500, min(3000, payload.silence_duration_ms))
    if payload.speech_threshold is not None:
        vad_engine.speech_threshold = max(0.1, min(0.9, payload.speech_threshold))

    return {
        "status": "OK",
        "silence_duration_ms": vad_engine.silence_duration_ms,
        "speech_threshold": vad_engine.speech_threshold
    }


@router.post("/stream-chunk")
async def stream_audio_chunk(
    file: UploadFile = File(...)
):
    """Process incoming audio chunk from Web Audio API / browser microphone."""
    content = await file.read()
    # Decode audio into 16kHz PCM
    try:
        import soundfile as sf
        import io
        data, sr = sf.read(io.BytesIO(content), dtype='int16')
        if data.ndim > 1:
            data = data[:, 0]
        result = await hands_free_manager.process_audio_chunk(data, source="web_audio")
        return {"status": "OK", "result": result}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """Transcribe an uploaded audio recording using Faster-Whisper."""
    upload_dir = settings.cache_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"upload_{int(time.time() * 1000)}_{file.filename}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    result = await stt_engine.transcribe(temp_path, language=language)
    return {
        "status": "OK",
        "transcription": result
    }


@router.post("/chat-voice")
async def chat_voice_loop(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form("sess_voice_default"),
    language: Optional[str] = Form(None)
):
    """Full End-to-End Voice Cycle:
    USER SPEECH -> STT -> MATRIX BRAIN -> TTS -> ASSISTANT AUDIO + TRANSCRIPT
    """
    start_time = time.perf_counter()
    upload_dir = settings.cache_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"voice_in_{int(time.time() * 1000)}_{file.filename}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 1. Speech to Text
    stt_res = await stt_engine.transcribe(temp_path, language=language)
    user_text = stt_res.get("text", "").strip()

    if not user_text:
        return {
            "status": "ERROR",
            "error": "No speech detected in audio file",
            "user_text": "",
            "reply_text": "I could not hear any speech. Please try speaking again.",
            "audio_url": None
        }

    # 2. Process through MATRIX Brain
    brain_res = await brain.process_user_request(session_id=session_id, user_prompt=user_text)
    reply_text = brain_res.get("response", "")

    # 3. Text to Speech
    audio_path = await tts_engine.speak(reply_text)
    audio_url = f"/api/v1/voice/audio/{audio_path.name}" if (audio_path and audio_path.exists()) else None

    total_latency = (time.perf_counter() - start_time) * 1000

    return {
        "status": "OK",
        "user_text": user_text,
        "reply_text": reply_text,
        "audio_url": audio_url,
        "session_id": session_id,
        "plan_status": brain_res.get("plan_status"),
        "latency_ms": round(total_latency, 2)
    }


@router.post("/record-and-transcribe")
async def record_and_transcribe(payload: RecordRequest):
    """Record audio directly from physical PC microphone and transcribe it."""
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Audio dependencies missing: {e}")

    sr = 16000
    duration = max(1.0, min(10.0, payload.duration_seconds))
    
    def _record():
        recording = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='float32')
        sd.wait()
        return recording

    recording = await asyncio.to_thread(_record)

    out_dir = settings.cache_dir / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_wav = out_dir / f"mic_{int(time.time() * 1000)}.wav"
    sf.write(str(temp_wav), recording, sr)

    result = await stt_engine.transcribe(temp_wav, language=payload.language)
    return {
        "status": "OK",
        "duration": duration,
        "audio_file": str(temp_wav),
        "transcription": result
    }


@router.post("/toggle-listen")
async def toggle_listening(payload: ToggleListenRequest):
    """Enable or disable wake-word continuous listening."""
    if payload.enable:
        wake_word_detector.start_listening()
    else:
        wake_word_detector.stop_listening()

    return {
        "status": "OK",
        "listening": wake_word_detector.is_listening
    }


@router.get("/status")
async def voice_status():
    """Retrieve voice system status."""
    return {
        "listening": wake_word_detector.is_listening,
        "is_speaking": tts_engine.is_speaking,
        "wake_word": settings.wake_word,
        "supported_wake_words": ["Matrix", "Snap"],
        "hands_free_mode": hands_free_manager.mode.value,
        "hands_free_state": hands_free_manager.state.value,
        "supported_languages": ["English", "Hindi", "Hinglish"],
        "tts_engine": "Edge-TTS Neural + SAPI5 Offline Fallback",
        "stt_engine": "Faster-Whisper (INT8 CPU)"
    }


@router.get("/devices")
async def list_audio_devices():
    """List physical microphone and output devices."""
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        input_devs = [
            {"index": i, "name": d["name"], "channels": d["max_input_channels"], "sample_rate": d["default_samplerate"]}
            for i, d in enumerate(devs) if d["max_input_channels"] > 0
        ]
        output_devs = [
            {"index": i, "name": d["name"], "channels": d["max_output_channels"], "sample_rate": d["default_samplerate"]}
            for i, d in enumerate(devs) if d["max_output_channels"] > 0
        ]
        return {
            "status": "OK",
            "default_input": sd.default.device[0],
            "default_output": sd.default.device[1],
            "input_devices": input_devs,
            "output_devices": output_devs
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


@router.get("/mic/diagnostics")
async def get_mic_diagnostics():
    """Retrieve live microphone hardware and capture telemetry."""
    return {
        "status": "OK",
        "diagnostics": mic_listener.get_diagnostics()
    }


@router.post("/mic/test")
async def test_mic_hardware(payload: RecordRequest):
    """Test live physical microphone audio recording and level analysis."""
    result = mic_listener.test_capture(duration_seconds=payload.duration_seconds)
    return result


@router.get("/snap/diagnostics")
async def get_snap_diagnostics():
    """Retrieve acoustic transient finger-snap detector telemetry."""
    return {
        "status": "OK",
        "diagnostics": snap_detector.get_diagnostics()
    }


@router.post("/snap/toggle")
async def toggle_snap_detector(payload: ToggleListenRequest):
    """Enable or disable acoustic transient finger-snap detection."""
    snap_detector.enabled = payload.enable
    return {
        "status": "OK",
        "enabled": snap_detector.enabled
    }


@router.get("/wake-word/diagnostics")
async def get_wake_word_diagnostics():
    """Retrieve openWakeWord model and prediction telemetry."""
    return {
        "status": "OK",
        "diagnostics": wake_word_detector.get_diagnostics()
    }


@router.post("/device/select")
async def select_audio_device(payload: DeviceSelectRequest):
    """Explicitly select and persist physical microphone device index."""
    try:
        res = mic_listener.select_device(payload.device_index)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/device/inventory")
async def get_device_inventory():
    """Retrieve full hardware device inventory across all Windows audio APIs."""
    return mic_listener.inspect_all_devices()


@router.post("/playback-timing")
async def update_playback_timing(payload: PlaybackTimingRequest):
    """Configure natural speech rate and post-playback settling pause."""
    if payload.speech_rate:
        settings.voice_speech_rate = payload.speech_rate
    if payload.post_pause_ms is not None:
        settings.voice_playback_post_pause_ms = max(50, min(2000, payload.post_pause_ms))
    return {
        "status": "OK",
        "speech_rate": settings.voice_speech_rate,
        "post_pause_ms": settings.voice_playback_post_pause_ms
    }
