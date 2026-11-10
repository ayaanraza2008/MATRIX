"""MATRIX AirTouch Gesture & Vision API Routes.
Provides REST and WebSocket endpoints for controlling AirTouch modes, telemetry, calibration, and Visual QA.
Handles gracefully environments where OpenCV is unavailable.
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# OpenCV is optional - try to import, graceful fallback if unavailable
_HAS_CV2 = False
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    cv2 = None

import numpy as np

from vision.airtouch.service import airtouch_service
from config.logging_config import get_logger

logger = get_logger("api.airtouch")
router = APIRouter(prefix="/airtouch", tags=["AirTouch Vision & Gesture"])


class ModeRequest(BaseModel):
    mode: str = Field(..., description="Operating mode: OFF, GESTURE_3D, GESTURE_SCROLL, GESTURE_EYE, FULL_VISION")


class SettingsRequest(BaseModel):
    sensitivity_3d: Optional[float] = None
    scroll_speed: Optional[str] = None
    scroll_sensitivity: Optional[float] = None
    dwell_ms: Optional[float] = None
    eye_enabled: Optional[bool] = None


class VisualQueryRequest(BaseModel):
    query: str = Field("What am I looking at?", description="Natural language visual query for Matrix AI Brain")


@router.get("/status")
async def get_airtouch_status():
    """Retrieve current AirTouch operational status, active mode, and engine state."""
    return airtouch_service.get_status()


@router.post("/mode")
async def set_airtouch_mode(req: ModeRequest):
    """Switch AirTouch operating mode."""
    try:
        res = airtouch_service.set_mode(req.mode)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settings")
async def update_airtouch_settings(req: SettingsRequest):
    """Update dynamic AirTouch parameters (sensitivity, speeds, dwell threshold)."""
    settings_dict = {k: v for k, v in req.model_dump().items() if v is not None}
    return airtouch_service.update_settings(settings_dict)


@router.post("/reset_3d")
async def reset_airtouch_3d():
    """Reset Gesture3D rotation matrix and angles to default identity."""
    return airtouch_service.reset_3d()


@router.post("/calibrate")
async def calibrate_airtouch_eye():
    """Trigger or advance GesturEye 5-point screen calibration."""
    return airtouch_service.calibrate_eye()


@router.get("/telemetry")
async def get_airtouch_telemetry():
    """Get the latest real-time tracking telemetry packet."""
    return airtouch_service.latest_telemetry


@router.post("/process_frame")
async def process_frame_upload(file: UploadFile = File(...)):
    """Upload a raw image frame to process through active AirTouch pipelines."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    if _HAS_CV2:
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        # Fallback: skip cv2 decode, return raw bytes info
        frame = None

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image payload.")

    telemetry = airtouch_service.process_frame(frame)
    return telemetry


@router.post("/query")
async def query_visual_scene(req: VisualQueryRequest):
    """Visual Question Answering (VQA) query routed to Modern AI Vision Subsystem."""
    # Use latest available frame or capture from hardware
    from vision.camera.capture import camera_capture
    res = camera_capture.capture_frame()

    if res.get("success") and res.get("filepath"):
        if _HAS_CV2:
            img = cv2.imread(res["filepath"])
        else:
            img = None
    else:
        # Generate diagnostic frame
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        if _HAS_CV2:
            cv2.putText(img, "MATRIX LIVE CAMERA", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    qa_res = airtouch_service.modern_ai.answer_visual_query(img, req.query)
    return qa_res


@router.websocket("/ws")
async def airtouch_websocket_stream(websocket: WebSocket):
    """Real-time bi-directional WebSocket telemetry stream for AirTouch HUD."""
    await websocket.accept()
    logger.info("AirTouch WebSocket client connected.")

    queue = []

    def on_telemetry(data: Dict[str, Any]):
        queue.append(data)

    airtouch_service.subscribe(on_telemetry)

    try:
        import asyncio
        while True:
            # Send pending telemetry updates
            if queue:
                batch = queue.pop(0)
                await websocket.send_json(batch)
            else:
                await asyncio.sleep(0.03)

            # Check for client messages/commands non-blockingly
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.01)
                cmd = data.get("command")
                if cmd == "SET_MODE":
                    airtouch_service.set_mode(data.get("mode", "OFF"))
                elif cmd == "RESET_3D":
                    airtouch_service.reset_3d()
                elif cmd == "CALIBRATE":
                    airtouch_service.calibrate_eye()
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        logger.info("AirTouch WebSocket client disconnected.")
    except Exception as e:
        logger.debug(f"AirTouch WebSocket error: {e}")
    finally:
        airtouch_service.unsubscribe(on_telemetry)