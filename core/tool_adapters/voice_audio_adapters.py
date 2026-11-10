"""MATRIX Voice & Audio Adapters.
Dedicated adapters for 5 repositories:
1. resemble-ai/chatterbox
2. SaarthurR/atticus-mac
3. OpenWhispr/openwhispr
4. k2-fsa/OmniVoice
5. cjpais/Handy
"""
import time
from pathlib import Path
from typing import Dict, Any, List
from core.tool_adapters.base_adapter import BaseAdapter, AdapterExecutionResult, unimplemented_result


class ChatterboxAcousticsAdapter(BaseAdapter):
    """Adapter for resemble-ai/chatterbox (Acoustic modeling & emotional speech synthesis)."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_chatterbox",
            name="Chatterbox Acoustics Adapter",
            description="Emotional prosody modeling, voice timbre modulation, and acoustic synthesis.",
            source_repo="resemble-ai/chatterbox",
            category="Voice & Audio",
            version="1.0.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["synthesize_speech", "transcribe_audio", "voice_cloning", "audio_filter"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "synthesize_speech": {"text": "string", "emotion": "string"},
            "transcribe_audio": {"audio_path": "string"},
            "voice_cloning": {"reference_wav": "string"},
            "audio_filter": {"filter_type": "string"}
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "synthesize_speech": {"audio_buffer_bytes": "integer", "duration_sec": "float"},
            "transcribe_audio": {"transcript": "string"},
            "voice_cloning": {"embedding_dim": "integer"},
            "audio_filter": {"applied": "boolean"}
        }

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        op = operation.lower().strip()

        if op == "synthesize_speech":
            text = parameters.get("text", "System ready.")
            emotion = parameters.get("emotion", "calm_authoritative")
            try:
                from voice.text_to_speech.engine import tts_engine

                audio_path = await tts_engine.speak(text=text, play_audio=False)
            except Exception as exc:
                latency = (time.perf_counter() - start_time) * 1000
                return unimplemented_result(
                    self.adapter_id,
                    operation,
                    f"local TTS backend raised: {exc}",
                    latency,
                )

            if not audio_path or not Path(audio_path).exists():
                latency = (time.perf_counter() - start_time) * 1000
                return unimplemented_result(
                    self.adapter_id,
                    operation,
                    "no audio file was produced (offline TTS backend unavailable)",
                    latency,
                )

            duration = None
            try:
                import soundfile as sf

                duration = round(float(sf.info(str(audio_path)).duration), 2)
            except Exception:
                duration = None

            latency = (time.perf_counter() - start_time) * 1000
            return AdapterExecutionResult(
                success=True,
                adapter_id=self.adapter_id,
                operation=operation,
                data={
                    "audio_path": str(audio_path),
                    "size_bytes": Path(audio_path).stat().st_size,
                    "duration_sec": duration,
                    "emotion": emotion,
                },
                verification={
                    "audio_file_exists": True,
                    "duration_measured": duration is not None,
                },
                execution_time_ms=round(latency, 2),
            )
        elif op == "transcribe_audio":
            latency = (time.perf_counter() - start_time) * 1000
            return unimplemented_result(
                self.adapter_id, operation, "'transcribe_audio' has no real backend wired in this build", latency
            )
        elif op == "voice_cloning":
            latency = (time.perf_counter() - start_time) * 1000
            return unimplemented_result(
                self.adapter_id, operation, "'voice_cloning' has no real backend wired in this build", latency
            )
        else:  # audio_filter
            latency = (time.perf_counter() - start_time) * 1000
            return unimplemented_result(
                self.adapter_id, operation, "'audio_filter' has no real backend wired in this build", latency
            )


class AtticusAudioAdapter(BaseAdapter):
    """Adapter for SaarthurR/atticus-mac (Low-latency audio streaming & native audio capture)."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_atticus_mac",
            name="Atticus Audio Stream Adapter",
            description="Ultra low-latency audio capture buffers and stream processing.",
            source_repo="SaarthurR/atticus-mac",
            category="Voice & Audio",
            version="1.0.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["synthesize_speech", "transcribe_audio", "voice_cloning", "audio_filter"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"audio_filter": {"buffer_size": "integer"}}

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"audio_filter": {"latency_ms": "float"}}

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        latency = (time.perf_counter() - start_time) * 1000
        return unimplemented_result(
            self.adapter_id, operation, "operation has no real backend wired in this build", latency
        )


class OpenWhisprAdapter(BaseAdapter):
    """Adapter for OpenWhispr/openwhispr (Fast offline speech recognition & whisper streaming)."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_openwhispr",
            name="OpenWhispr Fast STT Adapter",
            description="Fast AVX2-accelerated Whisper transcription and voice activity filtering.",
            source_repo="OpenWhispr/openwhispr",
            category="Voice & Audio",
            version="1.0.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["synthesize_speech", "transcribe_audio", "voice_cloning", "audio_filter"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"transcribe_audio": {"audio_data": "string"}}

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"transcribe_audio": {"text": "string"}}

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        latency = (time.perf_counter() - start_time) * 1000
        return unimplemented_result(
            self.adapter_id, operation, "operation has no real backend wired in this build", latency
        )


class OmniVoiceSynthesisAdapter(BaseAdapter):
    """Adapter for k2-fsa/OmniVoice (Universal multi-lingual text-to-speech engine)."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_omnivoice",
            name="OmniVoice Universal TTS Adapter",
            description="Multi-dialect speech generation, expressive voice inflection, and phoneme synthesis.",
            source_repo="k2-fsa/OmniVoice",
            category="Voice & Audio",
            version="1.0.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["synthesize_speech", "transcribe_audio", "voice_cloning", "audio_filter"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"synthesize_speech": {"text": "string", "lang": "string"}}

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"synthesize_speech": {"waveform_frames": "integer"}}

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        latency = (time.perf_counter() - start_time) * 1000
        return unimplemented_result(
            self.adapter_id, operation, "operation has no real backend wired in this build", latency
        )


class HandyVoiceAssistantAdapter(BaseAdapter):
    """Adapter for cjpais/Handy (Hands-free voice assistant integration and background hotword)."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_handy",
            name="Handy Voice Control Adapter",
            description="Continuous hands-free voice loop, background hotkey triggers, and audio event daemon.",
            source_repo="cjpais/Handy",
            category="Voice & Audio",
            version="1.0.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["synthesize_speech", "transcribe_audio", "voice_cloning", "audio_filter"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"audio_filter": {"hotword": "string"}}

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"audio_filter": {"hotword_listening": "boolean"}}

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        latency = (time.perf_counter() - start_time) * 1000
        return unimplemented_result(
            self.adapter_id, operation, "operation has no real backend wired in this build", latency
        )
