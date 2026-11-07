"""MATRIX Voice System API Route.
Provides endpoints for speech synthesis, microphone audio transcription,
end-to-end voice loop (Speech -> STT -> Brain -> TTS -> Audio),
audio file serving, wake-word toggling, audio device discovery, and speech stop controls.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import time
import asyncio
from voice.text_to_speech.engine import tts_engine
from voice.speech_to_text.engine import stt_engine
from voice.wake_word.engine import wake_word_detector
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


class RecordRequest(BaseModel):
    duration_seconds: float = 3.0
    language: Optional[str] = None


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
    """Immediately abort speech synthesis."""
    tts_engine.stop()
    return {"status": "OK", "stopped": True}


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
        import numpy as np
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
