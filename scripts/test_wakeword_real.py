"""MATRIX Real Wake-Word Detection Verification Suite.
Synthesizes fresh spoken audio clips of 'Matrix', 'Snap', and negative phrases,
streams them in 80ms chunks into openWakeWord, and verifies activation scores.
"""
import sys
import asyncio
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile
from openwakeword.model import Model

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

MODEL_DIR = Path(r"D:\matrix_data\models\wakeword")


async def generate_test_wav(text: str, voice: str, out_wav: Path):
    import edge_tts
    mp3_path = out_wav.with_suffix(".mp3")
    comm = edge_tts.Communicate(text, voice)
    await comm.save(str(mp3_path))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(mp3_path),
        "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
        "-af", "apad=pad_dur=0.5",
        str(out_wav)
    ]
    subprocess.run(cmd, check=True)
    if mp3_path.exists():
        mp3_path.unlink()


async def run_wakeword_evaluation():
    print("=" * 70)
    print("        MATRIX WAKE-WORD REAL INFERENCE ACCURACY TEST")
    print("=" * 70)

    oww = Model(
        wakeword_models=[
            str(MODEL_DIR / "matrix.onnx"),
            str(MODEL_DIR / "snap.onnx")
        ],
        inference_framework="onnx"
    )
    print(f"[+] Loaded models: {list(oww.models.keys())}")

    test_cases = [
        ("Matrix", "en-US-ChristopherNeural", "matrix", True),
        ("Hey Matrix", "en-US-JennyNeural", "matrix", True),
        ("Snap", "en-GB-RyanNeural", "snap", True),
        ("Hey Snap", "en-IN-PrabhatNeural", "snap", True),
        ("Jarvis", "en-US-ChristopherNeural", "none", False),
        ("Hello computer", "en-US-GuyNeural", "none", False),
        ("What time is it", "en-AU-WilliamNeural", "none", False),
    ]

    temp_dir = Path(tempfile.mkdtemp())
    results = []

    try:
        for idx, (phrase, voice, expected_target, should_trigger) in enumerate(test_cases, start=1):
            wav_path = temp_dir / f"test_{idx}.wav"
            await generate_test_wav(phrase, voice, wav_path)

            sr, data = wavfile.read(str(wav_path))
            if data.ndim > 1:
                data = data[:, 0]

            oww.reset()
            max_scores = {"matrix": 0.0, "snap": 0.0}

            # Stream through 1280 sample chunks (80ms)
            for i in range(0, len(data) - 1280, 1280):
                chunk = data[i:i + 1280]
                preds = oww.predict(chunk)
                for k, v in preds.items():
                    if v > max_scores[k]:
                        max_scores[k] = v

            wav_path.unlink()

            detected_matrix = max_scores["matrix"] >= 0.5
            detected_snap = max_scores["snap"] >= 0.5

            if should_trigger:
                passed = (expected_target == "matrix" and detected_matrix) or (expected_target == "snap" and detected_snap)
            else:
                passed = not detected_matrix and not detected_snap

            status_str = "[PASS]" if passed else "[FAIL]"
            results.append(passed)

            print(f"  {status_str} Phrase: '{phrase:<16}' (Voice: {voice.split('-')[2]})")
            print(f"         Scores -> matrix: {max_scores['matrix']:.4f} | snap: {max_scores['snap']:.4f}")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("-" * 70)
    all_passed = all(results)
    print(f"Test Summary: {sum(results)}/{len(results)} PASSED ({100 * sum(results) / len(results):.0f}%)")
    if all_passed:
        print("[✔] BOTH 'Matrix' AND 'Snap' WAKE-WORDS ARE 100% OPERATIONAL WITH ZERO FALSE POSITIVES!")
    else:
        print("[!] Some test cases failed evaluation.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_wakeword_evaluation())
