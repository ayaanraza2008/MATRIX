"""Test live hardware microphone using NativeMicListener.test_capture() and background listener."""
import sys
import time
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from voice.mic_listener import NativeMicListener

def run_mic_test():
    print("=" * 80)
    print("      LIVE MICROPHONE HARDWARE VERIFICATION (NativeMicListener)")
    print("=" * 80)

    listener = NativeMicListener()
    
    # 1. Run test_capture (synchronous 1.5s hardware sample)
    print("\n--- 1. Synchronous Hardware Test Capture (1.5 seconds) ---")
    res = listener.test_capture(duration_seconds=1.5)
    print("Capture Result:", json.dumps(res, indent=2))
    
    # 2. Run background listener
    print("\n--- 2. Background Stream Listener (3 seconds) ---")
    listener.start()
    for i in range(3):
        time.sleep(1.0)
        diag = listener.get_diagnostics()
        print(f"Sec {i+1}: Device=[{diag['active_device_index']}] {diag['active_device_name']} | Frames={diag['frames_captured']} | RMS={diag['last_rms']:.2f} | Peak={diag['last_peak']}")

    listener.stop()
    final_diag = listener.get_diagnostics()
    print("\nListener Stopped. Final frames captured:", final_diag['frames_captured'])

    passed = res.get("success", False) and final_diag['frames_captured'] > 0
    print(f"\nOVERALL MICROPHONE HARDWARE STATUS: {'PASS' if passed else 'FAIL'}")

if __name__ == "__main__":
    run_mic_test()
