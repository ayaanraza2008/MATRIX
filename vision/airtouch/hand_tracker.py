"""MATRIX AirTouch Hand & Gesture Tracking Subsystem.
Implements dual-engine hand tracking:
1. High-precision MediaPipe HandLandmarker (21 3D landmarks, finger state analysis, gesture classification).
2. Resilient OpenCV fallback engine (skin segmentation, contour convex hull, convexity defects).

Classifies gestures: FIST, OPEN_PALM, POINTING, THUMBS_UP, PEACE, PINCH.
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import math
import time
import cv2
import numpy as np

from config.logging_config import get_logger

logger = get_logger("vision.airtouch.hand")

# 21 Hand Landmark Names per MediaPipe specification
LANDMARK_NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
    "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
    "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17)              # Palm base
]


class AirTouchHandTracker:
    """Tracks hands, extracts 21 3D landmarks, counts fingers, and classifies gestures."""

    def __init__(self, model_path: Optional[str] = None, max_num_hands: int = 2):
        self.max_num_hands = max_num_hands
        self.mp_landmarker = None
        self.engine_type = "opencv_fallback"
        
        # Default model location
        default_model = Path(__file__).parent / "models" / "hand_landmarker.task"
        effective_model = Path(model_path) if model_path else default_model

        if effective_model.exists():
            try:
                import mediapipe as mp
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision

                base_options = python.BaseOptions(model_asset_path=str(effective_model))
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=self.max_num_hands,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.mp_landmarker = vision.HandLandmarker.create_from_options(options)
                self.engine_type = "mediapipe_tasks"
                # Pre-warm HandLandmarker graph to eliminate initial compilation latency
                try:
                    dummy_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
                    dummy_rgb = cv2.cvtColor(dummy_bgr, cv2.COLOR_BGR2RGB)
                    dummy_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=dummy_rgb)
                    self.mp_landmarker.detect(dummy_mp)
                except Exception:
                    pass
                logger.info(f"AirTouch HandTracker initialized with MediaPipe engine: {effective_model.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe HandLandmarker ({e}). Falling back to OpenCV engine.")
                self.mp_landmarker = None
        else:
            logger.info("MediaPipe task model not found at path. Using robust OpenCV engine.")

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process a BGR video frame and return detected hands, landmarks, and gestures."""
        start_time = time.perf_counter()
        h, w = frame.shape[:2]

        if self.engine_type == "mediapipe_tasks" and self.mp_landmarker is not None:
            result = self._process_mediapipe(frame, w, h)
            if result.get("hands_detected", 0) > 0:
                result["engine"] = "mediapipe_tasks"
                result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
                return result

        # Fallback to OpenCV contour/defect pipeline if MediaPipe didn't detect or is unavailable
        result = self._process_opencv(frame, w, h)
        result["engine"] = "opencv_fallback"
        result["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
        return result

    def _process_mediapipe(self, frame_bgr: np.ndarray, w: int, h: int) -> Dict[str, Any]:
        """Process frame via MediaPipe Tasks HandLandmarker."""
        import mediapipe as mp

        max_dim = max(w, h)
        if max_dim > 640:
            scale = 640.0 / max_dim
            proc_w, proc_h = int(w * scale), int(h * scale)
            resized_bgr = cv2.resize(frame_bgr, (proc_w, proc_h), interpolation=cv2.INTER_LINEAR)
            rgb_frame = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection_result = self.mp_landmarker.detect(mp_image)

        hands_list = []
        if detection_result.hand_landmarks:
            for idx, landmarks in enumerate(detection_result.hand_landmarks):
                handedness = "Right"
                if detection_result.handedness and idx < len(detection_result.handedness):
                    handedness = detection_result.handedness[idx][0].category_name

                parsed_landmarks = []
                xs = []
                ys = []
                for lm_idx, lm in enumerate(landmarks):
                    px = int(lm.x * w)
                    py = int(lm.y * h)
                    xs.append(px)
                    ys.append(py)
                    parsed_landmarks.append({
                        "id": lm_idx,
                        "name": LANDMARK_NAMES[lm_idx],
                        "x": round(float(lm.x), 4),
                        "y": round(float(lm.y), 4),
                        "z": round(float(lm.z), 4),
                        "pixel_x": px,
                        "pixel_y": py
                    })

                # Bounding box & centroid
                min_x, max_x = max(0, min(xs)), min(w, max(xs))
                min_y, max_y = max(0, min(ys)), min(h, max(ys))
                cx = int(sum(xs) / len(xs))
                cy = int(sum(ys) / len(ys))

                # Finger states & gesture classification
                finger_states = self._evaluate_fingers(parsed_landmarks, handedness)
                open_count = sum(1 for is_open in finger_states.values() if is_open)
                gesture = self._classify_gesture(parsed_landmarks, finger_states, open_count)

                hands_list.append({
                    "hand_id": idx,
                    "handedness": handedness,
                    "centroid": {"x": cx, "y": cy},
                    "normalized_centroid": {"x": round(cx / w, 4), "y": round(cy / h, 4)},
                    "bounding_box": {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y},
                    "landmarks": parsed_landmarks,
                    "finger_states": finger_states,
                    "open_finger_count": open_count,
                    "gesture": gesture,
                    "confidence": 0.95
                })

        return {
            "hands_detected": len(hands_list),
            "hands": hands_list
        }

    def _evaluate_fingers(self, landmarks: List[Dict[str, Any]], handedness: str) -> Dict[str, bool]:
        """Determine open/closed state for each of the 5 fingers."""
        # Landmarks:
        # Thumb: 4 (tip), 3 (IP), 2 (MCP)
        # Index: 8 (tip), 6 (PIP)
        # Middle: 12 (tip), 10 (PIP)
        # Ring: 16 (tip), 14 (PIP)
        # Pinky: 20 (tip), 18 (PIP)

        states = {}
        # Thumb: Check x-axis extension relative to MCP depending on hand side
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]
        wrist = landmarks[0]

        # In normalized coords:
        if handedness == "Right":
            states["thumb"] = thumb_tip["x"] < thumb_ip["x"]
        else:
            states["thumb"] = thumb_tip["x"] > thumb_ip["x"]

        # Other 4 fingers: tip y is above (less than) PIP joint y
        states["index"] = landmarks[8]["y"] < landmarks[6]["y"]
        states["middle"] = landmarks[12]["y"] < landmarks[10]["y"]
        states["ring"] = landmarks[16]["y"] < landmarks[14]["y"]
        states["pinky"] = landmarks[20]["y"] < landmarks[18]["y"]

        return states

    def _classify_gesture(
        self,
        landmarks: List[Dict[str, Any]],
        fingers: Dict[str, bool],
        open_count: int
    ) -> str:
        """Classify hand gesture based on landmark topology and open fingers."""
        # Check pinch: distance between thumb tip (4) and index tip (8)
        t_tip = landmarks[4]
        i_tip = landmarks[8]
        pinch_dist = math.hypot(t_tip["x"] - i_tip["x"], t_tip["y"] - i_tip["y"])

        if pinch_dist < 0.07:
            return "PINCH"

        if open_count == 0:
            return "FIST"

        if open_count == 5:
            return "OPEN_PALM"

        if fingers.get("index") and not fingers.get("middle") and not fingers.get("ring") and not fingers.get("pinky"):
            if not fingers.get("thumb"):
                return "POINTING"
            # If thumb also out, could be pointing or gun
            return "POINTING"

        if fingers.get("thumb") and not fingers.get("index") and not fingers.get("middle") and not fingers.get("ring") and not fingers.get("pinky"):
            # Check thumb is pointing upwards (tip y < wrist y)
            if landmarks[4]["y"] < landmarks[0]["y"]:
                return "THUMBS_UP"

        if fingers.get("index") and fingers.get("middle") and not fingers.get("ring") and not fingers.get("pinky"):
            return "PEACE"

        if open_count >= 4:
            return "OPEN_PALM"

        return "PARTIAL_HAND"

    def _process_opencv(self, frame_bgr: np.ndarray, w: int, h: int) -> Dict[str, Any]:
        """OpenCV contour and convexity defect fallback tracking."""
        # Convert to YCrCb color space for robust skin tone segmentation
        ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)

        # Morphological filtering to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hands_list = []

        if contours:
            # Sort contours by area and pick largest
            valid_contours = [c for c in contours if cv2.contourArea(c) > 3000]
            valid_contours.sort(key=cv2.contourArea, reverse=True)

            for idx, cnt in enumerate(valid_contours[:self.max_num_hands]):
                area = cv2.contourArea(cnt)
                x, y, cw, ch = cv2.boundingRect(cnt)
                M = cv2.moments(cnt)
                if M["m00"] == 0:
                    continue
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                # Convex hull & defects
                hull = cv2.convexHull(cnt, returnPoints=False)
                finger_count = 0
                if hull is not None and len(hull) > 3:
                    try:
                        defects = cv2.convexityDefects(cnt, hull)
                        if defects is not None:
                            for i in range(defects.shape[0]):
                                s, e, f, d = defects[i, 0]
                                start = cnt[s][0]
                                end = cnt[e][0]
                                far = cnt[f][0]

                                # Calculate triangle sides
                                a = math.hypot(end[0] - start[0], end[1] - start[1])
                                b = math.hypot(far[0] - start[0], far[1] - start[1])
                                c = math.hypot(end[0] - far[0], end[1] - far[1])
                                
                                # Angle using cosine law
                                if b * c > 0:
                                    angle = math.degrees(math.acos(max(min((b**2 + c**2 - a**2) / (2 * b * c), 1.0), -1.0)))
                                    # Finger web angle is typically < 90 degrees and depth > 20px
                                    if angle <= 85.0 and d > 3000:
                                        finger_count += 1
                    except Exception:
                        pass

                # Approximate gesture
                if finger_count == 0:
                    gesture = "FIST"
                elif finger_count == 1:
                    gesture = "POINTING"
                elif finger_count == 2:
                    gesture = "PEACE"
                elif finger_count >= 4:
                    gesture = "OPEN_PALM"
                else:
                    gesture = "PARTIAL_HAND"

                # Generate synthetic proxy landmarks for visualization/HUD compatibility
                landmarks = []
                for lm_idx in range(21):
                    # Distribute around bounding box and centroid
                    offset_x = (cx - x) * (lm_idx / 21.0)
                    offset_y = (cy - y) * (lm_idx / 21.0)
                    px = int(x + offset_x)
                    py = int(y + offset_y)
                    landmarks.append({
                        "id": lm_idx,
                        "name": LANDMARK_NAMES[lm_idx],
                        "x": round(px / w, 4),
                        "y": round(py / h, 4),
                        "z": 0.0,
                        "pixel_x": px,
                        "pixel_y": py
                    })

                hands_list.append({
                    "hand_id": idx,
                    "handedness": "Unknown",
                    "centroid": {"x": cx, "y": cy},
                    "normalized_centroid": {"x": round(cx / w, 4), "y": round(cy / h, 4)},
                    "bounding_box": {"x": x, "y": y, "width": cw, "height": ch},
                    "landmarks": landmarks,
                    "finger_states": {"thumb": finger_count >= 5, "index": finger_count >= 1, "middle": finger_count >= 2, "ring": finger_count >= 3, "pinky": finger_count >= 4},
                    "open_finger_count": min(finger_count + 1, 5) if finger_count > 0 else 0,
                    "gesture": gesture,
                    "confidence": 0.70
                })

        return {
            "hands_detected": len(hands_list),
            "hands": hands_list
        }

    def draw_hand_annotations(self, frame: np.ndarray, tracking_result: Dict[str, Any]) -> np.ndarray:
        """Render 21 landmarks, connections, bounding boxes, and gesture labels onto frame."""
        annotated = frame.copy()
        for hand in tracking_result.get("hands", []):
            bbox = hand["bounding_box"]
            bx, by, bw, bh = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
            cx, cy = hand["centroid"]["x"], hand["centroid"]["y"]
            gesture = hand["gesture"]
            fingers = hand["open_finger_count"]
            handedness = hand["handedness"]

            # Draw bounding box (Cyan HUD style)
            cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), (0, 230, 255), 2)

            # Draw connections
            lm_pts = {lm["id"]: (lm["pixel_x"], lm["pixel_y"]) for lm in hand.get("landmarks", [])}
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx in lm_pts and end_idx in lm_pts:
                    cv2.line(annotated, lm_pts[start_idx], lm_pts[end_idx], (0, 180, 255), 2)

            # Draw landmark points
            for lm in hand.get("landmarks", []):
                cv2.circle(annotated, (lm["pixel_x"], lm["pixel_y"]), 4, (0, 255, 120), -1)

            # Draw centroid
            cv2.circle(annotated, (cx, cy), 6, (0, 0, 255), -1)

            # Draw label banner
            label = f"{handedness} [{gesture}] Fingers: {fingers}"
            cv2.putText(annotated, label, (bx, max(20, by - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return annotated
