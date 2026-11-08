"""MATRIX Native Background Microphone Streamer.
Streams 16kHz audio from system microphone into HandsFreeManager using non-blocking sounddevice callbacks.
Features:
- Automatic detection and explicit binding to default physical microphone
- Real-time RMS energy and peak amplitude telemetry
- Automatic reconnection on device unplug/error with exponential backoff
- Zero-copy buffer feeds and low-RAM footprint
- Diagnostic queries and test capture endpoints
"""
from typing import Optional, Dict, Any, List, Tuple
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

        # Telemetry and state metrics
        self.active_device_index: Optional[int] = None
        self.active_device_name: str = "Unknown"
        self.frames_captured: int = 0
        self.total_samples: int = 0
        self.last_rms: float = 0.0
        self.last_peak: int = 0
        self.silence_frames: int = 0
        self.active_frames: int = 0
        self.error_count: int = 0
        self.last_error: Optional[str] = None
        self.start_time: float = 0.0

    def _discover_input_device(self) -> Tuple[Optional[int], str]:
        """Find the default PortAudio recording device."""
        try:
            default_in = sd.default.device[0]
            dev_info = sd.query_devices(default_in, 'input')
            return default_in, dev_info['name']
        except Exception as e:
            logger.debug(f"Default input device query failed ({e}); scanning devices...")
            try:
                for idx, dev in enumerate(sd.query_devices()):
                    if dev['max_input_channels'] > 0:
                        return idx, dev['name']
            except Exception as e2:
                logger.error(f"Cannot enumerate audio input devices: {e2}")
        return None, "Default PortAudio Device"

    def _audio_callback(self, indata, frames, time_info, status):
        """Low-latency callback fired by PortAudio for each 80ms chunk."""
        if not self._running:
            return
        if status:
            logger.debug(f"PortAudio status flag: {status}")

        chunk = indata[:, 0].copy()  # int16 1D array
        self.frames_captured += 1
        self.total_samples += len(chunk)

        # Calculate telemetry metrics
        peak = int(np.max(np.abs(chunk)))
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        self.last_peak = peak
        self.last_rms = round(rms, 2)

        if rms < 30.0:
            self.silence_frames += 1
        else:
            self.active_frames += 1

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                hands_free_manager.process_audio_chunk(chunk, source="native_mic"),
                self._loop
            )
            if self.frames_captured % 50 == 1:
                asyncio.run_coroutine_threadsafe(
                    hands_free_manager.emit_event("AUDIO_FRAME_RECEIVED", {
                        "frame_index": self.frames_captured,
                        "rms": self.last_rms,
                        "peak": self.last_peak,
                        "active": self.last_rms >= 30.0
                    }),
                    self._loop
                )

    def _run_stream_loop(self):
        """Worker thread running PortAudio input stream with automatic error recovery."""
        logger.info("Native microphone capture thread started.")
        retry_delay = 1.0

        while self._running:
            dev_idx, dev_name = self._discover_input_device()
            self.active_device_index = dev_idx
            self.active_device_name = dev_name
            logger.info(f"Binding NativeMicListener to device [{dev_idx}]: '{dev_name}' @ {self.sample_rate}Hz")

            try:
                stream_kwargs = {
                    "samplerate": self.sample_rate,
                    "channels": 1,
                    "dtype": 'int16',
                    "blocksize": self.block_size,
                    "callback": self._audio_callback
                }
                if dev_idx is not None and dev_idx >= 0:
                    stream_kwargs["device"] = dev_idx

                with sd.InputStream(**stream_kwargs):
                    retry_delay = 1.0  # Reset backoff on successful open
                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            hands_free_manager.emit_event("DEVICE_READY", {
                                "device_index": dev_idx,
                                "device_name": dev_name,
                                "sample_rate": self.sample_rate,
                                "channels": 1,
                                "block_size": self.block_size
                            }),
                            self._loop
                        )
                    while self._running:
                        time.sleep(0.1)
            except Exception as e:
                if not self._running:
                    break
                self.error_count += 1
                self.last_error = str(e)
                logger.warning(
                    f"Microphone stream disconnected or unavailable: {e}. "
                    f"Retrying in {retry_delay:.1f}s (Error count: {self.error_count})..."
                )
                time.sleep(retry_delay)
                retry_delay = min(10.0, retry_delay * 1.5)

        logger.info("Native microphone capture thread stopped.")

    def start(self, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """Start background microphone monitoring."""
        if self._running:
            return
        self._running = True
        self.start_time = time.time()
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

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return full hardware and streaming telemetry."""
        uptime = (time.time() - self.start_time) if self._running else 0.0
        return {
            "is_running": self._running,
            "uptime_seconds": round(uptime, 1),
            "sample_rate": self.sample_rate,
            "block_size": self.block_size,
            "active_device_index": self.active_device_index,
            "active_device_name": self.active_device_name,
            "frames_captured": self.frames_captured,
            "total_samples": self.total_samples,
            "last_rms": self.last_rms,
            "last_peak": self.last_peak,
            "silence_frames": self.silence_frames,
            "active_frames": self.active_frames,
            "error_count": self.error_count,
            "last_error": self.last_error
        }

    def test_capture(self, duration_seconds: float = 1.0) -> Dict[str, Any]:
        """Perform a synchronous hardware test recording."""
        duration = max(0.5, min(5.0, duration_seconds))
        sr = self.sample_rate
        try:
            dev_idx, dev_name = self._discover_input_device()
            rec = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='int16', device=dev_idx)
            sd.wait()
            rec_1d = rec[:, 0]
            peak = int(np.max(np.abs(rec_1d)))
            rms = float(np.sqrt(np.mean(rec_1d.astype(np.float32) ** 2)))
            return {
                "status": "PASS",
                "device_index": dev_idx,
                "device_name": dev_name,
                "duration_seconds": duration,
                "samples_captured": len(rec_1d),
                "peak_amplitude": peak,
                "rms_amplitude": round(rms, 2),
                "is_non_silent": (rms > 20.0 or peak > 150)
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e)
            }


# Global native mic listener instance
mic_listener = NativeMicListener()
