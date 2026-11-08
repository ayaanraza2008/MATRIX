"""MATRIX Voice Speech Synthesis Engine.
Provides natural text-to-speech in English, Hindi, and Hinglish with fallback from edge-tts to pyttsx3.
"""
from typing import Optional
import asyncio
from pathlib import Path
import time
import re
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.tts")


class TTSEngine:
    """Multi-engine TTS supporting offline SAPI5 and neural speech."""

    HINGLISH_KEYWORDS = [
        "namaste", "aap", "kaise", "kya", "haan", "theek", "shukriya",
        "kaam", "karo", "batao", "sunao", "mera", "meri", "hum"
    ]

    def __init__(self):
        self.output_dir = settings.cache_dir / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.is_speaking: bool = False
        self._stop_requested: bool = False

    def stop(self):
        """Request immediate cancellation of speech and halt audio playback."""
        self._stop_requested = True
        self.is_speaking = False
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        logger.info("Speech stop requested and speaker playback halted.")

    def select_voice(self, text: str, voice_override: Optional[str] = None) -> str:
        """Select appropriate neural voice for English, Hindi, or Hinglish."""
        if voice_override:
            return voice_override

        # Check Devanagari Hindi
        if any('\u0900' <= c <= '\u097F' for c in text):
            return "hi-IN-SwaraNeural"

        # Check Romanized Hinglish
        words = re.findall(r'\b\w+\b', text.lower())
        if any(w in self.HINGLISH_KEYWORDS for w in words):
            return "en-IN-PrabhatNeural"

        # JARVIS-style English persona
        return "en-US-ChristopherNeural"

    async def _play_audio(self, path: Path):
        """Play audio file through sounddevice asynchronously with interruption monitoring."""
        try:
            import soundfile as sf
            import sounddevice as sd
            data, sr = sf.read(str(path))
            sd.play(data, samplerate=sr)
            duration = len(data) / sr
            start = time.time()
            while (time.time() - start) < duration:
                if self._stop_requested:
                    sd.stop()
                    logger.info("Audio playback interrupted by user.")
                    break
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Audio playback encountered an exception: {e}")

    async def speak(self, text: str, voice_override: Optional[str] = None, play_audio: bool = True) -> Optional[Path]:
        """Synthesize text to audio, optionally play through speakers, and return audio file path."""
        self._stop_requested = False
        self.is_speaking = True
        target_path = self.output_dir / f"speech_{int(time.time() * 1000)}.mp3"

        voice = self.select_voice(text, voice_override)

        # Try edge-tts for high-quality natural voice
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(target_path))

            if self._stop_requested:
                logger.info("Speech generation aborted before playback.")
                self.is_speaking = False
                return None

            if target_path.exists() and target_path.stat().st_size > 0:
                logger.info(f"Synthesized neural speech ({voice}): {target_path.name}")
                if play_audio and not self._stop_requested:
                    await self._play_audio(target_path)
                self.is_speaking = False
                return target_path
        except Exception as e:
            logger.warning(f"Neural TTS failed ({e}), attempting offline SAPI5 fallback...")

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
                if play_audio and not self._stop_requested:
                    await self._play_audio(wav_path)
                self.is_speaking = False
                return wav_path
        except Exception as e:
            logger.error(f"Offline TTS failed: {e}")

        self.is_speaking = False
        return None


# Global TTS instance
tts_engine = TTSEngine()
