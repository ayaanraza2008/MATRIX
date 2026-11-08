"""MATRIX Autonomous Hands-Free Conversation & State Manager.
Coordinates:
SLEEPING -> IDLE (Wake-word & Snap standby) -> WAKE_DETECTED -> LISTENING (VAD capture with timeout) ->
TRANSCRIBING -> THINKING -> PLANNING -> EXECUTING -> SPEAKING -> AUTO-RESUME or STANDBY.

Features:
- Dual wake-word trigger: Spoken "Matrix" and spoken "Snap" (openWakeWord)
- Dedicated acoustic transient impulse detection for real physical finger-snaps
- Real-time acoustic echo suppression during TTS speech output
- Intelligent turn timeout preventing infinite listening loops
- Immediate barge-in voice directives ("stop", "cancel", "sleep", "listen")
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
import time
import asyncio
import numpy as np
import scipy.io.wavfile as wavfile
from voice.wake_word.engine import wake_word_detector
from voice.snap_detector import snap_detector
from voice.vad.engine import vad_engine
from voice.speech_to_text.engine import stt_engine
from voice.text_to_speech.engine import tts_engine
from core.brain import brain
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("voice.conversation")


class ConversationMode(str, Enum):
    CONTINUOUS = "continuous"            # Stays in listening mode after responding, times out to IDLE if silent
    WAKE_WORD_ONLY = "wake_word_only"    # Returns to wake-word standby immediately after each turn
    PUSH_TO_TALK = "push_to_talk"        # Manual push-to-talk button only
    PRIVACY_PAUSE = "privacy_pause"      # Microphone completely muted


class HandsFreeState(str, Enum):
    SLEEPING = "sleeping"                # Low-resource sleep mode
    IDLE = "idle"                        # Standby waiting for 'Matrix' or physical finger-snap
    WAKE_DETECTED = "wake_detected"      # Wake-word or snap triggered
    LISTENING = "listening"              # Capturing speech via VAD with timeout guard
    TRANSCRIBING = "transcribing"        # Whisper STT running
    THINKING = "thinking"                # Brain LLM reasoning
    PLANNING = "planning"                # Orchestrator planning
    EXECUTING = "executing"              # Multi-agent tools executing
    SPEAKING = "speaking"                # TTS audio playing
    INTERRUPTED = "interrupted"          # Aborted by user
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

        # Turn timeout guards
        self._consecutive_empty_turns: int = 0
        self._listening_start_time: float = 0.0
        self._listening_timeout_seconds: float = 7.5

        # Arm wake word engine (single-dispatch via process_audio_chunk)
        wake_word_detector.callback = None
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
            self.state = HandsFreeState.SLEEPING
        elif mode in [ConversationMode.CONTINUOUS, ConversationMode.WAKE_WORD_ONLY]:
            wake_word_detector.start_listening()
            if self.state in (HandsFreeState.SLEEPING, HandsFreeState.ERROR):
                self.state = HandsFreeState.IDLE
        logger.info(f"Hands-Free mode changed to: {mode.value}")
        asyncio.create_task(self.emit_event("MODE_CHANGED", {"mode": mode.value}))

    async def handle_wake_word_activation(self, trigger_source: str):
        """Trigger activation sequence on spoken wake-word or acoustic finger snap."""
        if self.state in [HandsFreeState.SPEAKING, HandsFreeState.THINKING, HandsFreeState.EXECUTING, HandsFreeState.PLANNING]:
            # User interrupted ongoing speech or execution!
            await self.interrupt()

        logger.info(f"ACTIVATING HANDS-FREE on trigger: '{trigger_source}'")
        self.state = HandsFreeState.WAKE_DETECTED
        self._consecutive_empty_turns = 0
        await self.emit_event("WAKE_DETECTED", {"trigger": trigger_source})
        await self.emit_event("WAKE_WORD_DETECTED", {"trigger": trigger_source})

        # JARVIS Spoken Acknowledgment
        ack_phrases = {
            "matrix": "Yes, sir?",
            "snap": "Standing by, sir.",
            "finger_snap": "At your service, sir."
        }
        ack_phrase = ack_phrases.get(trigger_source, "I'm listening.")

        # Brief activation window then transition to active listening
        await asyncio.sleep(0.15)
        vad_engine.reset()
        self._listening_start_time = time.time()
        self.state = HandsFreeState.LISTENING
        await self.emit_event("LISTENING", {"trigger": trigger_source, "ack": ack_phrase})
        await self.emit_event("RECORDING_STARTED", {"trigger": trigger_source, "ack": ack_phrase})

    async def interrupt(self):
        """Immediately abort speech synthesis and cancel current thinking task."""
        self._interrupted = True
        tts_engine.stop()
        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()

        self.state = HandsFreeState.INTERRUPTED
        await self.emit_event("INTERRUPTED", {})
        vad_engine.reset()

        # Wait briefly then resume appropriate state
        await asyncio.sleep(0.3)
        if self.mode == ConversationMode.CONTINUOUS:
            self.state = HandsFreeState.LISTENING
            self._listening_start_time = time.time()
            await self.emit_event("RECORDING_STARTED", {"reason": "interrupted_resume"})
        else:
            self.state = HandsFreeState.IDLE
            await self.emit_event("LISTENING_RESUMED", {})

    async def process_audio_chunk(self, chunk: np.ndarray, source: str = "mic") -> Dict[str, Any]:
        """Ingest 16kHz PCM audio chunk from native mic or Web Audio stream.
        
        Args:
            chunk: numpy int16 audio array (e.g. 512 to 1280 samples)
            source: 'native_mic' or 'web_audio'
        """
        if self.mode == ConversationMode.PRIVACY_PAUSE:
            return {"status": "paused"}

        # Active Echo Suppression with Finger-Snap Barge-In during TTS Playback
        if tts_engine.is_speaking:
            # Check for acoustic snap barge-in interrupt
            if snap_detector.process_audio_frame(chunk, is_tts_speaking=False):
                logger.info("Barge-in: Acoustic snap detected during speech; interrupting playback.")
                await self.interrupt()
                return {"status": "barge_in_snap"}
            return {"status": "tts_speaking_suppressed"}

        # 1. In IDLE / SLEEPING mode: Evaluate Acoustic Finger-Snap and Spoken Wake Words
        if self.state in (HandsFreeState.IDLE, HandsFreeState.SLEEPING):
            # Check A: Physical Finger-Snap Acoustic Transient
            if snap_detector.process_audio_frame(chunk, is_tts_speaking=False):
                await self.handle_wake_word_activation("finger_snap")
                return {"status": "snap_activated", "trigger": "finger_snap"}

            # Check B: Spoken 'Matrix' or 'Snap' (openWakeWord)
            detected = wake_word_detector.process_audio_frame(
                chunk,
                is_tts_speaking=False,
                trigger_callback=False
            )
            if detected:
                await self.handle_wake_word_activation(detected)
                return {"status": "wake_word_detected", "word": detected}

            return {"status": self.state.value}

        # 2. In LISTENING mode: Guard with timeout, feed VAD, and monitor endpoint
        if self.state == HandsFreeState.LISTENING:
            # Physical snap during listening acts as immediate cancel / standby
            if snap_detector.process_audio_frame(chunk, is_tts_speaking=False):
                logger.info("Snap detected during listening; returning to standby.")
                self.state = HandsFreeState.IDLE
                vad_engine.reset()
                await self.emit_event("LISTENING_RESUMED", {"reason": "snap_interrupt"})
                return {"status": "snap_cancelled"}

            # Silence Timeout Guard: If no speech starts within 7.5 seconds, return to IDLE standby
            elapsed_listening = time.time() - self._listening_start_time
            if elapsed_listening > self._listening_timeout_seconds and not vad_engine.speech_started:
                logger.info(f"Listening timed out after {elapsed_listening:.1f}s of silence. Returning to IDLE standby.")
                self.state = HandsFreeState.IDLE
                vad_engine.reset()
                await self.emit_event("LISTENING_RESUMED", {"reason": "silence_timeout"})
                return {"status": "idle_timeout"}

            # Feed Silero VAD
            is_speech, is_endpoint, completed_audio = vad_engine.process_frame(chunk)
            if is_endpoint and completed_audio is not None and len(completed_audio) > 0:
                logger.info(f"Captured complete speech segment ({len(completed_audio)} samples). Submitting...")
                self._active_turn_task = asyncio.create_task(self._process_completed_speech(completed_audio))
                return {"status": "speech_captured", "samples": len(completed_audio)}

            return {"status": "listening", "is_speech": is_speech}

        return {"status": self.state.value}

    async def _process_completed_speech(self, audio_data: np.ndarray):
        """Process captured speech buffer: STT -> Directives / Brain -> TTS -> Auto-resume."""
        async with self._lock:
            self._interrupted = False
            try:
                # 1. State: TRANSCRIBING
                self.state = HandsFreeState.TRANSCRIBING
                await self.emit_event("RECORDING_STOPPED", {})

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

                # Handle empty / ambient noise transcription
                if not transcript or len(transcript) < 2:
                    self._consecutive_empty_turns += 1
                    logger.debug(f"Empty speech segment ({self._consecutive_empty_turns} turns).")

                    # If empty turn occurs 2 times or in wake-word-only mode, drop to standby
                    if self._consecutive_empty_turns >= 2 or self.mode == ConversationMode.WAKE_WORD_ONLY:
                        logger.info("Empty speech threshold reached; returning to wake-word standby.")
                        self.state = HandsFreeState.IDLE
                        self._consecutive_empty_turns = 0
                        vad_engine.reset()
                        await self.emit_event("LISTENING_RESUMED", {"reason": "empty_timeout"})
                    else:
                        self.state = HandsFreeState.LISTENING
                        self._listening_start_time = time.time()
                        vad_engine.reset()
                        await self.emit_event("RECORDING_STARTED", {"reason": "resume_empty"})
                    return

                # Valid speech received: reset empty turn counter
                self._consecutive_empty_turns = 0

                await self.emit_event("TRANSCRIPT_READY", {
                    "text": transcript,
                    "language": stt_result.get("detected_language", "en")
                })
                await self.emit_event("TRANSCRIPT_GENERATED", {
                    "text": transcript,
                    "language": stt_result.get("detected_language", "en")
                })

                from core.brain import brain
                from core.orchestrator import orchestrator
                from core.agent_coordinator import agent_coordinator

                # 2. Check for Immediate Voice Directives
                lower_text = transcript.lower().strip()
                import re
                clean_text = re.sub(r'[^\w\s]', ' ', lower_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                # Directive A: Stop / Interruption
                stop_cmds = ["matrix stop", "stop", "cancel", "chup", "ruko", "quiet", "silence", "abort"]
                if clean_text in stop_cmds or any(clean_text.startswith(cmd + " ") or clean_text.endswith(" " + cmd) or (" " + cmd + " ") in clean_text for cmd in stop_cmds):
                    await self.interrupt()
                    return

                # Directive B: Cancel that task
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix cancel that task", "cancel that task", "cancel task", "stop task",
                    "matrix cancel the current task", "cancel the current task"
                ]):
                    orchestrator.cancel_active()
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": "Task cancelled, sir."})
                    ack_audio = await tts_engine.speak("Task has been cancelled, sir.")
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                # Directive C: Go to sleep
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in ["matrix go to sleep", "go to sleep", "sleep", "so jao"]):
                    self.set_mode(ConversationMode.WAKE_WORD_ONLY)
                    self.state = HandsFreeState.SLEEPING
                    await self.emit_event("SPEAKING", {"text": "Going to sleep, sir."})
                    ack_audio = await tts_engine.speak("Going to sleep, sir. Say Matrix or Snap whenever you need me.")
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                # Directive D: Listen / Continuous Listening
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix listen", "listen", "suno", "continue listening",
                    "matrix continue listening after answering", "continue listening after answering"
                ]):
                    self.set_mode(ConversationMode.CONTINUOUS)
                    self.state = HandsFreeState.LISTENING
                    self._listening_start_time = time.time()
                    vad_engine.reset()
                    await self.emit_event("RECORDING_STARTED", {"reason": "explicit_listen"})
                    return

                # Directive E: What are you doing?
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix what are you doing", "what are you doing", "kya kar rahe ho",
                    "matrix explain what you are currently doing", "explain what you are currently doing"
                ]):
                    dashboard = agent_coordinator.get_agent_dashboard()
                    recent = dashboard.get("recent_tasks_count", 0)
                    msg = f"System is fully operational, sir. All 16 agents are standing by, with {recent} tasks recorded in this session."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                # AirTouch Gesture & Eye Directives
                from vision.airtouch.service import airtouch_service
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix start gesture control", "start gesture control",
                    "matrix activate hand control", "activate hand control", "start hand control"
                ]):
                    airtouch_service.set_mode("GESTURE_3D")
                    msg = "Hand control activated, sir. You can rotate 3D objects with hand gestures."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix activate gesture scroll", "activate gesture scroll",
                    "start gesture scroll", "activate touchless scroll"
                ]):
                    airtouch_service.set_mode("GESTURE_SCROLL")
                    msg = "Gesture scroll activated, sir. Use open palm to scroll, closed fist to lock."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix stop scrolling", "stop scrolling", "stop gesture scroll", "stop gesture control"
                ]):
                    airtouch_service.set_mode("OFF")
                    msg = "Gesture control has been stopped, sir."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix activate eye control", "activate eye control", "start eye control", "activate eye tracking"
                ]):
                    airtouch_service.set_mode("GESTURE_EYE")
                    msg = "Eye control activated, sir. GesturEye tracking and dwell click are online."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix reset 3d view", "reset 3d view", "matrix reset 3d", "reset 3d"
                ]):
                    airtouch_service.reset_3d()
                    msg = "3D hologram orientation has been reset to default identity, sir."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix calibrate eye tracking", "calibrate eye tracking", "calibrate eye"
                ]):
                    cal_res = airtouch_service.calibrate_eye()
                    msg = f"Eye calibration initiated, sir. Focus on the {cal_res.get('target', 'screen')} target."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix scroll down", "scroll down", "matrix scroll up", "scroll up"
                ]):
                    direction = "DOWN" if "down" in lower_text else "UP"
                    try:
                        import pyautogui
                        clicks = -250 if direction == "DOWN" else 250
                        pyautogui.scroll(clicks)
                    except Exception:
                        pass
                    msg = f"Scrolling {direction.lower()}, sir."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if "scroll speed" in lower_text:
                    speed = "HIGH" if "high" in lower_text else ("LOW" if "low" in lower_text else "MEDIUM")
                    airtouch_service.update_settings({"scroll_speed": speed})
                    msg = f"Gesture scroll speed set to {speed.lower()}, sir."
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in [
                    "matrix what am i looking at", "what am i looking at",
                    "matrix what do you see", "what do you see",
                    "matrix describe this scene", "describe this scene"
                ]):
                    from vision.camera.capture import camera_capture
                    import cv2
                    c_res = camera_capture.capture_frame()
                    if c_res.get("success") and c_res.get("filepath"):
                        f_img = cv2.imread(c_res["filepath"])
                    else:
                        f_img = np.zeros((480, 640, 3), dtype=np.uint8)
                    v_res = airtouch_service.modern_ai.answer_visual_query(f_img, lower_text)
                    msg = v_res.get("response", "Visual perception complete, sir.")
                    self.state = HandsFreeState.SPEAKING
                    await self.emit_event("SPEAKING", {"text": msg})
                    ack_audio = await tts_engine.speak(msg)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {"audio_file": ack_audio.name if ack_audio else None})
                    return

                # Directive F: Open browser
                if any(lower_text == cmd or lower_text.startswith(cmd) for cmd in ["matrix open my browser", "open my browser", "open browser"]):
                    self.state = HandsFreeState.SPEAKING
                    ack_audio = await tts_engine.speak("Opening browser now, sir.")
                    await brain.interact("Open browser", session_id=self.active_session_id)
                    self.state = HandsFreeState.IDLE
                    await self.emit_event("LISTENING_RESUMED", {})
                    return

                # 3. State: THINKING -> PLANNING -> EXECUTING
                self.state = HandsFreeState.THINKING
                await self.emit_event("THINKING", {"prompt": transcript})

                self.state = HandsFreeState.EXECUTING
                await self.emit_event("EXECUTING", {"prompt": transcript})

                response_text = await brain.interact(
                    user_prompt=transcript,
                    session_id=self.active_session_id
                )
                self.last_response = response_text
                await self.emit_event("BRAIN_RESPONSE", {"text": response_text[:300]})

                if self._interrupted:
                    logger.info("Turn execution was interrupted before speaking.")
                    return

                # 4. State: SPEAKING (TTS Generation & Playback)
                self.state = HandsFreeState.SPEAKING
                await self.emit_event("SPEAKING", {"text": response_text[:120]})

                # Keep voice output concise: synthesize up to 250 characters for fast speech
                tts_text = response_text.strip()
                if len(tts_text) > 250:
                    sentences = re.split(r'(?<=[.!?])\s+', tts_text)
                    if sentences:
                        candidate = sentences[0]
                        if len(candidate) < 150 and len(sentences) > 1:
                            candidate += " " + sentences[1]
                        tts_text = candidate[:250]

                await self.emit_event("TTS_STARTED", {"text": tts_text})
                audio_file = await tts_engine.speak(tts_text)
                self.last_audio_file = audio_file
                await self.emit_event("TTS_FINISHED", {"audio_file": audio_file.name if audio_file else None})

                # 5. Transition back: Auto-resume listening with timeout in CONTINUOUS, or return to IDLE
                if not self._interrupted:
                    if self.mode == ConversationMode.CONTINUOUS:
                        self.state = HandsFreeState.LISTENING
                        self._listening_start_time = time.time()
                        vad_engine.reset()
                        await self.emit_event("LISTENING_RESUMED", {
                            "reason": "continuous_resume",
                            "mode": "continuous"
                        })
                        await self.emit_event("RECORDING_STARTED", {
                            "reason": "continuous_resume",
                            "audio_file": audio_file.name if audio_file else None
                        })
                    else:
                        self.state = HandsFreeState.IDLE
                        await self.emit_event("LISTENING_RESUMED", {
                            "audio_file": audio_file.name if audio_file else None
                        })

            except asyncio.CancelledError:
                logger.info("Speech turn task was cancelled.")
                self.state = HandsFreeState.IDLE
            except Exception as e:
                logger.error(f"Error in speech processing turn: {e}", exc_info=True)
                self.state = HandsFreeState.ERROR
                await self.emit_event("ERROR", {"error": str(e)})
                await asyncio.sleep(1.0)
                self.state = HandsFreeState.IDLE


# Global Hands-Free Manager singleton
hands_free_manager = HandsFreeManager()
conversation_manager = hands_free_manager
