"""MATRIX Acoustic Finger Snap Detector Verification Script (PART 11, Test 3).
Tests physical finger-snap acoustic transient detection:
- Tests transient detection on synthetic finger-snap pulse (high peak, high crest factor, sharp rise)
- Verifies rejection of continuous speech and background white noise (zero false alarms)
- Verifies refractory cooldown period (1.2s) preventing duplicate activations
- Verifies Realtek 16kHz audio buffer compatibility
"""
import sys
import time
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.snap_detector import AcousticSnapDetector


def run_finger_snap_test():
    print("=" * 70)
    print("  MATRIX ACOUSTIC FINGER-SNAP DETECTOR TEST (PART 11, SCRIPT 3)")
    print("=" * 70)

    stages_passed = 0
    total_stages = 4
    detector = AcousticSnapDetector(sample_rate=16000, min_peak=3000, min_crest_factor=4.0)

    # Stage 1: Positive Detection on Realistic Finger Snap Impulse
    print("\n[STAGE 1/4] Testing acoustic transient detector with synthetic finger snap...")
    snap_audio = np.zeros(1280, dtype=np.int16)
    t = np.arange(480)  # 30ms snap transient + ring at 16kHz
    impulse = (7000.0 * np.exp(-t / 50.0) * np.sin(2 * np.pi * 3200 * t / 16000.0)).astype(np.int16)
    snap_audio[200:680] = impulse

    is_detected = detector.process_audio_frame(snap_audio)
    metrics = detector.last_metrics
    if is_detected:
        print(f"  [PASS] Finger snap correctly detected! Peak: {metrics.get('peak')}, Crest Factor: {metrics.get('crest_factor')}, ZCR: {metrics.get('zcr')}")
        stages_passed += 1
    else:
        print(f"  [FAIL] Finger snap transient was not detected. Metrics: {metrics}")
        return False

    # Stage 2: Cooldown Refractory Period Verification
    print("\n[STAGE 2/4] Testing refractory cooldown period (1.2s)...")
    # Immediate second snap should be rejected by cooldown
    is_second_detected = detector.process_audio_frame(snap_audio)
    if not is_second_detected and detector.is_cooling_down():
        print(f"  [PASS] Refractory period properly blocked immediate duplicate detection.")
        stages_passed += 1
    else:
        print(f"  [FAIL] Cooldown guard failed (detected: {is_second_detected}).")
        return False

    # Stage 3: False Positive Rejection on Continuous Speech
    print("\n[STAGE 3/4] Testing rejection of continuous human speech...")
    time.sleep(1.3)  # Wait for cooldown to expire
    t_speech = np.arange(1280)
    speech_wave = (2500.0 * np.sin(2 * np.pi * 200 * t_speech / 16000.0) +
                   1500.0 * np.sin(2 * np.pi * 400 * t_speech / 16000.0)).astype(np.int16)

    is_speech_snap = detector.process_audio_frame(speech_wave)
    s_metrics = detector.last_metrics
    if not is_speech_snap:
        print(f"  [PASS] Continuous speech properly rejected. Crest Factor: {s_metrics.get('crest_factor')} (< 4.0 threshold)")
        stages_passed += 1
    else:
        print(f"  [FAIL] Speech was falsely classified as a snap.")
        return False

    # Stage 4: False Positive Rejection on Background White Noise
    print("\n[STAGE 4/4] Testing rejection of background noise and ambient sound...")
    ambient_noise = np.random.randint(-800, 800, size=1280, dtype=np.int16)
    is_noise_snap = detector.process_audio_frame(ambient_noise)
    n_metrics = detector.last_metrics
    if not is_noise_snap:
        print(f"  [PASS] Background ambient noise correctly ignored. Peak: {n_metrics.get('peak')} (< 3000 threshold)")
        stages_passed += 1
    else:
        print(f"  [FAIL] Noise falsely classified as snap.")
        return False

    print("\n" + "=" * 70)
    print(f"RESULT: {stages_passed}/{total_stages} stages passed. Status: PASS")
    print("=" * 70)
    return stages_passed == total_stages


if __name__ == "__main__":
    success = run_finger_snap_test()
    sys.exit(0 if success else 1)
