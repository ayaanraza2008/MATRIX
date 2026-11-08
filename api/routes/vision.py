"""MATRIX Vision System API Route.
Provides camera capture, desktop screenshot analysis, native OCR, perceptual vision inspection,
and direct image frame serving.
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import time
import shutil

from vision.camera.capture import camera_capture
from vision.screenshot.capture import desktop_screen_capture
from vision.detection.analyzer import vision_analyzer
from vision.ocr.engine import ocr_engine
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("api.vision")
router = APIRouter(prefix="/vision", tags=["Vision System"])


class AnalyzeRequest(BaseModel):
    filepath: str
    question: Optional[str] = "Describe this scene"


class OCRRequest(BaseModel):
    filepath: str


@router.get("/frame/{filename}")
async def get_frame_image(filename: str):
    """Serve a captured camera or screenshot image file to the frontend UI."""
    # Prevent path traversal
    safe_filename = Path(filename).name
    candidate_paths = [
        settings.cache_dir / "vision" / safe_filename,
        settings.cache_dir / "uploads" / safe_filename,
    ]
    for p in candidate_paths:
        if p.exists() and p.is_file():
            media_type = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            return FileResponse(path=str(p), media_type=media_type)

    raise HTTPException(status_code=404, detail="Image frame not found.")


@router.get("/devices")
async def list_camera_devices():
    """List physical camera devices detected on the system."""
    devices = camera_capture.list_devices()
    return {"status": "OK", "devices": devices, "count": len(devices)}


@router.post("/camera")
async def capture_camera():
    """Capture a single frame from the physical Integrated Camera."""
    result = camera_capture.capture_frame()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Camera capture failed."))

    if result.get("filepath"):
        img_path = Path(result["filepath"])
        analysis = vision_analyzer.analyze_image(img_path)
        ocr_res = await ocr_engine.extract_text(img_path)
        result["analysis"] = analysis
        result["ocr"] = ocr_res
        result["image_url"] = f"/api/v1/vision/frame/{img_path.name}"

    return result


@router.post("/screenshot")
async def capture_screen():
    """Capture instant desktop screenshot with session security awareness and OCR."""
    result = desktop_screen_capture.capture()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Screenshot capture failed."))

    if result.get("filepath"):
        img_path = Path(result["filepath"])
        analysis = vision_analyzer.analyze_image(img_path)
        ocr_res = await ocr_engine.extract_text(img_path)
        result["analysis"] = analysis
        result["ocr"] = ocr_res
        result["image_url"] = f"/api/v1/vision/frame/{img_path.name}"

    return result


@router.post("/ocr")
async def run_ocr_on_file(payload: OCRRequest):
    """Run native Windows OCR on a local image file."""
    target_path = Path(payload.filepath)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found.")

    ocr_res = await ocr_engine.extract_text(target_path)
    return ocr_res


@router.post("/upload")
async def upload_image_for_analysis(file: UploadFile = File(...)):
    """Upload an image file from the frontend for instant OCR and scene analysis."""
    upload_dir = settings.cache_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"upload_{int(time.time() * 1000)}_{Path(file.filename).name}"
    target_path = upload_dir / safe_name

    with open(target_path, "wb") as f:
        content = await file.read()
        f.write(content)

    analysis = vision_analyzer.analyze_image(target_path)
    ocr_res = await ocr_engine.extract_text(target_path)

    return {
        "success": True,
        "filename": safe_name,
        "filepath": str(target_path),
        "image_url": f"/api/v1/vision/frame/{safe_name}",
        "analysis": analysis,
        "ocr": ocr_res
    }


@router.post("/analyze")
async def analyze_frame(payload: AnalyzeRequest):
    """Analyze an image file and compute perceptual visual metrics."""
    target_path = Path(payload.filepath)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found.")

    res = await vision_analyzer.describe_scene(target_path, prompt=payload.question)
    ocr_res = await ocr_engine.extract_text(target_path)
    res["ocr"] = ocr_res
    return res
