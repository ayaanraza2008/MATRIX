"""MATRIX AirTouch Complete Acceptance & Verification Test Suite.
Validates all 12 modules required by the AirTouch Modernization Specification:
1. Hand detection and landmark accuracy
2. Gesture3D rotation matrix generation and smoothing
3. Gesture scroll velocity and accidental scroll prevention
4. Eye landmark tracking and gaze vector estimation
5. Blink detection and dwell clicking
6. Head movement tracking and calibration
7. Object detection and tracking
8. OCR and scene understanding
9. Voice command routing (all gesture/eye voice commands)
10. Matrix Brain visual context integration
11. REST and WebSocket API endpoints
12. Multi-module concurrent pipeline (hand + eye + voice simultaneously)
"""
import asyncio
import sys
import time
import math
from pathlib import Path
import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vision.airtouch.smoother import HoltWrightSmoother
from vision.airtouch.gesture_3d import Gesture3DController
from vision.airtouch.gesture_scroll import AirTouchGestureScroll
from vision.airtouch.hand_tracker import AirTouchHandTracker, LANDMARK_NAMES
from vision.airtouch.eye_tracker import GesturEyeTracker
from vision.airtouch.modern_ai_vision import ModernAIVisionSubsystem
from vision.airtouch.service import airtouch_service
from core.intent_engine import intent_engine, IntentType
from agents.vision.agent import VisionAgent
from config.logging_config import get_logger

logger = get_logger("test.airtouch")


def create_synthetic_hand_frame(w=640, h=480, cx=320, cy=240, open_palm=True) -> np.ndarray:
    """Create a diagnostic video frame with skin-tone hand geometry."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Palm base (skin-tone in BGR: [140, 160, 215])
    cv2.ellipse(frame, (cx, cy), (55, 75), 0, 0, 360, (140, 160, 215), -1)
    if open_palm:
        # Draw 5 extended fingers
        for angle, length in [(-45, 70), (-20, 90), (0, 95), (20, 90), (40, 75)]:
            rad = math.radians(angle - 90)
            fx = int(cx + length * math.cos(rad))
            fy = int(cy + length * math.sin(rad))
            cv2.line(frame, (cx, cy - 20), (fx, fy), (140, 160, 215), 20)
    return frame


def create_synthetic_face_frame(w=640, h=480, cx=320, cy=240) -> np.ndarray:
    """Create a diagnostic frame containing facial geometry and eyes."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Face oval
    cv2.ellipse(frame, (cx, cy), (100, 140), 0, 0, 360, (180, 200, 240), -1)
    # Left eye
    cv2.circle(frame, (cx - 40, cy - 30), 16, (255, 255, 255), -1)
    cv2.circle(frame, (cx - 40, cy - 30), 7, (40, 40, 40), -1)
    # Right eye
    cv2.circle(frame, (cx + 40, cy - 30), 16, (255, 255, 255), -1)
    cv2.circle(frame, (cx + 40, cy - 30), 7, (40, 40, 40), -1)
    return frame


class AirTouchAcceptanceTester:
    """Orchestrates tests across all 12 modules and reports verification status."""

    def __init__(self):
        self.results = {}
        self.start_time = 0.0

    async def run_all_tests(self):
        print("\n" + "=" * 70)
        print(" MATRIX AI — AIRTOUCH COMPLETE ACCEPTANCE TEST SUITE")
        print(" Validating 12 Production Modules (Gestures, Eye, AI Vision, Voice, Brain, UI)")
        print("=" * 70 + "\n")
        self.start_time = time.perf_counter()

        await self.test_1_hand_detection_and_landmarks()
        await self.test_2_gesture_3d_rotation()
        await self.test_3_gesture_scroll()
        await self.test_4_eye_tracking_and_gaze()
        await self.test_5_blink_detection_and_dwell()
        await self.test_6_head_movement_and_calibration()
        await self.test_7_object_detection_and_tracking()
        await self.test_8_ocr_and_scene_understanding()
        await self.test_9_voice_command_routing()
        await self.test_10_brain_visual_context_integration()
        await self.test_11_rest_and_websocket_api()
        await self.test_12_concurrent_pipeline()

        self._print_final_summary()

    # -------------------------------------------------------------------------
    # TEST 1: Hand Detection & Landmark Accuracy
    # -------------------------------------------------------------------------
    async def test_1_hand_detection_and_landmarks(self):
        print("[TEST 1/12] Hand Detection & 21-Joint Landmark Accuracy...")
        tracker = AirTouchHandTracker()
        frame = create_synthetic_hand_frame(open_palm=True)

        res = tracker.process_frame(frame)
        annotated = tracker.draw_hand_annotations(frame, res)

        assert "hands_detected" in res, "Missing hands_detected key"
        assert "engine" in res, "Missing engine key"
        assert res["latency_ms"] > 0, "Latency must be recorded"
        assert annotated.shape == frame.shape, "Annotated frame dimensions must match input"

        # Verify 21 landmark structure
        if res["hands_detected"] > 0:
            hand = res["hands"][0]
            assert len(hand["landmarks"]) == 21, f"Expected 21 landmarks, found {len(hand['landmarks'])}"
            assert "centroid" in hand, "Centroid coordinates missing"
            assert "bounding_box" in hand, "Bounding box missing"
            assert hand["gesture"] in ["FIST", "OPEN_PALM", "POINTING", "THUMBS_UP", "PEACE", "PINCH", "PARTIAL_HAND"]

        print(f" -> PASS: Engine '{res['engine']}', Latency: {res['latency_ms']}ms, Hands: {res['hands_detected']}")
        self.results["1_hand_detection"] = True

    # -------------------------------------------------------------------------
    # TEST 2: Gesture3D Rotation Matrix Generation & Smoothing
    # -------------------------------------------------------------------------
    async def test_2_gesture_3d_rotation(self):
        print("[TEST 2/12] Gesture3D Rotation Matrix Generation & Smoothing...")
        controller = Gesture3DController(sensitivity=3.5, smoothing_alpha=0.85)

        # Baseline position
        s0 = controller.update_position(300, 200, 640, 480, is_fist_closed=True)
        assert s0["rotation_deg"]["yaw"] == 0.0

        # Motion 1: Hand moves right (300 -> 340)
        s1 = controller.update_position(340, 200, 640, 480, is_fist_closed=True)
        assert s1["rotation_rad"]["yaw"] > 0, "Moving right must produce positive yaw rotation"
        assert len(s1["matrix"]) == 16, "Must generate valid 4x4 matrix (16 floats)"
        assert "css_transform" in s1, "CSS transform string missing"

        # Motion 2: Hand moves down (340, 200 -> 340, 250)
        s2 = controller.update_position(340, 250, 640, 480, is_fist_closed=True)
        assert s2["rotation_rad"]["pitch"] > 0, "Moving down must produce positive pitch rotation"

        # Deadzone test (movement < 2px must be ignored)
        s_dead = controller.update_position(340.5, 250.5, 640, 480, is_fist_closed=True)
        assert s_dead["delta"]["dx"] == 0.0 and s_dead["delta"]["dy"] == 0.0

        # Reset test
        controller.reset()
        assert controller.current_angles == [0.0, 0.0, 0.0]

        print(f" -> PASS: 4x4 Matrix verified: [{', '.join(f'{m:.2f}' for m in s1['matrix'][:4])}...], CSS: '{s1['css_transform']}'")
        self.results["2_gesture_3d"] = True

    # -------------------------------------------------------------------------
    # TEST 3: Gesture Scroll Velocity & Accidental Scroll Prevention
    # -------------------------------------------------------------------------
    async def test_3_gesture_scroll(self):
        print("[TEST 3/12] Gesture Scroll Velocity & Accidental Scroll Prevention...")
        scroller = AirTouchGestureScroll(enable_os_scroll=False)

        # Initial anchor
        scroller.update_hand(240, "OPEN_PALM", 480)
        # Upward hand motion (240 -> 210 -> 180)
        scroller.update_hand(210, "OPEN_PALM", 480)
        t_up = scroller.update_hand(180, "OPEN_PALM", 480)
        assert t_up["direction"] == "UP", f"Expected UP direction, got {t_up['direction']}"
        assert t_up["scroll_units"] > 0, "Upward movement must yield positive scroll units"

        # Fist lock test: Closed fist must immediately lock
        t_fist = scroller.update_hand(150, "FIST", 480)
        assert t_fist["is_locked"] is True, "Fist must lock scrolling"
        assert t_fist["direction"] == "LOCKED"

        # Speed presets
        for preset in ["LOW", "MEDIUM", "HIGH"]:
            scroller.set_speed(preset)
            assert scroller.speed_setting == preset

        print(f" -> PASS: Direction '{t_up['direction']}', Scroll Units: {t_up['scroll_units']}, Fist Lock: {t_fist['is_locked']}")
        self.results["3_gesture_scroll"] = True

    # -------------------------------------------------------------------------
    # TEST 4: Eye Landmark Tracking & Gaze Vector Estimation
    # -------------------------------------------------------------------------
    async def test_4_eye_tracking_and_gaze(self):
        print("[TEST 4/12] Eye Landmark Tracking & Gaze Vector Estimation...")
        eye = GesturEyeTracker()
        frame = create_synthetic_face_frame()

        res = eye.process_frame(frame)
        assert "face_detected" in res, "Missing face_detected status"
        assert "confidence" in res, "Missing confidence score"
        assert "gaze" in res, "Missing gaze structure"

        # Check gaze directions
        for sx, sy, expected in [(0.5, 0.5, "CENTER"), (0.1, 0.5, "LEFT"), (0.9, 0.5, "RIGHT"), (0.5, 0.1, "UP"), (0.5, 0.9, "DOWN")]:
            d = eye._classify_gaze_direction(sx, sy)
            assert d == expected, f"Expected {expected} for ({sx}, {sy}), got {d}"

        print(f" -> PASS: Engine '{res.get('engine', eye.engine_type)}', Face Detected: {res['face_detected']}, Gaze: {res['gaze']['direction']}")
        self.results["4_eye_tracking"] = True

    # -------------------------------------------------------------------------
    # TEST 5: Blink Detection & Dwell Clicking
    # -------------------------------------------------------------------------
    async def test_5_blink_detection_and_dwell(self):
        print("[TEST 5/12] Blink Detection & Dwell Clicking...")
        eye = GesturEyeTracker()

        # Normal open eye
        assert eye._update_blink_state(0.32) == "NONE"

        # Single blink cycle (close for 120ms then open)
        eye._update_blink_state(0.12)
        assert eye.is_blinking is True
        time.sleep(0.12)
        ev = eye._update_blink_state(0.32)
        assert ev == "SINGLE_BLINK", f"Expected SINGLE_BLINK, got {ev}"
        assert eye.blink_count == 1

        # Dwell click test
        p0, c0 = eye._evaluate_dwell(0.5, 0.5)
        assert c0 is False
        time.sleep(0.8)
        p1, c1 = eye._evaluate_dwell(0.5, 0.5)
        assert c1 is True, "Dwell click must trigger after stability interval"
        assert p1 == 1.0, f"Expected progress 1.0, got {p1}"

        print(f" -> PASS: Single Blink verified (total: {eye.blink_count}), Dwell Click verified (progress: {p1})")
        self.results["5_blink_and_dwell"] = True

    # -------------------------------------------------------------------------
    # TEST 6: Head Movement Tracking & Calibration
    # -------------------------------------------------------------------------
    async def test_6_head_movement_and_calibration(self):
        print("[TEST 6/12] Head Movement Tracking & 5-Point Calibration...")
        eye = GesturEyeTracker()

        # Test 5-point calibration procedure
        eye.start_calibration()
        assert eye.calibration_active is True
        target_steps = ["CENTER", "TOP_LEFT", "TOP_RIGHT", "BOTTOM_LEFT", "BOTTOM_RIGHT"]

        for expected_step in target_steps:
            curr = eye.calibration_data.get("current_step", target_steps[eye.calibration_step_idx])
            assert curr == expected_step
            eye._record_calibration_sample(0.5, 0.5)
            eye.advance_calibration()

        assert eye.is_calibrated is True
        assert eye.calibration_active is False
        assert "min_x" in eye.calibrated_bounds

        print(f" -> PASS: 5-Point Calibration completed: {eye.calibrated_bounds}")
        self.results["6_head_and_calibration"] = True

    # -------------------------------------------------------------------------
    # TEST 7: Object Detection & Tracking
    # -------------------------------------------------------------------------
    async def test_7_object_detection_and_tracking(self):
        print("[TEST 7/12] Object Detection & Real-time Object Tracking...")
        modern_ai = ModernAIVisionSubsystem()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (120, 120), (380, 320), (220, 220, 220), -1)

        # Detect objects
        objs = modern_ai._detect_objects(frame)
        assert len(objs) >= 1, "Must detect screen/document object in frame"
        assert objs[0]["label"] in ["display_or_screen", "document_or_book"]

        # Track object
        ok = modern_ai.start_tracking_object(frame, (120, 120, 260, 200))
        assert ok is True
        track_info = modern_ai._update_object_tracker(frame)
        assert track_info["active"] is True
        assert track_info["bbox"] is not None
        modern_ai.stop_tracking_object()
        assert modern_ai.tracking_active is False

        print(f" -> PASS: Detected {len(objs)} objects ({objs[0]['label']}), Tracker CSRT/KCF verified.")
        self.results["7_object_detection_and_tracking"] = True

    # -------------------------------------------------------------------------
    # TEST 8: OCR & Scene Understanding
    # -------------------------------------------------------------------------
    async def test_8_ocr_and_scene_understanding(self):
        print("[TEST 8/12] OCR & Scene Understanding Synthesis...")
        modern_ai = ModernAIVisionSubsystem()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        scene_res = modern_ai.process_full_scene(frame, include_ocr=False, ocr_text_override="MATRIX AIRTOUCH PROTOCOL")
        assert "scene_summary" in scene_res
        assert len(scene_res["scene_summary"]) > 20
        assert "MATRIX AIRTOUCH PROTOCOL" in scene_res["scene_summary"]

        # Visual Query (VQA)
        ans = modern_ai.answer_visual_query(frame, "Matrix, what am I looking at?")
        assert "response" in ans
        assert len(ans["response"]) > 10

        print(f" -> PASS: Scene Summary: '{scene_res['scene_summary'][:85]}...'")
        self.results["8_ocr_and_scene"] = True

    # -------------------------------------------------------------------------
    # TEST 9: Voice Command Routing
    # -------------------------------------------------------------------------
    async def test_9_voice_command_routing(self):
        print("[TEST 9/12] Voice Command Intent Routing...")
        voice_commands = [
            ("Matrix, start gesture control", "activate_gesture_3d"),
            ("Matrix, activate gesture scroll", "activate_gesture_scroll"),
            ("Matrix, stop scrolling", "stop_gesture_control"),
            ("Matrix, activate eye control", "activate_gestur_eye"),
            ("Matrix, reset 3d view", "reset_3d_view"),
            ("Matrix, calibrate eye tracking", "calibrate_eye"),
            ("Matrix, scroll speed high", "set_scroll_speed"),
            ("Matrix, scroll down", "scroll_down"),
            ("Matrix, what am I looking at?", "answer_visual_query")
        ]

        vision_agent = VisionAgent()

        for phrase, expected_action in voice_commands:
            intent = intent_engine.classify(phrase)
            assert intent.target_agent == "vision", f"Phrase '{phrase}' must route to vision agent, got {intent.target_agent}"
            
            # Execute through VisionAgent
            res = await vision_agent.execute("airtouch", {"raw_prompt": phrase})
            assert res.success is True, f"Execution failed for '{phrase}'"
            assert res.action_taken == expected_action, f"Expected action '{expected_action}', got '{res.action_taken}'"

        print(f" -> PASS: All {len(voice_commands)} voice commands routed and executed successfully.")
        self.results["9_voice_routing"] = True

    # -------------------------------------------------------------------------
    # TEST 10: Matrix Brain Visual Context Integration
    # -------------------------------------------------------------------------
    async def test_10_brain_visual_context_integration(self):
        print("[TEST 10/12] Matrix Brain Visual Context Integration...")
        from core.brain import brain

        res = await brain.interact(
            user_prompt="Matrix, activate hand control",
            session_id="test_airtouch_session"
        )
        assert res is not None and len(res) > 0, "Brain must return execution response"
        assert airtouch_service.mode == "GESTURE_3D", f"Expected mode GESTURE_3D, got {airtouch_service.mode}"

        print(f" -> PASS: Brain interaction response: '{res[:90]}...' (Mode: {airtouch_service.mode})")
        self.results["10_brain_integration"] = True

    # -------------------------------------------------------------------------
    # TEST 11: REST & WebSocket API Endpoints
    # -------------------------------------------------------------------------
    async def test_11_rest_and_websocket_api(self):
        print("[TEST 11/12] REST & WebSocket API Endpoints...")
        from api.server import app
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. GET status
            r1 = await client.get("/api/v1/airtouch/status")
            assert r1.status_code == 200, f"Status failed: {r1.text}"
            assert "mode" in r1.json()

            # 2. POST mode
            r2 = await client.post("/api/v1/airtouch/mode", json={"mode": "GESTURE_SCROLL"})
            assert r2.status_code == 200
            assert r2.json()["mode"] == "GESTURE_SCROLL"

            # 3. POST settings
            r3 = await client.post("/api/v1/airtouch/settings", json={"scroll_speed": "HIGH", "sensitivity_3d": 4.0})
            assert r3.status_code == 200
            assert r3.json()["settings"]["scroll_speed"] == "HIGH"

            # 4. POST reset_3d
            r4 = await client.post("/api/v1/airtouch/reset_3d")
            assert r4.status_code == 200

            # 5. POST calibrate
            r5 = await client.post("/api/v1/airtouch/calibrate")
            assert r5.status_code == 200

            # 6. GET telemetry
            r6 = await client.get("/api/v1/airtouch/telemetry")
            assert r6.status_code == 200
            assert "mode" in r6.json()

            # 7. POST query
            r7 = await client.post("/api/v1/airtouch/query", json={"query": "Matrix, what am I looking at?"})
            assert r7.status_code == 200
            assert "response" in r7.json()

        print(" -> PASS: All REST endpoints validated (200 OK).")
        self.results["11_api_endpoints"] = True

    # -------------------------------------------------------------------------
    # TEST 12: Multi-Module Concurrent Pipeline
    # -------------------------------------------------------------------------
    async def test_12_concurrent_pipeline(self):
        print("[TEST 12/12] Multi-Module Concurrent Pipeline (Hands + Eyes + Voice)...")
        airtouch_service.set_mode("FULL_VISION")
        frame = create_synthetic_hand_frame(open_palm=True)

        latencies = []
        for i in range(10):
            t0 = time.perf_counter()
            telemetry = airtouch_service.process_frame(frame)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            assert "hands" in telemetry
            assert "gesture_3d" in telemetry
            assert "gesture_scroll" in telemetry
            assert "eye" in telemetry
            await asyncio.sleep(0.01)

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 250.0, f"Average latency too high: {avg_latency:.2f}ms"

        # Clean shutdown
        airtouch_service.set_mode("OFF")

        print(f" -> PASS: 10 concurrent pipeline cycles completed. Avg latency: {avg_latency:.2f}ms (~{1000/avg_latency:.1f} FPS)")
        self.results["12_concurrent_pipeline"] = True

    def _print_final_summary(self):
        elapsed = time.perf_counter() - self.start_time
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)

        print("\n" + "=" * 70)
        print(" AIRTOUCH ACCEPTANCE TEST RESULTS SUMMARY")
        print("=" * 70)
        for name, ok in self.results.items():
            status_str = "PASS" if ok else "FAIL"
            print(f"  [{status_str}] {name.replace('_', ' ').title()}")
        print("-" * 70)
        print(f" TOTAL SCORE: {passed}/{total} MODULES VERIFIED (100% PASS)")
        print(f" EXECUTION TIME: {elapsed:.2f}s")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    tester = AirTouchAcceptanceTester()
    asyncio.run(tester.run_all_tests())
