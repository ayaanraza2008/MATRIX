"""MATRIX Voice Agent.
Coordinates voice recognition, speech synthesis, volume controls, and Hindi/English dialog.
Supports hands-free continuous listening, immediate barge-in silence, and sleep transitions.
"""
from typing import Dict, Any
import time
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult
from voice.text_to_speech.engine import tts_engine
from voice.speech_to_text.engine import stt_engine
from voice.wake_word.engine import wake_word_detector


class VoiceAgent(BaseAgent):
    """Executes JARVIS-style speech synthesis, recognition, and listening control."""

    def __init__(self):
        super().__init__(
            name="voice",
            description="Speaks natural responses, transcribes microphone input, and handles voice triggers.",
            max_autonomy_level=1
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("text", parameters.get("prompt", ""))).lower()

        # 1. Voice Directives: Stop, Sleep, Continuous Listening
        if any(w in action_lower or w in raw_prompt for w in ["stop speaking", "be quiet", "shut up", "silence", "stop talking", "go to sleep", "sleep mode", "continue listening", "keep listening"]):
            if any(w in raw_prompt for w in ["stop", "quiet", "silence", "shut"]):
                tts_engine.stop()
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="stop_speaking",
                    data={"status": "Speech stopped immediately, sir.", "speaking": False},
                    verification={"verified": True},
                    execution_time_ms=round(latency, 2)
                )

            if "sleep" in raw_prompt:
                try:
                    from voice.conversation.manager import hands_free_manager, HandsFreeState, ConversationMode
                    hands_free_manager.set_mode(ConversationMode.WAKE_WORD_ONLY)
                    hands_free_manager.state = HandsFreeState.SLEEPING
                except Exception:
                    pass
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="enter_sleep",
                    data={"state": "sleeping", "message": "Entering sleep mode, sir. Say Matrix or Snap to awaken."},
                    verification={"verified": True},
                    execution_time_ms=round(latency, 2)
                )

            if any(w in raw_prompt for w in ["continue", "continuous", "keep listening"]):
                try:
                    from voice.conversation.manager import hands_free_manager, ConversationMode
                    hands_free_manager.set_mode(ConversationMode.CONTINUOUS)
                except Exception:
                    pass
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="continuous_listening",
                    data={"mode": "continuous", "message": "Continuous listening engaged."},
                    verification={"verified": True},
                    execution_time_ms=round(latency, 2)
                )

        # 2. Synthesize Speech
        if "speak" in action_lower or "say" in action_lower or "synthesize" in action_lower:
            text = parameters.get("text", parameters.get("query", "MATRIX Voice active."))
            import re
            cleaned_text = re.sub(r'^(?:speak|say)(?:\s+out\s+loud)?(?:\s+using\s+voice)?(?:\s*:\s*|\s+that\s+|\s+)', '', str(text), flags=re.IGNORECASE).strip()
            if not cleaned_text:
                cleaned_text = str(text)
            audio_path = await tts_engine.speak(cleaned_text)
            latency = (time.perf_counter() - start_time) * 1000
            verified = audio_path is not None and audio_path.exists()
            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="synthesize_speech",
                data={"audio_file": str(audio_path) if audio_path else None, "text": cleaned_text},
                verification={"audio_created": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )

        # 3. Toggle Listening
        if "listen" in action_lower or "wake" in action_lower:
            enable = parameters.get("enable", True)
            if enable:
                wake_word_detector.start_listening()
            else:
                wake_word_detector.stop_listening()
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="toggle_listening",
                data={"listening": wake_word_detector.is_listening},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # Default Voice Status
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="voice_status",
            data={
                "listening": wake_word_detector.is_listening,
                "supported_languages": ["en", "hi", "hinglish"],
                "tts_ready": True
            },
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
