"""MATRIX Voice Activity Detection (VAD) & Continuous Speech Endpointing Engine.
Uses Silero VAD ONNX with recurrent LSTM state tracking, pre-roll buffering, and configurable endpointing.
"""
from typing import Optional, Tuple, List
from pathlib import Path
from collections import deque
import numpy as np
import onnxruntime as ort
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.vad")


class SileroVADEngine:
    """Offline neural Voice Activity Detector with dynamic endpointing and pre-roll preservation."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        sample_rate: int = 16000,
        speech_threshold: float = 0.45,
        silence_duration_ms: Optional[int] = None,
        min_speech_duration_ms: int = 250,
        energy_threshold: float = 0.005,
        preroll_frames: int = 3  # ~240ms of pre-speech audio
    ):
        self.sample_rate = sample_rate
        self.speech_threshold = speech_threshold
        self.silence_duration_ms = silence_duration_ms if silence_duration_ms is not None else settings.voice_silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.energy_threshold = energy_threshold
        self.preroll_frames = preroll_frames

        # Locate Silero VAD ONNX model
        if model_path is None:
            import openwakeword
            oww_dir = Path(openwakeword.__file__).parent / "resources" / "models"
            candidate = oww_dir / "silero_vad.onnx"
            if candidate.exists():
                self.model_path = candidate
            else:
                self.model_path = settings.models_dir / "wakeword" / "silero_vad.onnx"
        else:
            self.model_path = model_path

        self._session: Optional[ort.InferenceSession] = None
        self._preroll_buffer: deque = deque(maxlen=self.preroll_frames)
        self._init_session()
        self.reset()

    def _init_session(self):
        """Initialize ONNX session on CPU."""
        if self.model_path and self.model_path.exists():
            try:
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self._session = ort.InferenceSession(str(self.model_path), sess_options=opts, providers=["CPUExecutionProvider"])
                logger.info(f"Silero VAD initialized from: {self.model_path.name}")
            except Exception as e:
                logger.error(f"Failed to initialize Silero VAD: {e}")
                self._session = None
        else:
            logger.warning(f"Silero VAD model not found at {self.model_path}; falling back to RMS energy gating.")

    def set_silence_duration_ms(self, ms: int):
        """Update endpoint silence timeout in milliseconds."""
        self.silence_duration_ms = max(500, min(3000, ms))
        logger.info(f"VAD endpoint silence duration set to: {self.silence_duration_ms}ms")

    def reset(self):
        """Reset internal recurrent states and tracking buffers."""
        self._h = np.zeros((2, 1, 64), dtype=np.float32)
        self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self.speech_started = False
        self.total_speech_samples = 0
        self.consecutive_silence_samples = 0
        self.collected_audio_buffer = []
        self._preroll_buffer.clear()

    def compute_energy(self, chunk: np.ndarray) -> float:
        """Compute root-mean-square (RMS) energy of audio frame."""
        if len(chunk) == 0:
            return 0.0
        float_data = chunk.astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(float_data ** 2)))

    def is_speech(self, chunk: np.ndarray) -> Tuple[bool, float]:
        """Compute speech probability for an audio chunk (16kHz)."""
        # Quick energy gate
        rms = self.compute_energy(chunk)
        if rms < self.energy_threshold:
            return False, 0.0

        if self._session is None:
            # Fallback purely to energy
            return (rms >= self.energy_threshold), float(min(1.0, rms * 15.0))

        try:
            # Silero expects 512-sample (32ms) windows for 16kHz
            float_chunk = chunk.astype(np.float32) / 32768.0
            win_size = 512
            
            # Slice chunk into contiguous 512-sample sub-windows so zero audio is discarded
            if len(float_chunk) < win_size:
                windows = [np.pad(float_chunk, (0, win_size - len(float_chunk)))]
            else:
                windows = []
                for s_idx in range(0, len(float_chunk) - win_size + 1, win_size):
                    windows.append(float_chunk[s_idx:s_idx + win_size])
                rem = len(float_chunk) % win_size
                if rem > 0 and len(float_chunk) >= win_size:
                    windows.append(float_chunk[-win_size:])

            max_prob = 0.0
            any_speech = False
            for win in windows:
                inputs = {
                    "input": win.reshape(1, -1),
                    "sr": np.array(self.sample_rate, dtype=np.int64),
                    "h": self._h,
                    "c": self._c
                }
                out, hn, cn = self._session.run(None, inputs)
                self._h = hn
                self._c = cn
                prob = float(out[0][0])
                if prob > max_prob:
                    max_prob = prob
                if prob >= self.speech_threshold:
                    any_speech = True

            return any_speech, max_prob
        except Exception as e:
            logger.debug(f"Silero VAD execution fallback: {e}")
            return (rms >= self.energy_threshold), float(min(1.0, rms * 15.0))

    def process_frame(self, chunk: np.ndarray) -> Tuple[bool, bool, Optional[np.ndarray]]:
        """Process incoming 16kHz audio chunk.
        
        Returns:
            Tuple[is_speech, is_endpoint, completed_audio_clip]
            - is_speech: True if current frame contains voice
            - is_endpoint: True if speech has completed (silence after speech exceeded timeout)
            - completed_audio_clip: The full numpy audio array if endpoint reached, else None
        """
        has_voice, prob = self.is_speech(chunk)
        chunk_samples = len(chunk)

        if has_voice:
            if not self.speech_started:
                self.speech_started = True
                logger.debug("Speech activity detected. Capturing with pre-roll buffer...")
                # Prepend pre-roll buffer frames so the initial consonant is preserved
                for pre_chunk in self._preroll_buffer:
                    self.collected_audio_buffer.append(pre_chunk)
                    self.total_speech_samples += len(pre_chunk)
                self._preroll_buffer.clear()

            self.consecutive_silence_samples = 0
            self.total_speech_samples += chunk_samples
            self.collected_audio_buffer.append(chunk)
            return True, False, None

        if self.speech_started:
            # User previously started speaking, now in pause / trailing silence
            self.consecutive_silence_samples += chunk_samples
            self.collected_audio_buffer.append(chunk)

            silence_ms = (self.consecutive_silence_samples / self.sample_rate) * 1000
            min_speech_ms = (self.total_speech_samples / self.sample_rate) * 1000

            # Check if silence timeout reached (configurable, default 1200ms)
            if silence_ms >= self.silence_duration_ms and min_speech_ms >= self.min_speech_duration_ms:
                logger.info(f"Speech endpoint reached: {min_speech_ms:.0f}ms spoken, {silence_ms:.0f}ms silence.")
                completed_audio = np.concatenate(self.collected_audio_buffer, axis=0) if self.collected_audio_buffer else np.array([], dtype=np.int16)
                self.reset()
                return False, True, completed_audio

            return False, False, None

        # Ambient silence: maintain pre-roll ring buffer
        self._preroll_buffer.append(chunk)
        return False, False, None


# Global VAD singleton instance
vad_engine = SileroVADEngine()
