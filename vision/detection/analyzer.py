"""MATRIX Vision Scene & Image Analysis Engine.
Computes image metrics (sharpness, brightness, contrast, edge density) and integrates with AI models.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import time
import cv2
import numpy as np
from PIL import Image
from config.logging_config import get_logger

logger = get_logger("vision.analyzer")


class VisionAnalyzer:
    """Analyzes captured image files and extracts perceptual features."""

    def analyze_image(self, image_path: Path) -> Dict[str, Any]:
        """Compute perceptual metrics and diagnostic features of an image file."""
        start_time = time.perf_counter()

        if not image_path.exists():
            return {"success": False, "error": f"Image file not found: {image_path}"}

        # Load with OpenCV
        cv_img = cv2.imread(str(image_path))
        if cv_img is None:
            return {"success": False, "error": "Unable to decode image file via OpenCV"}

        h, w, c = cv_img.shape
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 1. Luminance & Brightness
        mean_brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # 2. Sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_score = float(laplacian.var())

        # 3. Edge density (Canny)
        edges = cv2.Canny(gray, 100, 200)
        edge_density = float(np.count_nonzero(edges) / (w * h))

        # 4. Dominant Colors (3-channel BGR -> RGB)
        img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        avg_r = float(np.mean(img_rgb[:, :, 0]))
        avg_g = float(np.mean(img_rgb[:, :, 1]))
        avg_b = float(np.mean(img_rgb[:, :, 2]))

        latency = (time.perf_counter() - start_time) * 1000

        return {
            "success": True,
            "filepath": str(image_path),
            "dimensions": {"width": w, "height": h, "channels": c},
            "brightness": round(mean_brightness, 2),
            "contrast": round(contrast, 2),
            "sharpness_score": round(sharpness_score, 2),
            "edge_density": round(edge_density, 4),
            "dominant_rgb": {
                "red": round(avg_r, 1),
                "green": round(avg_g, 1),
                "blue": round(avg_b, 1)
            },
            "latency_ms": round(latency, 2)
        }

    async def describe_scene(self, image_path: Path, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Synthesize a natural language scene description from visual analysis."""
        analysis = self.analyze_image(image_path)
        if not analysis.get("success"):
            return analysis

        w = analysis["dimensions"]["width"]
        h = analysis["dimensions"]["height"]
        brightness = analysis["brightness"]
        sharpness = analysis["sharpness_score"]
        edge_density = analysis["edge_density"]

        # Formulate structured description
        lighting = "well-lit" if brightness > 120 else ("moderately lit" if brightness > 60 else "dark/low-light")
        detail = "high-detail" if edge_density > 0.05 else "low-detail/smooth"
        focus = "sharp/in-focus" if sharpness > 100 else "soft/diffuse"

        summary = (
            f"Visual Frame ({w}x{h}): Captured scene is {lighting} (brightness: {brightness}/255), "
            f"featuring {focus} elements (sharpness: {sharpness}) with {detail} structural density."
        )

        return {
            "success": True,
            "summary": summary,
            "analysis": analysis,
            "question": prompt or "General scene inspection"
        }

    def compare_images(self, path1: Path, path2: Path) -> Dict[str, Any]:
        """Compute visual similarity and structural diff between two frames."""
        if not path1.exists() or not path2.exists():
            return {"success": False, "error": "One or both image files not found"}
        img1 = cv2.imread(str(path1), cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(str(path2), cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            return {"success": False, "error": "Failed to decode one or both images"}
        # Resize to match dimensions if needed
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        diff = cv2.absdiff(img1, img2)
        non_zero = np.count_nonzero(diff > 30)
        similarity = 1.0 - (non_zero / (img1.shape[0] * img1.shape[1]))
        return {
            "success": True,
            "similarity_score": round(similarity, 4),
            "changed_pixels_ratio": round(non_zero / (img1.shape[0] * img1.shape[1]), 4),
            "is_identical": similarity > 0.99
        }

    def find_ui_elements(self, image_path: Path) -> Dict[str, Any]:
        """Detect rectangular interactive UI elements (buttons, inputs) using morphological contours."""
        if not image_path.exists():
            return {"success": False, "error": "Image file not found"}
        img = cv2.imread(str(image_path))
        if img is None:
            return {"success": False, "error": "Unable to decode image"}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        elements = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            # Filter typical button/input dimensions
            if 40 < w < 600 and 20 < h < 150:
                elements.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})
        return {
            "success": True,
            "detected_elements_count": len(elements),
            "candidate_elements": elements[:20]
        }


# Global Vision Analyzer singleton
vision_analyzer = VisionAnalyzer()
