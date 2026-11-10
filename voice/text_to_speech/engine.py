"""MATRIX Voice Speech Synthesis Engine.
Provides natural text-to-speech in English, Hindi, and Hinglish with fallback from edge-tts to pyttsx3.
Features real-time interruption, audio buffer drain synchronization, configurable speech rate,
and coordinated playback deduplication through PlaybackCoordinator.
"""
from typing import Optional
import asyncio
from pathlib import Path
import time
import re
import uuid
from config.settings import settings
from config.logging_config import get_logger
from voice.playback_coordinator import playback_coordinator

logger = get_logger("voice.tts")


class TTSEngine:
    """Multi-engine TTS supporting offline SAPI5 and neural speech with hardware buffer drain."""

    HINGLISH_KEYWORDS = [
        "namaste", "aap", "kaise", "kya", "haan", "theek", "shukriya",
        "kaam", "karo", "batao", "sunao", "mera", "meri", "hum"
    ]

    def __init__(self):
        self.output_dir = settings.cache_dir / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.is_speaking: bool = False
        self._stop_requested: bool = False
        self.last_playback_duration: float = 0.0
        self.last_playback_finished: float = 0.0
        self._lock = asyncio.Lock()

    def stop(self):
        """Request immediate cancellation of speech and halt audio playback."""
        self._stop_requested = True
        self.is_speaking = False
        playback_coordinator.cancel()
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

    async def _play_audio(self, path: Path, playback_id: Optional[str] = None):
        """Play audio file through sounddevice asynchronously with hardware buffer drain."""
        try:
            import soundfile as sf
            import sounddevice as sd

            data, sr = sf.read(str(path))
            duration = len(data) / float(sr)
            self.last_playback_duration = round(duration, 2)

            if playback_id:
                playback_coordinator.mark_playing(playback_id)

            # Start asynchronous playback
            sd.play(data, samplerate=sr)
            start_time = time.time()

            # Active polling loop checking playback stream status and stop requests
            while (time.time() - start_time) < (duration + 0.1):
                if self._stop_requested:
                    sd.stop()
                    logger.info("Audio playback immediately aborted by user stop directive.")
                    break
                await asyncio.sleep(0.02)

            # Hardware DAC / driver buffer drain delay to ensure speaker reverberation clears
            if not self._stop_requested:
                try:
                    sd.wait(ignore_errors=True)
                except Exception:
                    pass
                # Post-playback settling pause (150ms buffer drain)
                await asyncio.sleep(0.15)

            self.last_playback_finished = time.time()
            logger.debug(f"Audio playback completed ({duration:.2f}s) and output buffers drained.")

        except Exception as e:
            logger.warning(f"Audio playback encountered an exception: {e}")
            try:
                import sounddevice as sd
                sd.stop()
            except Exception:
                pass

    async def synthesize_to_file(
        self,
        text: str,
        voice_override: Optional[str] = None,
        response_id: Optional[str] = None,
        owner: str = "direct"
    ) -> Optional[Path]:
        """Synthesize text to audio file without playing to speakers."""
        return await self.speak(
            text=text,
            voice_override=voice_override,
            play_audio=False,
            response_id=response_id,
            owner=owner
        )

    async def speak(
        self,
        text: str,
        voice_override: Optional[str] = None,
        play_audio: bool = True,
        response_id: Optional[str] = None,
        playback_id: Optional[str] = None,
        owner: str = "direct",
        request_id: Optional[str] = None
    ) -> Optional[Path]:
        """Synthesize text to audio, optionally play through speakers, and return audio file path.
        Enforces single-source playback coordination when play_audio=True and response_id is supplied.
        """
        async with self._lock:
            self._stop_requested = False
            active_pid = playback_id
            resp_id = response_id or f"resp_synth_{uuid.uuid4().hex[:10]}"

            # Deduplication & playback acquisition gate
            if play_audio:
                acquired, rec, reason = await playback_coordinator.acquire_playback(
                    response_id=resp_id,
                    owner=owner,
                    text=text,
                    request_id=request_id
                )
                if not acquired:
                    logger.info(
                        f"TTSEngine: audible playback suppressed for response '{resp_id}' ({reason}). "
                        f"Synthesizing audio file only."
                    )
                    play_audio = False
                active_pid = rec.playback_id
            elif not active_pid:
                # Track file-only synthesis for completeness
                active_pid = f"pb_file_{uuid.uuid4().hex[:8]}"

            if active_pid:
                playback_coordinator.mark_generating(active_pid)

            self.is_speaking = True
            target_path = self.output_dir / f"speech_{int(time.time() * 1000)}.mp3"

            voice = self.select_voice(text, voice_override)
            speech_rate = settings.voice_speech_rate or "+0%"

            # Try edge-tts for high-quality natural voice
            try:
                import edge_tts
                communicate = edge_tts.Communicate(text, voice, rate=speech_rate)
                await communicate.save(str(target_path))

                if self._stop_requested:
                    logger.info("Speech generation aborted before playback.")
                    self.is_speaking = False
                    if active_pid:
                        playback_coordinator.cancel(active_pid)
                    return None

                if target_path.exists() and target_path.stat().st_size > 0:
                    logger.info(f"Synthesized neural speech ({voice}, rate={speech_rate}): {target_path.name}")
                    if play_audio and not self._stop_requested:
                        await self._play_audio(target_path, playback_id=active_pid)
                    self.is_speaking = False
                    if active_pid:
                        playback_coordinator.mark_completed(active_pid, audio_file=target_path)
                    return target_path
            except Exception as e:
                logger.warning(f"Neural TTS failed ({e}), attempting offline SAPI5 fallback...")

            # Offline fallback: pyttsx3 (SAPI5 native on Windows)
            try:
                import pyttsx3
                wav_path = target_path.with_suffix(".wav")
                engine = pyttsx3.init()
                engine.setProperty('rate', 165)
                engine.save_to_file(text, str(wav_path))
                engine.runAndWait()
                if wav_path.exists() and wav_path.stat().st_size > 0:
                    logger.info(f"Synthesized offline SAPI5 speech: {wav_path.name}")
                    if play_audio and not self._stop_requested:
                        await self._play_audio(wav_path, playback_id=active_pid)
                    self.is_speaking = False
                    if active_pid:
                        playback_coordinator.mark_completed(active_pid, audio_file=wav_path)
                    return wav_path
            except Exception as e:
                logger.error(f"Offline TTS failed: {e}")
                if active_pid:
                    playback_coordinator.mark_failed(active_pid, str(e))

            self.is_speaking = False
            return None


# Global TTS Engine singleton
tts_engine = TTSEngine()
