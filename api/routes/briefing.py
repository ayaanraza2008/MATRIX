"""MATRIX Personal Briefing & Awareness API Route.
Endpoints:
- GET /api/v1/briefing/daily
- GET /api/v1/briefing/weather
- GET /api/v1/briefing/away-summary
- POST /api/v1/briefing/speak
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any
from core.information.briefing import briefing_engine
from voice.text_to_speech.engine import tts_engine
from config.logging_config import get_logger

logger = get_logger("api.briefing")
router = APIRouter(prefix="/briefing", tags=["Personal Intelligence & Briefings"])


@router.get("/daily")
async def get_daily_briefing(user_name: Optional[str] = "sir"):
    """Retrieve full synthesized daily intelligence briefing."""
    data = await briefing_engine.generate_daily_briefing(user_name=user_name)
    return {"status": "OK", **data}


@router.get("/weather")
async def get_weather(lat: float = 28.6139, lon: float = 77.2090):
    """Retrieve live global weather and forecast from Open-Meteo."""
    data = await briefing_engine.get_live_weather(latitude=lat, longitude=lon)
    return {"status": "OK", "weather": data}


@router.get("/away-summary")
async def get_away_summary():
    """Retrieve summary of PC activities and system status while user was away."""
    data = briefing_engine.get_away_pc_summary()
    return {"status": "OK", "away_summary": data}


@router.post("/speak")
async def speak_briefing():
    """Synthesize audio speech of today's executive briefing."""
    data = await briefing_engine.generate_daily_briefing()
    text = data.get("briefing_text", "Daily briefing ready, sir.")
    audio_path = await tts_engine.speak(text)
    if not audio_path or not audio_path.exists():
        raise HTTPException(status_code=500, detail="TTS synthesis failed.")

    return FileResponse(path=str(audio_path), media_type="audio/mpeg", filename=audio_path.name)
