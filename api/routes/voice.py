"""MATRIX Voice System API Route.
Provides endpoints for speech synthesis, microphone audio transcription,
wake-word toggling, audio device discovery, and speech stop controls.
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
    """Transcribe an uploaded audio file using Faster-Whisper."""
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
    wav_path = out_dir / f"mic_{int(time.time() * 1000)}.wav"

    sf.write(str(wav_path), recording, sr)
    rms = float(np.sqrt(np.mean(recording**2)))

    result = await stt_engine.transcribe(wav_path, language=payload.language)

    return {
        "status": "OK",
        "duration_recorded": duration,
        "energy_rms": round(rms, 6),
        "filepath": str(wav_path),
        "transcription": result
    }


@router.post("/toggle-listen")
async def toggle_listen(payload: ToggleListenRequest):
    """Enable or disable wake-word listening."""
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
