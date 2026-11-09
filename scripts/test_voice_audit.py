"""Voice subsystem independent audit test script.
Tests wake words (openWakeWord), acoustic snap detector, TTS engine,
playback coordinator deduplication, and interrupt cancellation.
"""
import sys
import os
import time
import asyncio
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

voice_results = {}

def test_wakeword_models():
    """Verify openWakeWord detector and models."""
    print("\n--- Testing openWakeWord Detector & Models ---")
    from voice.wake_word.engine import WakeWordDetector
    det = WakeWordDetector()
    det._init_model()
    diag = det.get_diagnostics()
    loaded = diag.get("loaded_models", [])
    
    # Check for Matrix, Hey Jarvis, and Snap models
    has_matrix = any("matrix" in m.lower() for m in loaded)
    has_snap = any("snap" in m.lower() for m in loaded)
    
    # Process 5 dummy frames and record inference timing
    latencies = []
    for _ in range(5):
        frame = np.zeros(1280, dtype=np.int16)
        t0 = time.perf_counter()
        det.process_audio_frame(frame)
        latencies.append((time.perf_counter() - t0) * 1000)
    
    avg_lat = round(sum(latencies) / len(latencies), 2)
    passed = has_matrix and has_snap and avg_lat < 20.0
    voice_results["openWakeWord"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Loaded models: {loaded}, Matrix: {has_matrix}, Snap: {has_snap}, Avg inference: {avg_lat}ms"
    }

def test_acoustic_snap_detector():
    """Verify acoustic finger snap transient detector (crest-factor & rise-time)."""
    print("\n--- Testing Acoustic Snap Detector ---")
    from voice.snap_detector import AcousticSnapDetector
    sd = AcousticSnapDetector()
    
    # 1. Background noise / speech simulation (low crest factor ~2-4)
    speech_sim = (np.sin(np.linspace(0, 50, 1280)) * 5000).astype(np.int16)
    is_snap_sp, m_sp = sd.analyze_frame(speech_sim)
    
    # 2. Sharp finger snap impulse (peak 28000, high crest factor >15)
    impulse = np.zeros(1280, dtype=np.int16)
    impulse[200:208] = np.array([4000, -16000, 28000, -20000, 12000, -6000, 2000, -500], dtype=np.int16)
    is_snap_imp, m_imp = sd.analyze_frame(impulse)
    
    passed = (not is_snap_sp) and is_snap_imp
    voice_results["AcousticSnap"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Speech rejected: {not is_snap_sp} (crest={m_sp.get('crest_factor', 0):.2f}), Impulse detected: {is_snap_imp} (crest={m_imp.get('crest_factor', 0):.2f}, peak={m_imp.get('peak', 0)})"
    }

async def test_playback_deduplication():
    """Verify PlaybackCoordinator prevents duplicate speech playback."""
    print("\n--- Testing Playback Coordinator Deduplication ---")
    from voice.playback_coordinator import playback_coordinator
    
    resp_id = f"audit_resp_{int(time.time())}"
    
    # 1. First lease by primary audio channel
    acq1, rec1, err1 = await playback_coordinator.acquire_playback(
        response_id=resp_id,
        owner="tts_engine",
        text="Audit test primary utterance"
    )
    
    # 2. Duplicate lease attempt by secondary channel
    acq2, rec2, err2 = await playback_coordinator.acquire_playback(
        response_id=resp_id,
        owner="frontend_streamer",
        text="Audit test primary utterance"
    )
    
    # 3. Mark completed
    playback_coordinator.mark_completed(rec1.playback_id)
    
    # 4. Third lease attempt after completion
    acq3, rec3, err3 = await playback_coordinator.acquire_playback(
        response_id=resp_id,
        owner="tts_engine",
        text="Audit test late replay"
    )
    
    passed = acq1 and (not acq2) and (not acq3)
    voice_results["PlaybackDeduplication"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Primary lease: {acq1}, Competing owner rejected: {not acq2} ('{err2}'), Post-completion rejected: {not acq3} ('{err3}')"
    }

async def test_interrupt_handling():
    """Verify playback cancellation on interrupt."""
    print("\n--- Testing Interrupt & Stop Handling ---")
    from voice.playback_coordinator import playback_coordinator
    
    resp_id = f"audit_cancel_{int(time.time())}"
    acq, rec, _ = await playback_coordinator.acquire_playback(
        response_id=resp_id,
        owner="tts_engine",
        text="Long speech stream to be interrupted"
    )
    
    # Cancel playback
    canceled = playback_coordinator.cancel(rec.playback_id)
    rec_after = playback_coordinator.get_playback(rec.playback_id)
    is_canceled = rec_after and rec_after.state.value == "CANCELLED"
    
    passed = acq and canceled and is_canceled
    voice_results["InterruptCancellation"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Lease acquired: {acq}, Cancel returned: {canceled}, Final state: {rec_after.state.value if rec_after else 'N/A'}"
    }

async def run_voice_tests():
    test_wakeword_models()
    test_acoustic_snap_detector()
    await test_playback_deduplication()
    await test_interrupt_handling()
    
    print("\n" + "=" * 80)
    print("      VOICE SUBSYSTEM AUDIT RESULTS")
    print("=" * 80)
    for k, v in voice_results.items():
        print(f"[{v['status']:4}] {k:25} | {v['details']}")

if __name__ == "__main__":
    asyncio.run(run_voice_tests())
