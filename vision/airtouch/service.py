"""MATRIX AirTouch Unified Vision & Gesture Background Service.
Coordinates camera acquisition, active operating modes, Gesture3D, Gesture Scroll, GesturEye,
and telemetry broadcasting for the Matrix HUD and WebSocket clients.
"""
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import threading
import time
import cv2
import numpy as np

from vision.airtouch.smoother import HoltWrightSmoother
from vision.airtouch.gesture_3d import Gesture3DController
from vision.airtouch.gesture_scroll import AirTouchGestureScroll
from vision.airtouch.hand_tracker import AirTouchHandTracker
from vision.airtouch.eye_tracker import GesturEyeTracker, CALIBRATION_STEPS
from vision.airtouch.modern_ai_vision import ModernAIVisionSubsystem
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("vision.airtouch.service")

VALID_MODES = ["OFF", "GESTURE_3D", "GESTURE_SCROLL", "GESTURE_EYE", "FULL_VISION"]


class AirTouchVisionService:
    """Manages real-time vision pipelines, hardware capture thread, and telemetry."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.mode = "OFF"
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Controllers
        self.gesture_3d = Gesture3DController()
        self.gesture_scroll = AirTouchGestureScroll()
        self.hand_tracker = AirTouchHandTracker()
        self.eye_tracker = GesturEyeTracker()
        self.modern_ai = ModernAIVisionSubsystem()

        # Telemetry cache
        self.latest_telemetry: Dict[str, Any] = {
            "mode": "OFF",
            "active": False,
            "fps": 0.0,
            "latency_ms": 0.0,
            "timestamp": time.time(),
            "gesture_3d": self.gesture_3d._build_state(0.0, 0.0, False),
            "gesture_scroll": self.gesture_scroll._build_telemetry(0.0, 0.0, False, "IDLE", "NONE"),
            "eye": {"face_detected": False, "gaze": {"direction": "CENTER", "screen_x": 0.5, "screen_y": 0.5}},
            "hands": {"hands_detected": 0, "hands": []},
            "scene_summary": "System initialized in standby."
        }

        # Subscribers for live event broadcasting
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []

        # Performance metrics
        self.fps_counter = 0
        self.fps_timer = time.perf_counter()
        self.current_fps = 0.0

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for telemetry broadcasts."""
        with self._lock:
            if callback not in self.subscribers:
                self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Unregister a callback."""
        with self._lock:
            if callback in self.subscribers:
                self.subscribers.remove(callback)

    def set_mode(self, mode: str) -> Dict[str, Any]:
        """Switch operating mode (OFF, GESTURE_3D, GESTURE_SCROLL, GESTURE_EYE, FULL_VISION)."""
        upper_mode = mode.upper()
        if upper_mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {VALID_MODES}")

        self.mode = upper_mode
        logger.info(f"AirTouch operating mode set to: {self.mode}")

        if self.mode != "OFF" and not self.is_running:
            self.start()
        elif self.mode == "OFF" and self.is_running:
            self.stop()

        self.latest_telemetry["mode"] = self.mode
        self.latest_telemetry["active"] = (self.mode != "OFF")
        return {"success": True, "mode": self.mode, "running": self.is_running}

    def start(self):
        """Start the background camera loop."""
        with self._lock:
            if self.is_running:
                return
            self._stop_event.clear()
            self.is_running = True
            self._thread = threading.Thread(target=self._capture_loop, name="AirTouchWorker", daemon=True)
            self._thread.start()
            logger.info("AirTouch vision capture worker thread started.")

    def stop(self):
        """Stop background capture worker."""
        with self._lock:
            if not self.is_running:
                return
            self._stop_event.set()
            self.is_running = False
            logger.info("AirTouch vision capture worker stopping...")

    def _capture_loop(self):
        """Background frame capture and processing loop."""
        cap = None
        try:
            cap = cv2.VideoCapture(self.device_index)
        except Exception as e:
            logger.warning(f"Could not open hardware camera index {self.device_index}: {e}")

        while not self._stop_event.is_set():
            loop_start = time.perf_counter()
            frame = None

            if cap is not None and cap.isOpened():
                ret, grabbed_frame = cap.read()
                if ret and grabbed_frame is not None:
                    frame = grabbed_frame

            # If physical camera is unavailable or not returning frames, wait briefly
            if frame is None:
                time.sleep(0.08)
                continue

            telemetry = self.process_frame(frame)
            self._update_fps()
            self._broadcast(telemetry)

            # Cap frame rate to ~30 FPS on CPU to save cycles
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0.005, 0.033 - elapsed)
            time.sleep(sleep_time)

        if cap is not None:
            cap.release()
        logger.info("AirTouch capture loop ended cleanly.")

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process an arbitrary frame through active pipelines and update telemetry."""
        start_time = time.perf_counter()
        h, w = frame.shape[:2]

        telemetry: Dict[str, Any] = {
            "mode": self.mode,
            "active": (self.mode != "OFF"),
            "timestamp": time.time(),
            "dimensions": {"width": w, "height": h}
        }

        # 1. Gesture3D Mode
        if self.mode in ("GESTURE_3D", "FULL_VISION"):
            hand_res = self.hand_tracker.process_frame(frame)
            telemetry["hands"] = hand_res

            if hand_res.get("hands_detected", 0) > 0:
                lead_hand = hand_res["hands"][0]
                cx = lead_hand["centroid"]["x"]
                cy = lead_hand["centroid"]["y"]
                is_fist = (lead_hand["gesture"] == "FIST")
                rot_state = self.gesture_3d.update_position(
                    pos_x=cx, pos_y=cy,
                    frame_width=w, frame_height=h,
                    is_fist_closed=is_fist
                )
                telemetry["gesture_3d"] = rot_state
            else:
                telemetry["gesture_3d"] = self.gesture_3d._build_state(0.0, 0.0, False)

        # 2. Gesture Scroll Mode
        if self.mode in ("GESTURE_SCROLL", "FULL_VISION"):
            # Reuse hand results if already computed
            hand_res = telemetry.get("hands") or self.hand_tracker.process_frame(frame)
            telemetry["hands"] = hand_res

            if hand_res.get("hands_detected", 0) > 0:
                lead_hand = hand_res["hands"][0]
                cy = lead_hand["centroid"]["y"]
                gesture = lead_hand["gesture"]
                scroll_state = self.gesture_scroll.update_hand(
                    pos_y=cy, gesture=gesture, frame_height=h
                )
                telemetry["gesture_scroll"] = scroll_state
            else:
                telemetry["gesture_scroll"] = self.gesture_scroll._build_telemetry(0.0, 0.0, False, "IDLE", "NONE")

        # 3. GesturEye Mode
        if self.mode in ("GESTURE_EYE", "FULL_VISION"):
            eye_res = self.eye_tracker.process_frame(frame)
            telemetry["eye"] = eye_res

        # 4. Full Vision Mode (Scene + Objects + OCR)
        if self.mode == "FULL_VISION":
            full_scene = self.modern_ai.process_full_scene(frame, include_ocr=False)
            telemetry["objects"] = full_scene["objects"]
            telemetry["tracking"] = full_scene["tracking"]
            telemetry["scene_summary"] = full_scene["scene_summary"]
        else:
            telemetry["scene_summary"] = f"AirTouch active in {self.mode} mode."

        latency = (time.perf_counter() - start_time) * 1000.0
        telemetry["latency_ms"] = round(latency, 2)
        telemetry["fps"] = round(self.current_fps, 1)

        with self._lock:
            self.latest_telemetry = telemetry

        return telemetry

    def _update_fps(self):
        self.fps_counter += 1
        now = time.perf_counter()
        if (now - self.fps_timer) >= 1.0:
            self.current_fps = self.fps_counter / (now - self.fps_timer)
            self.fps_counter = 0
            self.fps_timer = now

    def _broadcast(self, telemetry: Dict[str, Any]):
        subscribers_copy = []
        with self._lock:
            subscribers_copy = list(self.subscribers)

        for sub in subscribers_copy:
            try:
                sub(telemetry)
            except Exception as e:
                logger.debug(f"Broadcast to subscriber error: {e}")

    def reset_3d(self) -> Dict[str, Any]:
        """Reset Gesture3D rotation matrix back to default identity."""
        self.gesture_3d.reset()
        logger.info("AirTouch Gesture3D rotation reset to identity.")
        return {"success": True, "message": "3D rotation matrix reset to zero identity."}

    def calibrate_eye(self) -> Dict[str, Any]:
        """Advance or start GesturEye screen calibration."""
        if not self.eye_tracker.calibration_active:
            self.eye_tracker.start_calibration()
            step = "CENTER"
        else:
            self.eye_tracker.advance_calibration()
            step = CALIBRATION_STEPS[self.eye_tracker.calibration_step_idx] if self.eye_tracker.calibration_active else "COMPLETED"

        return {
            "success": True,
            "calibration_active": self.eye_tracker.calibration_active,
            "is_calibrated": self.eye_tracker.is_calibrated,
            "target": step
        }

    def update_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update tuning parameters dynamically."""
        if "sensitivity_3d" in settings_data:
            self.gesture_3d.sensitivity = float(settings_data["sensitivity_3d"])
        if "scroll_speed" in settings_data:
            self.gesture_scroll.set_speed(str(settings_data["scroll_speed"]))
        if "scroll_sensitivity" in settings_data:
            self.gesture_scroll.set_sensitivity(float(settings_data["scroll_sensitivity"]))
        if "dwell_ms" in settings_data:
            self.eye_tracker.dwell_threshold_ms = float(settings_data["dwell_ms"])
        if "eye_enabled" in settings_data:
            self.eye_tracker.is_enabled = bool(settings_data["eye_enabled"])

        return {
            "success": True,
            "settings": {
                "sensitivity_3d": self.gesture_3d.sensitivity,
                "scroll_speed": self.gesture_scroll.speed_setting,
                "scroll_sensitivity": self.gesture_scroll.sensitivity,
                "dwell_ms": self.eye_tracker.dwell_threshold_ms,
                "eye_enabled": self.eye_tracker.is_enabled
            }
        }

    def get_status(self) -> Dict[str, Any]:
        """Get full health and status report."""
        return {
            "mode": self.mode,
            "is_running": self.is_running,
            "fps": round(self.current_fps, 1),
            "engines": {
                "hand_engine": self.hand_tracker.engine_type,
                "eye_engine": self.eye_tracker.engine_type,
            },
            "subscribers_count": len(self.subscribers),
            "latest_telemetry": self.latest_telemetry
        }


# Global singleton instance
airtouch_service = AirTouchVisionService()
