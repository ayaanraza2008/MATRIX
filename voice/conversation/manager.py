"""MATRIX Autonomous Hands-Free Conversation & State Manager.
Coordinates:
IDLE (Wake-word standby) -> WAKE_WORD_DETECTED -> LISTENING (VAD capture) ->
END-OF-SPEECH -> TRANSCRIBING -> THINKING -> EXECUTING -> SPEAKING -> AUTO-RESUME
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import time
import asyncio
import numpy as np
import scipy.io.wavfile as wavfile
from voice.wake_word.engine import wake_word_detector
from voice.vad.engine import vad_engine
from voice.speech_to_text.engine import stt_engine
from voice.text_to_speech.engine import tts_engine
from core.brain import brain
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.conversation")


class ConversationMode(str, Enum):
    CONTINUOUS = "continuous"            # Stays in listening mode after responding
    WAKE_WORD_ONLY = "wake_word_only"    # Returns to wake-word standby after each turn
    PUSH_TO_TALK = "push_to_talk"        # Manual push-to-talk button only
    PRIVACY_PAUSE = "privacy_pause"      # Microphone completely muted


class HandsFreeState(str, Enum):
    IDLE = "idle"                        # Standby waiting for 'Matrix' or 'Snap'
    WAKE_WORD = "wake_word"              # Wake-word triggered
    LISTENING = "listening"              # Capturing speech via VAD
    TRANSCRIBING = "transcribing"        # Whisper STT running
    THINKING = "thinking"                # Brain LLM reasoning
    EXECUTING = "executing"              # Multi-agent tools executing
    SPEAKING = "speaking"                # TTS audio playing
    INTERRUPTED = "interrupted"          # Aborted by user
    PAUSED = "paused"                    # Microphone paused
    ERROR = "error"                      # Audio device or engine error


class HandsFreeManager:
    """Central manager for continuous hands-free voice interaction and event broadcasting."""

    def __init__(self):
        self.mode: ConversationMode = ConversationMode.CONTINUOUS
        self.state: HandsFreeState = HandsFreeState.IDLE
        self.active_session_id: str = "sess_hands_free"
        self.last_transcript: str = ""
        self.last_response: str = ""
        self.last_audio_file: Optional[Path] = None
        self._event_subscribers: List[Callable[[Dict[str, Any]], Any]] = []
        self._lock = asyncio.Lock()
        self._interrupted: bool = False
        self._active_turn_task: Optional[asyncio.Task] = None

        # Wire wake-word detector callback
        wake_word_detector.callback = self._on_wake_word_detected
        wake_word_detector.start_listening()

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        """Subscribe a listener (e.g. WebSocket connection manager) to hands-free events."""
        if callback not in self._event_subscribers:
            self._event_subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        """Unsubscribe a listener."""
        if callback in self._event_subscribers:
            self._event_subscribers.remove(callback)

    async def emit_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Broadcast real-time state and telemetry event to subscribers."""
        payload = {
            "type": event_type,
            "state": self.state.value,
            "mode": self.mode.value,
            "timestamp": time.time(),
            "data": data or {}
        }
        logger.debug(f"HandsFree Event: {event_type} (State: {self.state.value})")
        for sub in list(self._event_subscribers):
            try:
                res = sub(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.debug(f"Failed to deliver event to subscriber: {e}")

    def set_mode(self, mode: ConversationMode):
        """Update conversation mode."""
        self.mode = mode
        if mode == ConversationMode.PRIVACY_PAUSE:
            wake_word_detector.stop_listening()
            self.state = HandsFreeState.PAUSED
        elif mode in [ConversationMode.CONTINUOUS, ConversationMode.WAKE_WORD_ONLY]:
            wake_word_detector.start_listening()
            if self.state == HandsFreeState.PAUSED:
                self.state = HandsFreeState.IDLE
        logger.info(f"Hands-Free mode changed to: {mode.value}")
        asyncio.create_task(self.emit_event("MODE_CHANGED", {"mode": mode.value}))

    def _on_wake_word_detected(self, word: str):
        """Handle synchronous wake-word detection callback."""
        if self.mode == ConversationMode.PRIVACY_PAUSE:
            return
        asyncio.create_task(self.handle_wake_word_activation(word))

    async def handle_wake_word_activation(self, word: str):
        """Trigger activation sequence on wake word."""
        if self.state in [HandsFreeState.SPEAKING, HandsFreeState.THINKING, HandsFreeState.EXECUTING]:
            # User interrupted ongoing speech or execution!
            await self.interrupt()

        logger.info(f"ACTIVATING HANDS-FREE on wake-word: '{word}'")
        self.state = HandsFreeState.WAKE_WORD
        await self.emit_event("WAKE_WORD_DETECTED", {"word": word})

        # Short pause for visual activation pulse and optional beep
        await asyncio.sleep(0.3)

        # Transition to active listening
        vad_engine.reset()
        self.state = HandsFreeState.LISTENING
        await self.emit_event("RECORDING_STARTED", {"trigger": word})

    async def interrupt(self):
        """Immediately abort speech synthesis and cancel current thinking task."""
        self._interrupted = True
        tts_engine.stop()
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()

        self.state = HandsFreeState.INTERRUPTED
        await self.emit_event("INTERRUPTED", {})
        vad_engine.reset()

        # Wait briefly then resume appropriate listening state
        await asyncio.sleep(0.4)
        if self.mode == ConversationMode.CONTINUOUS:
            self.state = HandsFreeState.LISTENING
            await self.emit_event("RECORDING_STARTED", {"reason": "interrupted_resume"})
        else:
            self.state = HandsFreeState.IDLE
            await self.emit_event("LISTENING_RESUMED", {})

    async def process_audio_chunk(self, chunk: np.ndarray, source: str = "mic") -> Dict[str, Any]:
        """Ingest 16kHz PCM audio chunk from native mic or Web Audio stream.
        
        Args:
            chunk: numpy int16 audio array (e.g. 512 to 1280 samples)
            source: 'mic' or 'web_audio'
        """
        if self.mode == ConversationMode.PRIVACY_PAUSE:
            return {"status": "paused"}

        # 1. In IDLE mode: Evaluate Wake Word Detector
        if self.state == HandsFreeState.IDLE:
            detected = wake_word_detector.process_audio_frame(chunk, is_tts_speaking=tts_engine.is_speaking)
            if detected:
                await self.handle_wake_word_activation(detected)
                return {"status": "wake_word_detected", "word": detected}
            return {"status": "idle"}

        # 2. In LISTENING mode: Feed VAD and monitor endpoint
        if self.state == HandsFreeState.LISTENING:
            is_speech, is_endpoint, completed_audio = vad_engine.process_frame(chunk)
            if is_endpoint and completed_audio is not None and len(completed_audio) > 0:
                logger.info(f"Captured complete speech segment ({len(completed_audio)} samples). Submitting...")
                # Launch turn processing task
                self._active_turn_task = asyncio.create_task(self._process_completed_speech(completed_audio))
                return {"status": "speech_captured", "samples": len(completed_audio)}

            return {"status": "listening", "is_speech": is_speech}

        return {"status": self.state.value}

    async def _process_completed_speech(self, audio_data: np.ndarray):
        """Process captured speech buffer: STT -> Brain / Tools -> TTS -> Auto-playback -> Auto-resume."""
        async with self._lock:
            self._interrupted = False
            try:
                # 1. State: TRANSCRIBING
                self.state = HandsFreeState.TRANSCRIBING
                await self.emit_event("RECORDING_STOPPED", {})

                # Save temporary WAV for Faster-Whisper
                upload_dir = settings.cache_dir / "audio_in"
                upload_dir.mkdir(parents=True, exist_ok=True)
                temp_wav = upload_dir / f"input_{int(time.time() * 1000)}.wav"
                wavfile.write(str(temp_wav), 16000, audio_data)

                stt_result = await stt_engine.transcribe(temp_wav)
                if temp_wav.exists():
                    try:
                        temp_wav.unlink()
                    except Exception:
                        pass

                transcript = stt_result.get("text", "").strip()
                self.last_transcript = transcript
                logger.info(f"Transcribed user command: '{transcript}'")

                if not transcript or len(transcript) < 2:
                    logger.debug("Empty or unintelligible speech; resuming listening.")
                    if self.mode == ConversationMode.CONTINUOUS:
                        self.state = HandsFreeState.LISTENING
                        vad_engine.reset()
                        await self.emit_event("RECORDING_STARTED", {"reason": "resume_empty"})
                    else:
                        self.state = HandsFreeState.IDLE
                        await self.emit_event("LISTENING_RESUMED", {})
                    return

                await self.emit_event("TRANSCRIPT_GENERATED", {
                    "text": transcript,
                    "language": stt_result.get("detected_language", "en")
                })

                # 2. Check for Immediate Voice Directives
                lower_text = transcript.lower().strip()
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in ["matrix stop", "stop", "cancel", "chup", "ruko"]):
                    await self.interrupt()
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in ["matrix go to sleep", "go to sleep", "sleep", "so jao"]):
                    self.set_mode(ConversationMode.WAKE_WORD_ONLY)
                    ack_audio = await tts_engine.speak("Going to sleep, sir. Say Matrix or Snap whenever you need me.")
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in ["matrix listen", "listen", "suno"]):
                    self.set_mode(ConversationMode.CONTINUOUS)
                    self.state = HandsFreeState.LISTENING
                    vad_engine.reset()
                    await self.emit_event("RECORDING_STARTED", {"reason": "explicit_listen"})
                    return

                # 3. State: THINKING
                self.state = HandsFreeState.THINKING
                await self.emit_event("THINKING", {"prompt": transcript})

                # Execute Brain reasoning and autonomous tool dispatch
                response_text = await brain.interact(
                    user_prompt=transcript,
                    session_id=self.active_session_id
                )
                self.last_response = response_text
                logger.info(f"Brain synthesized response ({len(response_text)} chars).")

                if self._interrupted:
                    logger.info("Turn was interrupted before speech synthesis.")
                    return

                # 4. State: SPEAKING
                self.state = HandsFreeState.SPEAKING
                audio_path = await tts_engine.speak(response_text)
                self.last_audio_file = audio_path

                if self._interrupted:
                    return

                if audio_path and audio_path.exists():
                    audio_filename = audio_path.name
                    await self.emit_event("TTS_STARTED", {
                        "text": response_text,
                        "audio_url": f"/api/v1/voice/audio/{audio_filename}",
                        "filename": audio_filename
                    })

                    # Estimate speech playback duration: ~150 words per minute plus padding
                    word_count = len(response_text.split())
                    estimated_duration = max(1.5, min(25.0, (word_count / 2.5)))
                    await asyncio.sleep(estimated_duration)

                await self.emit_event("TTS_FINISHED", {})

                # 5. Return to Listening or Idle
                if self.mode == ConversationMode.CONTINUOUS and not self._interrupted:
                    logger.info("Continuous mode: Automatically resuming listening without wake word.")
                    vad_engine.reset()
                    self.state = HandsFreeState.LISTENING
                    await self.emit_event("RECORDING_STARTED", {"reason": "auto_resume"})
                else:
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {})

            except asyncio.CancelledError:
                logger.info("Speech processing task was cancelled.")
                self.state = HandsFreeState.IDLE
            except Exception as e:
                logger.error(f"Error in hands-free voice loop: {e}")
                self.state = HandsFreeState.ERROR
                await self.emit_event("ERROR", {"error": str(e)})
                await asyncio.sleep(1.0)
                self.state = HandsFreeState.IDLE
                await self.emit_event("LISTENING_RESUMED", {})


# Global Hands-Free singleton instance
hands_free_manager = HandsFreeManager()
