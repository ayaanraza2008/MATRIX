"""MATRIX Vision System API Route.
Provides camera capture, desktop screenshot analysis, and perceptual vision inspection.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from vision.camera.capture import camera_capture
from vision.screenshot.capture import desktop_screen_capture
from vision.detection.analyzer import vision_analyzer
from config.logging_config import get_logger

logger = get_logger("api.vision")
router = APIRouter(prefix="/vision", tags=["Vision System"])


class AnalyzeRequest(BaseModel):
    filepath: str
    question: Optional[str] = "Describe this scene"


@router.post("/camera")
async def capture_camera():
    """Capture a single frame from the physical Integrated Camera."""
    result = camera_capture.capture_frame()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Camera capture failed."))

    # Enrich with vision analysis
    if result.get("filepath"):
        analysis = vision_analyzer.analyze_image(Path(result["filepath"]))
        result["analysis"] = analysis

    return result


@router.post("/screenshot")
async def capture_screen():
    """Capture instant desktop screenshot with session security awareness."""
    result = desktop_screen_capture.capture()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Screenshot capture failed."))

    if result.get("filepath"):
        analysis = vision_analyzer.analyze_image(Path(result["filepath"]))
        result["analysis"] = analysis

    return result


@router.post("/analyze")
async def analyze_frame(payload: AnalyzeRequest):
    """Analyze an image file and compute perceptual visual metrics."""
    target_path = Path(payload.filepath)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found.")

    res = await vision_analyzer.describe_scene(target_path, prompt=payload.question)
    return res
