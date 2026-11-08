"""MATRIX Wake-Word Detection Engine.
Monitors microphone stream for 'Matrix', 'Hey Matrix', and 'Hey Jarvis' triggers locally using openWakeWord ONNX.
Features continuous low-resource background evaluation, zero cloud dependencies, and active echo suppression.
"""
from typing import Callable, Optional, Dict, Any, List
import os
import time
import asyncio
from pathlib import Path
import numpy as np
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.wakeword")

WAKEWORD_DIR = Path(r"D:\matrix_data\models\wakeword")


class WakeWordDetector:
    """Local offline wake-word detector using openWakeWord with custom ONNX models."""

    def __init__(
        self,
        sensitivity: Optional[float] = None,
        cooldown_seconds: float = 1.2,
        callback: Optional[Callable[[str], None]] = None
    ):
        self.sensitivity = sensitivity if sensitivity is not None else settings.wake_word_sensitivity
        self.cooldown_seconds = cooldown_seconds
        self.callback = callback
        self.is_listening: bool = False
        self.last_detection_time: float = 0.0
        self.last_detected_word: Optional[str] = None
        self.last_predictions: Dict[str, float] = {}
        self.total_detections: int = 0
        self.frames_processed: int = 0
        self._model = None
        self._initialized: bool = False
        self._audio_chunk_size = 1280  # 80ms at 16kHz

    def _init_model(self):
        """Initialize openWakeWord Model instance with matrix, jarvis, and snap models."""
        matrix_model = WAKEWORD_DIR / "matrix.onnx"
        snap_model = WAKEWORD_DIR / "snap.onnx"

        candidate_models = []
        if matrix_model.exists():
            candidate_models.append(str(matrix_model))
        
        # Include pre-trained robust hey_jarvis model as an official supported alias
        candidate_models.append("hey_jarvis_v0.1")

        if snap_model.exists():
            candidate_models.append(str(snap_model))

        try:
            from openwakeword.model import Model
            self._model = Model(
                wakeword_models=candidate_models,
                inference_framework="onnx"
            )
            self._initialized = True
            logger.info(f"WakeWordDetector armed with models: {list(self._model.models.keys())}")
        except Exception as e:
            logger.error(f"Failed to load openWakeWord models: {e}")
            self._model = None
            self._initialized = False

    def reload_models(self):
        """Force reload of wake-word models when new ONNX files are generated."""
        self._init_model()

    def start_listening(self):
        """Enable active wake-word detection."""
        if not self._initialized or self._model is None:
            self._init_model()
        self.is_listening = True
        logger.info(f"Wake-word monitoring armed (Sensitivity: {self.sensitivity}, Cooldown: {self.cooldown_seconds}s)")

    def stop_listening(self):
        """Disable wake-word detection."""
        self.is_listening = False
        logger.info("Wake-word monitoring disarmed.")

    def set_sensitivity(self, sensitivity: float):
        """Adjust detection threshold (0.1 to 0.95)."""
        self.sensitivity = max(0.1, min(0.95, sensitivity))
        logger.info(f"Wake-word sensitivity set to: {self.sensitivity}")

    def is_cooling_down(self) -> bool:
        """Check if currently in post-activation cooldown."""
        return (time.time() - self.last_detection_time) < self.cooldown_seconds

    def process_audio_frame(
        self,
        frame: np.ndarray,
        is_tts_speaking: bool = False,
        trigger_callback: bool = False
    ) -> Optional[str]:
        """Process incoming 16kHz PCM audio chunk for wake words in real time.
        
        Args:
            frame: 16-bit PCM numpy array (1280 samples = 80ms)
            is_tts_speaking: Whether MATRIX TTS audio is currently playing
            trigger_callback: Whether to execute self.callback(detected_name)

        Returns:
            Wake word string ('matrix', 'jarvis', or 'snap') if triggered, else None
        """
        if not self.is_listening:
            return None

        # Active Echo Suppression: Ignore mic frames while MATRIX is speaking
        if is_tts_speaking:
            return None

        # Cooldown guard: Prevent repeated firing from single utterance
        if self.is_cooling_down():
            return None

        if self._model is None:
            self._init_model()
            if self._model is None:
                return None

        self.frames_processed += 1

        # Ensure frame is 16-bit integer array
        if frame.dtype != np.int16:
            frame = (np.clip(frame, -1.0, 1.0) * 32767.0).astype(np.int16)

        # Slice or pad to exact 1280 samples for openWakeWord
        if len(frame) != self._audio_chunk_size:
            if len(frame) > self._audio_chunk_size:
                frame = frame[:self._audio_chunk_size]
            else:
                frame = np.pad(frame, (0, self._audio_chunk_size - len(frame)))

        try:
            # Predict scores on clean audio frame preserving spectro-temporal continuity
            predictions = self._model.predict(frame)
            self.last_predictions = {k: float(round(v, 4)) for k, v in predictions.items()}
            
            best_model = None
            best_score = 0.0

            for model_name, score in predictions.items():
                m_lower = model_name.lower()
                
                # 'Matrix' & 'Jarvis' models use configured sensitivity (default 0.35)
                if "matrix" in m_lower or "jarvis" in m_lower:
                    thresh = self.sensitivity
                else:
                    # 'Snap' spoken keyword requires higher threshold (0.75) to prevent consonant false positives
                    thresh = max(0.75, self.sensitivity + 0.35)

                if score >= thresh and score > best_score:
                    best_score = score
                    best_model = model_name

            if best_model:
                m_lower = best_model.lower()
                if "matrix" in m_lower:
                    detected_name = "matrix"
                elif "jarvis" in m_lower:
                    detected_name = "matrix"  # Treat 'Jarvis' as an alias for Matrix activation
                else:
                    detected_name = "snap"

                now = time.time()
                self.last_detection_time = now
                self.last_detected_word = detected_name
                self.total_detections += 1
                logger.info(f"Wake-word DETECTED: '{detected_name}' (model: {best_model}, score: {best_score:.3f})")

                if trigger_callback and self.callback:
                    try:
                        self.callback(detected_name)
                    except Exception as cb_err:
                        logger.error(f"Error in wake-word callback: {cb_err}")

                return detected_name
        except Exception as e:
            logger.debug(f"Wake-word inference error: {e}")

        return None

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic metrics for wake-word engine."""
        return {
            "initialized": self._initialized,
            "is_listening": self.is_listening,
            "sensitivity": self.sensitivity,
            "cooldown_seconds": self.cooldown_seconds,
            "total_detections": self.total_detections,
            "frames_processed": self.frames_processed,
            "last_detected_word": self.last_detected_word,
            "last_detection_time": self.last_detection_time,
            "last_predictions": self.last_predictions,
            "loaded_models": list(self._model.models.keys()) if self._model else []
        }


# Global wake-word instance
wake_word_detector = WakeWordDetector()
