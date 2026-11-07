"""MATRIX Voice Agent.
Coordinates voice recognition, speech synthesis, volume controls, and Hindi/English dialog.
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

        # 1. Synthesize Speech
        if "speak" in action_lower or "say" in action_lower:
            text = parameters.get("text", parameters.get("query", "MATRIX Voice active."))
            audio_path = await tts_engine.speak(text)
            latency = (time.perf_counter() - start_time) * 1000
            verified = audio_path is not None and audio_path.exists()
            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="synthesize_speech",
                data={"audio_file": str(audio_path) if audio_path else None, "text": text},
                verification={"audio_created": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )

        # 2. Toggle Listening
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
