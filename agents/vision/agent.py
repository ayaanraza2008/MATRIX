"""MATRIX Vision & Scene Intelligence Agent.
Captures real webcam frames, performs real desktop screen capture across native display APIs,
extracts on-screen text via native Windows 11 OCR, and performs perceptual scene analysis.
"""
from typing import Dict, Any, Optional
import time
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult
from vision.camera.capture import camera_capture
from vision.screenshot.capture import desktop_screen_capture
from vision.detection.analyzer import vision_analyzer
from vision.ocr.engine import ocr_engine
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("agents.vision")


class VisionAgent(BaseAgent):
    """Executes visual perception, camera capture, desktop screenshot analysis, and OCR."""

    def __init__(self):
        super().__init__(
            name="vision",
            description="Analyzes camera feeds, captures desktop visual state, extracts on-screen text via OCR, and inspects visual elements.",
            max_autonomy_level=1
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("raw_prompt", parameters.get("query", "")).lower()

        # 1. Camera Capture
        if "camera" in action_lower or "webcam" in action_lower or "camera" in raw_prompt:
            return await self._capture_camera_frame(start_time)

        # 2. Desktop Screen Capture & OCR Inspection
        return await self._inspect_desktop_screen(start_time, prompt=parameters.get("query", ""))

    async def _capture_camera_frame(self, start_time: float) -> AgentResult:
        """Capture a physical frame from the integrated webcam."""
        res = camera_capture.capture_frame()
        latency = (time.perf_counter() - start_time) * 1000
        verified = res.get("success", False)

        ocr_text = ""
        scene_summary = ""
        if verified and res.get("filepath"):
            img_path = Path(res["filepath"])
            analysis = vision_analyzer.analyze_image(img_path)
            ocr_res = await ocr_engine.extract_text(img_path)
            ocr_text = ocr_res.get("text", "")
            scene = await vision_analyzer.describe_scene(img_path)
            scene_summary = scene.get("summary", "")
            res["analysis"] = analysis
            res["ocr_text"] = ocr_text
            res["scene_summary"] = scene_summary

        return AgentResult(
            success=verified,
            agent_name=self.name,
            action_taken="capture_camera",
            data=res,
            verification={"frame_saved": verified, "verified": verified},
            error=res.get("error"),
            execution_time_ms=round(latency, 2)
        )

    async def _inspect_desktop_screen(self, start_time: float, prompt: str = "") -> AgentResult:
        """Capture real desktop screen, run native OCR to read on-screen text, and compute scene metrics."""
        capture_res = desktop_screen_capture.capture()
        if not capture_res.get("success"):
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="inspect_screen",
                error=capture_res.get("error", "Desktop capture failed"),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        img_path = Path(capture_res["filepath"])
        
        # 1. Real Perceptual Scene Analysis
        scene_info = await vision_analyzer.describe_scene(img_path, prompt=prompt)
        
        # 2. Real Native Windows 11 OCR Text Extraction
        ocr_res = await ocr_engine.extract_text(img_path)
        extracted_text = ocr_res.get("text", "")
        lines = ocr_res.get("lines", [])

        latency = (time.perf_counter() - start_time) * 1000

        # Construct visual perception summary
        visual_summary = (
            f"Screen captured ({capture_res['width']}x{capture_res['height']} via {capture_res['method']}). "
            f"{scene_info.get('summary', '')} "
            f"OCR detected {len(lines)} text lines on screen."
        )
        if lines:
            sample_lines = " | ".join(lines[:6])
            visual_summary += f" Detected Text: {sample_lines}"

        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="inspect_screen",
            data={
                "filepath": str(img_path),
                "resolution": f"{capture_res['width']}x{capture_res['height']}",
                "method": capture_res["method"],
                "ocr_text": extracted_text[:1000],
                "ocr_lines_count": len(lines),
                "scene_summary": scene_info.get("summary", ""),
                "visual_summary": visual_summary
            },
            verification={"verified": True, "frame_exists": img_path.exists()},
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
