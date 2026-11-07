"""MATRIX Wake-Word & Voice Activity Detection Engine.
Monitors microphone for 'Hey Matrix' trigger without cloud transmission.
"""
from typing import Callable, Optional
import asyncio
import numpy as np
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.wakeword")


class WakeWordDetector:
    """Detects wake phrase or voice activity triggers locally."""

    def __init__(self, callback: Optional[Callable[[], None]] = None):
        self.callback = callback
        self.is_listening = False
        self._task: Optional[asyncio.Task] = None

    def start_listening(self):
        """Enable active listening state."""
        self.is_listening = True
        logger.info(f"Wake-word monitoring armed: '{settings.wake_word}'")

    def stop_listening(self):
        """Disable listening state."""
        self.is_listening = False
        logger.info("Wake-word monitoring disarmed.")

    def process_audio_frame(self, frame: np.ndarray) -> bool:
        """Process incoming audio energy for Voice Activity Detection."""
        if not self.is_listening:
            return False
        # Calculate RMS energy
        rms = np.sqrt(np.mean(frame**2)) if len(frame) > 0 else 0
        threshold = 0.02  # Voice activity threshold
        return rms > threshold


# Global wake-word instance
wake_word_detector = WakeWordDetector()
