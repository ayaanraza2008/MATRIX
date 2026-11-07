"""MATRIX Speech-to-Text Recognition Engine.
Uses faster-whisper with quantized INT8 CPU inference for low-RAM multilingual transcription.
"""
from typing import Optional, Dict, Any
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.stt")


class STTEngine:
    """Offline speech recognition using faster-whisper INT8 CPU inference."""

    def __init__(self):
        self._model = None
        self.model_size = "tiny"

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                # Download and cache model in D:\matrix_data\models
                download_root = str(settings.models_dir / "whisper")
                logger.info(f"Loading faster-whisper '{self.model_size}' on CPU (INT8)...")
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=download_root,
                    cpu_threads=settings.cpu_cores
                )
            except Exception as e:
                logger.error(f"Failed to load faster-whisper model: {e}")
                self._model = None
        return self._model

    async def transcribe(self, audio_file_path: Path, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe an audio recording into text."""
        model = self._get_model()
        if not model:
            return {"text": "", "error": "Whisper engine unavailable"}

        try:
            segments, info = model.transcribe(
                str(audio_file_path),
                beam_size=3,
                language=language or ("en" if settings.speech_language == "en" else None)
            )
            full_text = " ".join([seg.text.strip() for seg in segments])
            return {
                "text": full_text,
                "detected_language": info.language,
                "language_probability": round(info.language_probability, 2),
                "duration": round(info.duration, 2)
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {"text": "", "error": str(e)}


# Global STT instance
stt_engine = STTEngine()
