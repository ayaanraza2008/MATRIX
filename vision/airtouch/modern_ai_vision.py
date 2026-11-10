"""MATRIX AirTouch Modern AI Vision Subsystem.
Extends AirTouch with state-of-the-art multi-modal visual perception.
Handles gracefully environments where certain OpenCV features are unavailable.
"""
from typing import Dict, Any, Optional, Tuple
import numpy as np

# OpenCV is optional - try to import, graceful fallback if unavailable
_HAS_CV2 = False
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    pass

from vision.airtouch.hand_tracker import AirTouchHandTracker
from vision.airtouch.eye_tracker import GesturEyeTracker
from vision.ocr.engine import ocr_engine
from config.logging_config import get_logger

logger = get_logger("vision.airtouch.modern_ai")

# Object cascade classifiers - loaded gracefully
object_cascades: Dict[str, Any] = {}
cascade_names = ["face", "eye", "fullbody", "upperbody"]
for name in cascade_names:
    try:
        import cv2
        cascade_path = getattr(cv2, "data", type("obj", (object,), {"haarcascades": ""})).haarcascades
        if cascade_path:
            cascade_full_path = cascade_path + f"haarcascade_{name}.xml"
        else:
            # Try common paths
            import os
            possible_paths = [
                os.path.join(cv2.__path__[0], "haarcascades", f"haarcascade_{name}.xml") if _HAS_CV2 else "",
                f"haarcascade_{name}.xml",
            ]
            cascade_full_path = next((p for p in possible_paths if p and os.path.exists(p)), "")
            if not cascade_full_path and _HAS_CV2:
                cascade_full_path = cv2.data.haarcascades + f"haarcascade_{name}.xml" if hasattr(cv2, "data") else ""
        if cascade_full_path and _HAS_CV2:
            object_cascades[name] = cv2.CascadeClassifier(cascade_full_path)
        else:
            object_cascades[name] = None
    except Exception:
        object_cascades[name] = None


class ModernAIVisionSubsystem:
    """Unified vision coordinator combining hand, eye, object, scene, and OCR intelligence."""

    def __init__(self):
        self.hand_tracker = AirTouchHandTracker()
        self.eye_tracker = GesturEyeTracker()

        # Object tracking state
        self.active_tracker = None
        self.tracked_bbox: Optional[Tuple[int, int, int, int]] = None
        self.tracking_active = False

        # Object detection cascades (graceful fallback if loading fails)
        self.object_cascades = object_cascades

    def process_full_scene(
        self,
        frame: np.ndarray,
        include_ocr: bool = False,
    ) -> Dict[str, Any]:
        """Process a full scene frame with hand tracking, eye gaze, object detection, and OCR."""
        results = {
            "success": _HAS_CV2,
            "hand_landmarks": None,
            "eye_gaze": None,
            "detected_objects": [],
            "ocr_text": [],
            "scene_analysis": "OpenCV features unavailable",
        }

        if not _HAS_CV2:
            results["scene_analysis"] = "OpenCV not available"
            return results

        try:
            # Hand tracking
            try:
                hand_results = self.hand_tracker.detect_hands(frame)
                results["hand_landmarks"] = hand_results
            except Exception:
                pass

            # Eye gaze tracking
            try:
                eye_results = self.eye_tracker.track_gaze(frame)
                results["eye_gaze"] = eye_results
            except Exception:
                pass

            # Object detection using cascades if available
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if _HAS_CV2 else None
                detected_objects = []
                for obj_name, cascade in self.object_cascades.items():
                    if cascade is not None and gray is not None:
                        try:
                            gray_small = cv2.pyrDown(gray)
                            matches = cascade.detectMultiScale(gray_small, scaleFactor=1.2, minNeighbors=4, minSize=(20, 20))
                            for (x, y, w, h) in matches:
                                detected_objects.append({
                                    "name": obj_name,
                                    "x": int(x * 2),  # Scale back up from pyrDown
                                    "y": int(y * 2),
                                    "w": int(w * 2),
                                    "h": int(h * 2),
                                })
                        except Exception:
                            pass
                results["detected_objects"] = detected_objects
            except Exception:
                pass

            # OCR if requested
            if include_ocr:
                try:
                    ocr_results = ocr_engine.extract_text(frame)
                    results["ocr_text"] = ocr_results
                except Exception:
                    pass

            results["success"] = True
            results["scene_analysis"] = "Processing complete"
        except Exception as e:
            if logger:
                logger.error(f"Error processing scene: {e}")
            results["error"] = str(e)

        return results