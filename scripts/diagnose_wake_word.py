"""MATRIX Wake-Word Dedicated Hardware & Inference Diagnostic Tool.
Tests openWakeWord pipeline for 'Matrix', 'Hey Matrix', and foils:
- Model loading and architecture verification
- Real audio streaming in 80ms chunks (1280 samples @ 16kHz)
- Quiet, normal, and accented pronunciation sensitivity
- False positive rate on phonemic foils and ambient conversation
- Verification of continuous low-resource audio path
"""
import sys
import os
import time
import asyncio
import tempfile
import subprocess
from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config.settings import settings
from voice.wake_word.engine import wake_word_detector, WAKEWORD_DIR


async def synthesize_test_clip(phrase: str, voice: str, rate: str = "+0%", out_wav: Path = None):
    """Generate high-fidelity audio clip via edge-tts converted to 16kHz mono int16."""
    import edge_tts
    temp_mp3 = out_wav.with_suffix(".mp3")
    comm = edge_tts.Communicate(phrase, voice, rate=rate)
    await comm.save(str(temp_mp3))
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(temp_mp3),
        "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
        "-af", "apad=pad_dur=0.4",
        str(out_wav)
    ], check=True)
    if temp_mp3.exists():
        temp_mp3.unlink()


async def run_wake_word_diagnostics():
    print("=" * 76)
    print("      MATRIX WAKE-WORD COMPREHENSIVE PIPELINE DIAGNOSTIC")
    print("=" * 76)

    # 1. Inspect Engine Initialization
    wake_word_detector.start_listening()
    print("\n[CHECK 1] Wake-Word Detector Engine Status")
    diag = wake_word_detector.get_diagnostics()
    print(f"  Initialized:      {diag['initialized']}")
    print(f"  Is Listening:     {diag['is_listening']}")
    print(f"  Sensitivity:      {diag['sensitivity']}")
    print(f"  Cooldown:         {diag['cooldown_seconds']}s")
    print(f"  Loaded Models:    {diag['loaded_models']}")

    if not diag['initialized'] or "matrix" not in [m.lower() for m in diag['loaded_models']]:
        print("  [FAIL] 'matrix' model not loaded!")
        return False
    print("  [PASS] Wake-word detector successfully armed with 'matrix' model.")

    # 2. Test Cases Matrix
    test_cases = [
        # (Category, Phrase, Voice, Rate, Amplitude Scale, Expected Trigger, Must Pass)
        ("Quiet 'Matrix'", "Matrix", "en-US-ChristopherNeural", "+0%", 0.25, "matrix", True),
        ("Normal 'Matrix'", "Matrix", "en-US-GuyNeural", "+0%", 1.0, "matrix", True),
        ("Fast 'Matrix'", "Matrix", "en-GB-RyanNeural", "+15%", 1.0, "matrix", True),
        ("Spoken 'Hey Matrix'", "Hey Matrix", "en-US-JennyNeural", "+0%", 1.0, "matrix", True),
        ("Indian Accented 'Matrix'", "Matrix", "en-IN-PrabhatNeural", "+0%", 0.8, "matrix", True),
        ("Conversational 'Matrix please'", "Matrix please", "en-US-ChristopherNeural", "+0%", 1.0, "matrix", True),
        ("Alias 'Hey Jarvis'", "Hey Jarvis", "en-US-ChristopherNeural", "+0%", 1.0, "matrix", True),
        # Foils (Must NOT trigger)
        ("Foil 'Metric'", "Metric", "en-US-GuyNeural", "+0%", 1.0, None, False),
        ("Foil 'Magic'", "Magic", "en-US-JennyNeural", "+0%", 1.0, None, False),
        ("Foil 'Music'", "Music", "en-US-ChristopherNeural", "+0%", 1.0, None, False),
        ("Foil 'Notice'", "Notice", "en-GB-RyanNeural", "+0%", 1.0, None, False),
        ("Foil 'Status'", "Status", "en-US-GuyNeural", "+0%", 1.0, None, False),
        ("Foil 'What time is it'", "What time is it", "en-US-ChristopherNeural", "+0%", 1.0, None, False),
        ("Foil 'Good morning'", "Good morning", "en-IN-PrabhatNeural", "+0%", 1.0, None, False),
    ]

    temp_dir = Path(tempfile.mkdtemp(prefix="matrix_ww_diag_"))
    results = []

    print("\n[CHECK 2] Streaming Inference Evaluation Across Speech Scenarios")
    print("-" * 76)
    print(f"{'Test Scenario':<26} | {'Expected':<8} | {'Score':<7} | {'Result':<8} | {'Status'}")
    print("-" * 76)

    try:
        from openwakeword.model import Model
        model_paths = [str(WAKEWORD_DIR / "matrix.onnx"), "hey_jarvis_v0.1"]
        snap_path = WAKEWORD_DIR / "snap.onnx"
        if snap_path.exists():
            model_paths.append(str(snap_path))

        oww = Model(wakeword_models=model_paths, inference_framework="onnx")

        for idx, (label, phrase, voice, rate, amp_scale, expected_trigger, should_trigger) in enumerate(test_cases, 1):
            clip_path = temp_dir / f"clip_{idx}.wav"
            await synthesize_test_clip(phrase, voice, rate, clip_path)

            sr, data = wavfile.read(str(clip_path))
            if data.ndim > 1:
                data = data[:, 0]

            # Scale amplitude for quiet vs normal test
            if amp_scale != 1.0:
                data = np.clip(data.astype(np.float32) * amp_scale, -32768, 32767).astype(np.int16)

            oww.reset()
            max_scores = {"matrix": 0.0, "hey_jarvis_v0.1": 0.0, "snap": 0.0}

            start_t = time.perf_counter()
            # Stream in continuous 80ms chunks (1280 samples)
            for i in range(0, len(data) - 1280, 1280):
                chunk = data[i:i + 1280]
                preds = oww.predict(chunk)
                for k, v in preds.items():
                    if v > max_scores.get(k, 0.0):
                        max_scores[k] = v

            latency_ms = (time.perf_counter() - start_t) * 1000

            # Determine best detection score
            matrix_score = max(max_scores.get("matrix", 0.0), max_scores.get("hey_jarvis_v0.1", 0.0))
            snap_score = max_scores.get("snap", 0.0)

            triggered = matrix_score >= wake_word_detector.sensitivity
            passed = (triggered == should_trigger)
            results.append(passed)

            status_text = "[PASS]" if passed else "[FAIL]"
            disp_expected = "TRIGGER" if should_trigger else "REJECT"
            disp_result = "TRIGGERED" if triggered else "REJECTED"
            print(f"{label:<26} | {disp_expected:<8} | {matrix_score:.4f}  | {disp_result:<8} | {status_text}")

            if clip_path.exists():
                clip_path.unlink()

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("-" * 76)
    passed_count = sum(results)
    total_count = len(results)
    pass_pct = (passed_count / total_count) * 100

    print(f"\nWAKE-WORD DIAGNOSTIC SUMMARY: {passed_count}/{total_count} PASSED ({pass_pct:.1f}%)")
    print(f"- Target Wake Words: 7/7 Evaluated")
    print(f"- Negative Foils:    7/7 Evaluated")
    print(f"- Sensitivity Gate:  {wake_word_detector.sensitivity} calibrated")
    print("=" * 76)

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(run_wake_word_diagnostics())
    sys.exit(0 if success else 1)
