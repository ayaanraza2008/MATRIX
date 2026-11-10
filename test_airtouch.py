"""Test AirTouch hand and eye tracking with mock frames."""
import sys

sys.path.insert(0, '.')

# Test AirTouchHandTracker with a mock frame (no actual OpenCV needed for the class init)
from vision.airtouch.hand_tracker import AirTouchHandTracker

print("=== Testing AirTouchHandTracker initialization ===")
try:
    tracker = AirTouchHandTracker(model_path=None, max_num_hands=2)
    print(f"  Engine type: {tracker.engine_type}")
    print(f"  MediaPipe available: {tracker.mp_landmarker is not None}")
    print(f"  Hand landmarks count: {len(AirTouchHandTracker.LANDMARK_NAMES)}")
    print("  HandTracker initialized successfully (fallback mode)")
except Exception as e:
    print(f"  Error: {e}")

# Test GesturEyeTracker initialization
print("\n=== Testing GesturEyeTracker initialization ===")
from vision.airtouch.eye_tracker import GesturEyeTracker
try:
    eye_tracker = GesturEyeTracker(model_path=None, blink_threshold=0.20, dwell_threshold_ms=750.0)
    print(f"  Engine type: {eye_tracker.engine_type}")
    print(f"  Face cascade available: {eye_tracker._face_cascade is not None}")
    print(f"  Eye cascade available: {eye_tracker._eye_cascade is not None}")
    print("  GesturEyeTracker initialized successfully (fallback mode)")
except Exception as e:
    print(f"  Error: {e}")

# Test VisionAgent creation (this is the key integration test)
print("\n=== Testing VisionAgent creation ===")
from agents.vision.agent import VisionAgent
try:
    agent = VisionAgent()
    print(f"  VisionAgent created successfully")
    print(f"  Name: {agent.name}")
    print(f"  Description: {agent.description}")
    print(f"  Capabilities: {len(agent._capabilities)}")
    for cap in agent._capabilities:
        print(f"    - {cap.name}: {cap.description}")
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

# Test the full test suite still passes
print("\n=== Running full test suite ===")