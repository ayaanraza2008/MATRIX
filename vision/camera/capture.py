"""MATRIX Camera Frame Capture Engine.
Accesses hardware camera devices (Integrated Camera) with Windows DirectShow acceleration,
automatic fallback, and clean handle release.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import time
import os
import cv2
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("vision.camera")


class CameraCapture:
    """Controls webcam hardware access with explicit status reporting and resource cleanup."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.output_dir = settings.cache_dir / "vision"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def list_devices(self) -> List[Dict[str, Any]]:
        """Probe available video capture devices."""
        available = []
        backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY
        for idx in range(3):
            cap = cv2.VideoCapture(idx, backend)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    available.append({"index": idx, "name": f"Camera Device {idx}", "available": True})
            else:
                cap.release()
        return available

    def capture_frame(self, device_override: Optional[int] = None) -> Dict[str, Any]:
        """Capture a single frame from the camera using DirectShow with fallback."""
        start_time = time.perf_counter()
        target_idx = device_override if device_override is not None else self.device_index
        backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY

        cap = cv2.VideoCapture(target_idx, backend)
        try:
            if not cap.isOpened():
                # Fallback to alternate indices if 0 is busy
                logger.warning(f"Device index {target_idx} not open; trying alternate index 1...")
                cap.release()
                target_idx = 1 if target_idx == 0 else 0
                cap = cv2.VideoCapture(target_idx, backend)

            if not cap.isOpened():
                return {
                    "success": False,
                    "error": f"Camera device is busy or permissions are not granted by Windows.",
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }

            # Warm up single buffer frame
            cap.grab()
            ret, frame = cap.read()

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
        finally:
            if cap is not None:
                cap.release()


# Global camera instance
camera_capture = CameraCapture()
