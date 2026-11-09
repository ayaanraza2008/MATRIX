"""MATRIX Camera Frame Capture Engine.
Accesses hardware camera devices (Integrated Camera) with Windows Media Foundation (MSMF)
and DirectShow (DSHOW) acceleration, automatic fallback, and clean handle release.
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

    def list_devices(self, max_devices: int = 1) -> List[Dict[str, Any]]:
        """Probe available video capture devices across MSMF and DirectShow backends."""
        available = []
        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW] if os.name == 'nt' else [cv2.CAP_ANY]

        for backend in backends:
            for idx in range(max_devices):
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        h, w, c = frame.shape
                        backend_name = "MSMF" if backend == cv2.CAP_MSMF else "DirectShow"
                        if not any(d["index"] == idx for d in available):
                            available.append({
                                "index": idx,
                                "name": f"Integrated Camera (Device {idx})",
                                "backend": backend_name,
                                "resolution": f"{w}x{h}",
                                "available": True
                            })
                else:
                    cap.release()
            if available:
                break
        return available

    def capture_frame(self, device_override: Optional[int] = None) -> Dict[str, Any]:
        """Capture a single frame from the camera using MSMF or DirectShow with automatic fallback."""
        start_time = time.perf_counter()
        target_idx = device_override if device_override is not None else self.device_index
        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY]

        cap = None
        used_backend = "UNKNOWN"

        for b_id in backends:
            c = cv2.VideoCapture(target_idx, b_id)
            if c.isOpened():
                cap = c
                used_backend = "MSMF" if b_id == cv2.CAP_MSMF else ("DirectShow" if b_id == cv2.CAP_DSHOW else "ANY")
                break
            c.release()

        try:
            if cap is None or not cap.isOpened():
                return {
                    "success": False,
                    "error": f"Camera device {target_idx} is busy or permissions are not granted by Windows.",
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
            if cap is not None:
                cap.release()


# Global camera instance
camera_capture = CameraCapture()
