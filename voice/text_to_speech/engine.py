"""MATRIX Voice Speech Synthesis Engine.
Provides natural text-to-speech in English and Hindi with fallback from edge-tts to pyttsx3.
"""
from typing import Optional
import asyncio
from pathlib import Path
import time
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.tts")


class TTSEngine:
    """Multi-engine TTS supporting offline SAPI5 and neural speech."""

    def __init__(self):
        self.output_dir = settings.cache_dir / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def speak(self, text: str, voice_override: Optional[str] = None) -> Optional[Path]:
        """Synthesize text to audio and return the audio file path."""
        target_path = self.output_dir / f"speech_{int(time.time() * 1000)}.mp3"

        # Try edge-tts for high-quality natural voice (English / Hindi / Hinglish)
        try:
            import edge_tts
            voice = voice_override or ("hi-IN-SwaraNeural" if any('\u0900' <= c <= '\u097F' for c in text) else "en-US-ChristopherNeural")
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(target_path))

            if target_path.exists() and target_path.stat().st_size > 0:
                logger.info(f"Synthesized neural speech ({voice}): {target_path.name}")
                return target_path
        except Exception as e:
            logger.warning(f"Neural TTS failed, using offline fallback: {e}")

        # Offline fallback: pyttsx3 (SAPI5 native on Windows)
        try:
            import pyttsx3
            wav_path = target_path.with_suffix(".wav")
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.save_to_file(text, str(wav_path))
            engine.runAndWait()
            if wav_path.exists() and wav_path.stat().st_size > 0:
                logger.info(f"Synthesized offline SAPI5 speech: {wav_path.name}")
                return wav_path
        except Exception as e:
            logger.error(f"Offline TTS failed: {e}")

        return None


# Global TTS instance
tts_engine = TTSEngine()
