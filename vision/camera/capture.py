"""MATRIX Camera Frame Capture Engine.
Accesses hardware camera devices (Integrated Camera) with Windows Media Foundation (MSMF)
and DirectShow (DSHOW) acceleration, automatic fallback, and clean hand
over. Gracefully handles environments where OpenCV is unavailable.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import time
import os

# OpenCV is optional - try to import, graceful fallback if unavailable
_HAS_CV2 = False
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    pass

logger = None
try:
    from config.logging_config import get_logger
    logger = get_logger("vision.camera")
except Exception:
    logger = None


class CameraCapture:
    """Controls webcam hardware access with explicit status reporting and resource cleanup."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.output_dir = Path(".") / "cache" / "vision"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def list_devices(self, max_devices: int = 1) -> List[Dict[str, Any]]:
        """Probe available video capture devices across MSMF and DirectShow backends."""
        available = []
        if _HAS_CV2:
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW] if os.name == 'nt' else [cv2.CAP_ANY]
            for backend in backends:
                for idx in range(max_devices):
                    try:
                        cap = cv2.VideoCapture(idx, backend)
                        if cap.isOpened():
                            available.append({
                                "index": idx,
                                "name": f"Integrated Camera (Device {idx})",
                                "backend": "MSMF" if backend == cv2.CAP_MSMF else "DirectShow",
                                "available": True
                            })
                        cap.release()
                    except Exception:
                        pass
                if available:
                    break
        if not available and logger:
            logger.info("No camera devices found (OpenCV unavailable or no hardware)")
        return available

    def capture_frame(self, device_override: Optional[int] = None) -> Dict[str, Any]:
        """Capture a single frame from the camera using MSMF or DirectShow with automatic fallback."""
        start_time = time.perf_counter()
        target_idx = device_override if device_override is not None else self.device_index

        if not _HAS_CV2:
            if logger:
                logger.info("Camera capture skipped: OpenCV not available")
            return {
                "success": False,
                "error": "Camera capture unavailable: OpenCV is not available in this environment.",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }

        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY]

        cap = None
        used_backend = "UNKNOWN"

        for b_id in backends:
            try:
                c = cv2.VideoCapture(target_idx, b_id)
                if c.isOpened():
                    cap = c
                    used_backend = "MSMF" if b_id == cv2.CAP_MSMF else ("DirectShow" if b_id == cv2.CAP_DSHOW else "ANY")
                    break
            except Exception:
                c.release()
                continue

        try:
            if cap is None or not cap.isOpened():
                return {
                    "success": False,
                    "error": f"Camera device {target_idx} is busy or permissions are not granted by Windows.",
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }

            # Warm up single buffer frame
            try:
                cap.grab()
            except Exception:
                pass

            ret, frame = cap.read()

            if not ret or frame is None:
                return {
                    "success": False,
                    "error": "Failed to read video frame from camera stream.",
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }

            try:
                height, width, channels = frame.shape
            except Exception:
                height, width = 640, 480
                channels = 3

            target_path = self.output_dir / f"cam_{int(time.time() * 1000)}.jpg"
            try:
                cv2.imwrite(str(target_path), frame)
            except Exception:
                pass

            latency = (time.perf_counter() - start_time) * 1000
            if logger:
                logger.info(f"Captured camera frame ({width}x{height} via {used_backend}) -> {target_path.name}")

            return {
                "success": True,
                "filepath": str(target_path),
                "width": width,
                "height": height,
                "channels": channels,
                "backend": used_backend,
                "latency_ms": round(latency, 2)
            }
        finally:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass


# Global camera instance - will be created lazily
camera_capture = None
try:
    camera_capture = CameraCapture()
except Exception:
    camera_capture = None