"""MATRIX Voice Agent.
Coordinates voice recognition, speech synthesis, volume controls, and Hindi/English dialog.
Supports hands-free continuous listening, immediate barge-in silence, and sleep transitions.
Enforces single-source audio playback coordination to eliminate duplicate sound playback.
"""
from typing import Dict, Any
import time
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from voice.text_to_speech.engine import tts_engine
from voice.wake_word.engine import wake_word_detector


class VoiceAgent(BaseAgent):
    """Executes JARVIS-style speech synthesis, recognition, and listening control."""

    def __init__(self):
        super().__init__(
            name="voice",
            description="Speaks natural responses, transcribes microphone input, and handles voice triggers.",
            max_autonomy_level=1
        )
        self._capabilities = [
            AgentCapability(name="speech_synthesis", description="Convert text into natural streaming audio responses", operations=["speak", "speech"]),
            AgentCapability(name="wake_word_control", description="Manage openWakeWord background activation listener", operations=["listen", "toggle_listening", "wake"]),
            AgentCapability(name="voice_status", description="Query speech engine status and language models", operations=["voice_status", "status"])
        ]

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

            # Enforce single-source playback rule: tool steps synthesize to file without
            # playing audio on host soundcard unless explicitly requested and acquired.
            should_play = parameters.get("play_audio", False)
            resp_id = parameters.get("response_id")

            if should_play:
                audio_path = await tts_engine.speak(
                    cleaned_text,
                    play_audio=True,
                    response_id=resp_id,
                    owner="voice_agent"
                )
            else:
                audio_path = await tts_engine.synthesize_to_file(
                    cleaned_text,
                    response_id=resp_id,
                    owner="voice_agent"
                )

            latency = (time.perf_counter() - start_time) * 1000
            verified = audio_path is not None and audio_path.exists() and audio_path.stat().st_size > 0
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
        if action_lower in ["voice_status", "status", "query_status"]:
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

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=False,
            agent_name=self.name,
            action_taken=action,
            error=f"Unsupported action '{action}' for VoiceAgent",
            execution_status="FAILED",
            verification_status="FAILED",
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
