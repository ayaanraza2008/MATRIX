"""MATRIX Voice System API Route.
Provides endpoints for speech synthesis, microphone wake-word toggling, and audio streaming.
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from voice.text_to_speech.engine import tts_engine
from voice.wake_word.engine import wake_word_detector

router = APIRouter(prefix="/voice", tags=["Voice System"])


class SpeakRequest(BaseModel):
    text: str
    voice: str | None = None


class ToggleListenRequest(BaseModel):
    enable: bool


@router.post("/speak")
async def speak_text(payload: SpeakRequest):
    """Synthesize text to speech and return the generated audio file."""
    audio_path = await tts_engine.speak(payload.text, voice_override=payload.voice)
    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")

    media_type = "audio/mpeg" if audio_path.suffix == ".mp3" else "audio/wav"
    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=audio_path.name
    )


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
        "supported_languages": ["English", "Hindi", "Hinglish"],
        "tts_engine": "Edge-TTS Neural + SAPI5 Offline Fallback"
    }
