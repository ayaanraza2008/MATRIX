"""MATRIX Speech-to-Text Recognition Engine.
Uses faster-whisper with quantized INT8 CPU inference for low-RAM multilingual transcription.
Supports automatic language detection (English, Hindi, Hinglish), hallucination filtering,
and asynchronous non-blocking execution.
"""
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
import re
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.stt")

# Common Whisper hallucinations on ambient noise/silence
HALLUCINATION_PATTERNS = [
    r"^thank you for watching.*",
    r"^thanks for watching.*",
    r"^subtitles by.*",
    r"^please subscribe.*",
    r"^you$"
]


class STTEngine:
    """Offline speech recognition using faster-whisper INT8 CPU inference."""

    def __init__(self):
        self._model = None
        self.model_size = "tiny"

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                download_root = str(settings.models_dir / "whisper")
                logger.info(f"Loading faster-whisper '{self.model_size}' on CPU (INT8)...")
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=download_root,
                    cpu_threads=min(4, settings.cpu_cores)
                )
            except Exception as e:
                logger.error(f"Failed to load faster-whisper model: {e}")
                self._model = None
        return self._model

    def _transcribe_sync(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous CPU transcription worker."""
        model = self._get_model()
        if not model:
            return {"text": "", "error": "Whisper engine unavailable"}

        try:
            # If language is None or 'auto', allow automatic language detection
            lang_param = language if (language and language.lower() not in ["auto", "all"]) else None

            segments, info = model.transcribe(
                audio_path,
                beam_size=3,
                language=lang_param,
                vad_filter=False
            )

            seg_list = list(segments)
            raw_text = " ".join([seg.text.strip() for seg in seg_list]).strip()

            # Clean bracketed tags e.g. [Music], (Laughter)
            cleaned = re.sub(r'\[.*?\]|\(.*?\)', '', raw_text).strip()

            # Filter hallucinations on silence
            for pat in HALLUCINATION_PATTERNS:
                if re.match(pat, cleaned, re.IGNORECASE):
                    cleaned = ""
                    break

            return {
                "text": cleaned,
                "detected_language": info.language,
                "language_probability": round(info.language_probability, 2),
                "duration": round(info.duration, 2)
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {"text": "", "error": str(e)}

    async def transcribe(self, audio_file_path: Path, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe an audio recording into text without blocking the async event loop."""
        if not audio_file_path.exists():
            return {"text": "", "error": "Audio file not found"}

        return await asyncio.to_thread(self._transcribe_sync, str(audio_file_path), language)


# Global STT instance
stt_engine = STTEngine()
