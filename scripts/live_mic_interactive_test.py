"""MATRIX Interactive Real Microphone Hardware Test.
Guides the user through speaking:
1. "Hello Matrix, introduce yourself."
2. "Matrix, check my CPU usage."
Displays live audio metrics, transcribed text, Brain response, and speaker playback.
"""
import sys
import os
import time
import asyncio
from pathlib import Path
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from voice.speech_to_text.engine import stt_engine
from voice.text_to_speech.engine import tts_engine
from core.brain import brain


async def run_command_interaction(command_num: int, expected_prompt: str, duration: float = 4.5):
    in_dev = sd.default.device[0]
    out_dev = sd.default.device[1]
    in_name = sd.query_devices(in_dev)["name"]
    out_name = sd.query_devices(out_dev)["name"]
    sr = 16000

    print("\n" + "=" * 80)
    print(f"COMMAND {command_num}: PLEASE SPEAK INTO YOUR MICROPHONE")
    print(f"Target Phrase: \"{expected_prompt}\"")
    print("=" * 80)
    print(f"Microphone: [{in_dev}] {in_name}")
    print(f"Recording in 1 second for {duration} seconds... Please speak clearly.")
    await asyncio.sleep(1.0)

    print("\n>>> RECORDING NOW... SPEAK! <<<")
    raw = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='int16', device=in_dev)
    sd.wait()
    samples = raw[:, 0]
    peak = int(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
    is_non_silent = bool(rms > 12.0 or peak > 100)

    print(f"\n[1] CAPTURED AUDIO STATUS:")
    print(f"    - Buffer Size: {len(samples)} samples ({duration}s @ {sr}Hz)")
    print(f"    - Peak Amplitude: {peak} / 32,767 ({peak / 327.67:.1f}% FS)")
    print(f"    - RMS Energy: {rms:.2f}")
    print(f"    - Non-Silent: {'YES' if is_non_silent else 'NO (Audio was silent or muted)'}")

    if not is_non_silent:
        print("    [!] Warning: Microphone buffer was silent. Ensure Windows microphone is not hardware muted.")

    # Save to temp wav and transcribe
    tmp_dir = PROJECT_ROOT / "docs"
    tmp_dir.mkdir(exist_ok=True)
    wav_path = tmp_dir / f"live_test_cmd_{command_num}.wav"
    wavfile.write(str(wav_path), sr, samples)

    print("\n[2] RUNNING FASTER-WHISPER STT TRANSCRIPTION...")
    stt_res = await stt_engine.transcribe(wav_path)
    transcript = stt_res.get("text", "").strip()
    detected_lang = stt_res.get("detected_language", "en")
    print(f"    - Recognized Transcript: \"{transcript}\"")
    print(f"    - Detected Language: {detected_lang}")

    if not transcript:
        print("    [!] Notice: No words recognized. Check speech volume or speak closer to laptop mic.")
        return False

    print("\n[3] SUBMITTING TRANSCRIPT TO MATRIXBRAIN...")
    start_brain = time.perf_counter()
    brain_res = await brain.process_user_request(
        session_id=f"sess_live_user_test_{command_num}",
        user_prompt=transcript
    )
    brain_latency = (time.perf_counter() - start_brain) * 1000
    reply = brain_res.get("response", "")
    plan_status = brain_res.get("plan_status")
    print(f"    - Brain Response: \"{reply}\"")
    print(f"    - Plan Status: {plan_status}")
    print(f"    - Latency: {brain_latency:.2f} ms")

    print("\n[4] SYNTHESIZING & PLAYING AUDIO THROUGH SPEAKERS...")
    tts_spoken = reply[:250].strip()
    print(f"    - Output Device: [{out_dev}] {out_name}")
    print(f"    - Spoken Text: \"{tts_spoken}\"")
    audio_file = await tts_engine.speak(tts_spoken, play_audio=True)
    tts_ok = audio_file is not None and audio_file.exists()
    print(f"    - Playback Status: {'SUCCESS' if tts_ok else 'FAILED'}")
    return True


async def main():
    print("=" * 80)
    print("    MATRIX — LIVE USER MICROPHONE ACCEPTANCE SESSION")
    print("=" * 80)
    print("This session tests the two standard spoken commands:")
    print("  1. 'Hello Matrix, introduce yourself.'")
    print("  2. 'Matrix, check my CPU usage.'")
    print("=" * 80)

    # Command 1
    await run_command_interaction(1, "Hello Matrix, introduce yourself.", duration=4.5)
    await asyncio.sleep(2.0)

    # Command 2
    await run_command_interaction(2, "Matrix, check my CPU usage.", duration=4.0)

    print("\n" + "=" * 80)
    print("Live user test session completed.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
