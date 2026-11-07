"""MATRIX Camera Frame Capture Engine.
Accesses hardware camera devices (Integrated Camera) and captures verified video frames.
"""
from typing import Optional, Dict, Any
from pathlib import Path
import time
import cv2
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("vision.camera")


class CameraCapture:
    """Controls webcam hardware access with explicit status reporting."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.output_dir = settings.cache_dir / "vision"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture_frame(self) -> Dict[str, Any]:
        """Capture a single frame from the camera, save to disk, and return properties."""
        start_time = time.perf_counter()
        cap = cv2.VideoCapture(self.device_index)

        if not cap.isOpened():
            logger.warning(f"Unable to open camera device at index {self.device_index}")
            return {
                "success": False,
                "error": f"Camera index {self.device_index} is busy or unavailable.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return {
                "success": False,
                "error": "Failed to read video frame from camera stream.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        height, width, channels = frame.shape
        target_path = self.output_dir / f"cam_{int(time.time() * 1000)}.jpg"
        cv2.imwrite(str(target_path), frame)

        latency = (time.perf_counter() - start_time) * 1000
        logger.info(f"Captured camera frame ({width}x{height}) -> {target_path.name}")

        return {
            "success": True,
            "filepath": str(target_path),
            "width": width,
            "height": height,
            "channels": channels,
            "latency_ms": round(latency, 2)
        }


# Global camera instance
camera_capture = CameraCapture()
