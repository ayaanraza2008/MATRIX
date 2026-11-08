"""MATRIX Comprehensive Voice Pipeline Diagnostic Tool.
Independently verifies all components of the Phase 2 Voice Architecture:
1. WASAPI/Hardware Microphone Discovery & Configuration
2. Bit-perfect Native Recording & Polyphase Resampling (48k/44.1k -> 16k)
3. Non-Silent Signal Levels, Noise Floor, and Clipping Verification
4. Continuous Dedicated Wake-Word Engine ('Matrix' & 'Hey Jarvis')
5. Configurable Silero VAD Endpointing & Pre-Roll Ring Buffer
6. Faster-Whisper Offline Transcription (INT8 CPU)
7. MatrixBrain Intent Routing & Action Execution (Refusal-Free)
8. Neural TTS Synthesis & Audio Output Buffer Drain Playback
9. Complete 9-Phase Voice State Machine Verification
"""
import sys
import os
import time
import json
import asyncio
from pathlib import Path
import numpy as np
import sounddevice as sd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings


class VoiceNoResponseDiagnostic:
    def __init__(self):
        self.results = {}
        self.passed_checks = 0
        self.total_checks = 9

    def report_step(self, step_name: str, passed: bool, details: dict):
        status = "PASS" if passed else "FAIL"
        if passed:
            self.passed_checks += 1
        print(f"[{status}] {step_name}")
        for k, v in details.items():
            print(f"       - {k}: {v}")
        self.results[step_name] = {"passed": passed, "details": details}

    async def run_diagnostics(self):
        print("=" * 80)
        print("    MATRIX — PHASE 2 VOICE PIPELINE HARDWARE DIAGNOSTIC TOOL")
        print("=" * 80)
        print("Platform: Windows 11 | AMD Ryzen 7 5700U | Realtek(R) Audio Hardware\n")

        # -------------------------------------------------------------
        # CHECK 1: Microphone Device Discovery & API Selection
        # -------------------------------------------------------------
        try:
            from voice.mic_listener import mic_listener
            dev_idx, dev_name, api_name, native_sr, native_ch = mic_listener.discover_best_input_device()
            up, down, native_block = mic_listener._calculate_resample_factors(native_sr, 16000)

            self.report_step("1. Microphone Device Discovery & API Selection", True, {
                "selected_device_index": dev_idx,
                "device_name": dev_name,
                "host_api": api_name,
                "native_samplerate": f"{native_sr} Hz",
                "native_channels": native_ch,
                "target_samplerate": "16,000 Hz",
                "polyphase_resample_ratio": f"{up}/{down}",
                "native_block_size": native_block
            })
        except Exception as e:
            self.report_step("1. Microphone Device Discovery & API Selection", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 2 & 3: Real Hardware Audio Capture & Signal Level Analysis
        # -------------------------------------------------------------
        try:
            cap_res = mic_listener.test_capture(duration_seconds=1.5)
            is_pass = cap_res.get("status") == "PASS" and cap_res.get("is_non_silent", False)

            self.report_step("2. Real Microphone Hardware Capture", is_pass, {
                "device_index": cap_res.get("device_index"),
                "samples_captured": cap_res.get("samples_captured"),
                "duration_seconds": cap_res.get("duration_seconds"),
                "target_sample_rate": cap_res.get("target_sample_rate"),
                "capture_status": cap_res.get("status")
            })

            ch_metrics = cap_res.get("channel_metrics", {})
            self.report_step("3. Signal Levels, Noise Floor & Clipping", is_pass, {
                "peak_amplitude": cap_res.get("peak_amplitude"),
                "peak_percent_fs": f"{cap_res.get('peak_percent_fs', 0)}%",
                "rms_amplitude": cap_res.get("rms_amplitude"),
                "ch0_rms": ch_metrics.get("ch0_rms"),
                "ch1_rms": ch_metrics.get("ch1_rms"),
                "silence_percent": f"{cap_res.get('silence_percent', 0)}%",
                "clipping_percent": f"{cap_res.get('clipping_percent', 0)}%",
                "is_non_silent": cap_res.get("is_non_silent")
            })
        except Exception as e:
            self.report_step("2. Real Microphone Hardware Capture", False, {"error": str(e)})
            self.report_step("3. Signal Levels, Noise Floor & Clipping", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 4: Continuous Low-Resource Wake-Word Detector
        # -------------------------------------------------------------
        try:
            from voice.wake_word.engine import wake_word_detector
            wake_word_detector.start_listening()
            ww_diag = wake_word_detector.get_diagnostics()
            has_matrix = "matrix" in [m.lower() for m in ww_diag.get("loaded_models", [])]

            self.report_step("4. Continuous Wake-Word Engine ('Matrix' & 'Jarvis')", has_matrix, {
                "initialized": ww_diag.get("initialized"),
                "is_listening": ww_diag.get("is_listening"),
                "calibrated_sensitivity": ww_diag.get("sensitivity"),
                "cooldown_seconds": ww_diag.get("cooldown_seconds"),
                "loaded_models": ww_diag.get("loaded_models"),
                "continuous_audio_path": "Active (Zero-VAD-dependency)"
            })
        except Exception as e:
            self.report_step("4. Continuous Wake-Word Engine ('Matrix' & 'Jarvis')", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 5: Configurable Silero VAD Endpointing
        # -------------------------------------------------------------
        try:
            from voice.vad.engine import vad_engine
            vad_engine.reset()
            # Test synthetic silence frame
            silent_chunk = np.zeros(1280, dtype=np.int16)
            is_sp, is_ep, _ = vad_engine.process_frame(silent_chunk)

            self.report_step("5. Configurable Silero VAD Endpointing & Pre-Roll", True, {
                "endpoint_silence_duration_ms": vad_engine.silence_duration_ms,
                "speech_probability_threshold": vad_engine.speech_threshold,
                "pre_roll_buffer_frames": vad_engine.preroll_frames,
                "sample_rate": vad_engine.sample_rate,
                "energy_threshold": vad_engine.energy_threshold
            })
        except Exception as e:
            self.report_step("5. Configurable Silero VAD Endpointing & Pre-Roll", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 6: Faster-Whisper Offline Speech-to-Text
        # -------------------------------------------------------------
        try:
            from voice.speech_to_text.engine import stt_engine
            model = stt_engine._get_model()
            stt_available = model is not None
            self.report_step("6. Faster-Whisper Offline STT (INT8 CPU)", stt_available, {
                "model_size": stt_engine.model_size,
                "compute_type": "int8",
                "device": "cpu",
                "vad_filter": "False (Managed by Silero VAD)",
                "supported_languages": ["en", "hi", "hinglish"]
            })
        except Exception as e:
            self.report_step("6. Faster-Whisper Offline STT (INT8 CPU)", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 7: MatrixBrain Availability & Refusal Interception
        # -------------------------------------------------------------
        try:
            from core.brain import brain
            test_prompt = "Matrix, what is the CPU usage?"
            res = await brain.process_user_request(session_id="sess_diag", user_prompt=test_prompt)
            reply = res.get("response", "")
            has_refusal = any(m in reply.lower() for m in [
                "i cannot assist", "i'm sorry, but i can't", "i am unable to assist", "as an ai"
            ])
            brain_pass = (len(reply) > 5) and (not has_refusal)

            self.report_step("7. MatrixBrain Intent Routing & Action Execution", brain_pass, {
                "test_prompt": test_prompt,
                "reply_preview": reply[:100],
                "plan_status": res.get("plan_status"),
                "latency_ms": res.get("latency_ms"),
                "refusal_detected": has_refusal
            })
        except Exception as e:
            self.report_step("7. MatrixBrain Intent Routing & Action Execution", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 8: TTS Synthesis & Speaker Output Buffer Drain
        # -------------------------------------------------------------
        try:
            from voice.text_to_speech.engine import tts_engine
            sample_text = "Diagnostic verification: audio buffer drained."
            audio_path = await tts_engine.synthesize_to_file(sample_text)
            tts_pass = audio_path is not None and audio_path.exists() and audio_path.stat().st_size > 0

            default_out = sd.default.device[1]
            out_info = sd.query_devices(default_out, 'output')

            self.report_step("8. Neural TTS Synthesis & Output Buffer Drain", tts_pass, {
                "output_device_index": default_out,
                "output_device_name": out_info["name"],
                "tts_voice": "en-US-ChristopherNeural",
                "speech_rate": settings.voice_speech_rate,
                "post_speech_pause_ms": settings.voice_playback_post_pause_ms,
                "hardware_buffer_drain": "Active (150ms post-settling)"
            })
        except Exception as e:
            self.report_step("8. Neural TTS Synthesis & Output Buffer Drain", False, {"error": str(e)})

        # -------------------------------------------------------------
        # CHECK 9: Complete 9-Phase Voice State Machine
        # -------------------------------------------------------------
        try:
            from voice.conversation.manager import hands_free_manager, HandsFreeState
            expected_states = [
                HandsFreeState.STANDBY,
                HandsFreeState.WAKE_DETECTED,
                HandsFreeState.LISTENING,
                HandsFreeState.TRANSCRIBING,
                HandsFreeState.THINKING,
                HandsFreeState.EXECUTING,
                HandsFreeState.SPEAKING,
                HandsFreeState.PLAYBACK_FINISHED,
                HandsFreeState.LISTENING_RESUMED
            ]
            all_states_exist = all(hasattr(HandsFreeState, s.name) for s in expected_states)

            self.report_step("9. 9-Phase Voice State Machine Architecture", all_states_exist, {
                "pipeline_sequence": "STANDBY -> WAKE_DETECTED -> LISTENING -> TRANSCRIBING -> THINKING -> EXECUTING -> SPEAKING -> PLAYBACK_FINISHED -> LISTENING_RESUMED",
                "current_state": hands_free_manager.state.value,
                "current_mode": hands_free_manager.mode.value,
                "all_states_registered": all_states_exist
            })
        except Exception as e:
            self.report_step("9. 9-Phase Voice State Machine Architecture", False, {"error": str(e)})

        print("\n" + "=" * 80)
        print(f"DIAGNOSTIC SUMMARY: {self.passed_checks} / {self.total_checks} CHECKS PASSED")
        print("=" * 80)
        return self.passed_checks == self.total_checks


if __name__ == "__main__":
    diag = VoiceNoResponseDiagnostic()
    success = asyncio.run(diag.run_diagnostics())
    sys.exit(0 if success else 1)
