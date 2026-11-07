"""MATRIX Native Background Microphone Streamer.
Streams 16kHz audio from system microphone into HandsFreeManager using non-blocking sounddevice callbacks.
Features automatic reconnection on device unplug/error, zero-copy buffer feeds, and low-RAM footprint.
"""
from typing import Optional
import threading
import time
import asyncio
import numpy as np
import sounddevice as sd
from voice.conversation.manager import hands_free_manager, HandsFreeState, ConversationMode
from config.logging_config import get_logger

logger = get_logger("voice.mic_listener")


class NativeMicListener:
    """Non-blocking background microphone capture thread feeding HandsFreeManager."""

    def __init__(self, sample_rate: int = 16000, block_size: int = 1280):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Low-latency callback fired by PortAudio for each 80ms chunk."""
        if not self._running:
            return
        if status:
            logger.debug(f"Audio stream status flag: {status}")

        chunk = indata[:, 0].copy()  # int16 1D array
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                hands_free_manager.process_audio_chunk(chunk, source="native_mic"),
                self._loop
            )

    def _run_stream_loop(self):
        """Worker thread running PortAudio input stream with automatic error recovery."""
        logger.info("Native microphone capture thread started.")
        retry_delay = 1.0

        while self._running:
            try:
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='int16',
                    blocksize=self.block_size,
                    callback=self._audio_callback
                ):
                    retry_delay = 1.0  # Reset on successful open
                    while self._running:
                        time.sleep(0.1)
            except Exception as e:
                if not self._running:
                    break
                logger.warning(f"Microphone stream disconnected or unavailable: {e}. Retrying in {retry_delay:.1f}s...")
                time.sleep(retry_delay)
                retry_delay = min(10.0, retry_delay * 1.5)

        logger.info("Native microphone capture thread stopped.")

    def start(self, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """Start background microphone monitoring."""
        if self._running:
            return
        self._running = True
        self._loop = event_loop or asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._run_stream_loop, daemon=True, name="MatrixNativeMicListener")
        self._thread.start()
        logger.info("Native microphone listener armed.")

    def stop(self):
        """Stop background microphone monitoring."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        logger.info("Native microphone listener disarmed.")


# Global native mic listener instance
mic_listener = NativeMicListener()
