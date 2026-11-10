"""MATRIX Vision Scene & Image Analysis Engine.
Computes image metrics (sharpness, brightness, contrast, edge density) and integrates with AI models.
Handles gracefully environments where OpenCV is unavailable.
"""
from typing import Dict, Any
from pathlib import Path
import time
import numpy as np

# OpenCV is optional - try to import, graceful fallback if unavailable
_HAS_CV2 = False
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    pass

from PIL import Image
from config.logging_config import get_logger

logger = get_logger("vision.analyzer")


def compute_image_metrics(image_path: Path) -> Dict[str, Any]:
    """Compute perceptual metrics of an image file without requiring OpenCV."""
    start_time = time.perf_counter()
    results: Dict[str, Any] = {
        "success": _HAS_CV2,
        "image_path": str(image_path),
        "width": None,
        "height": None,
        "channels": None,
        "brightness": None,
        "contrast": None,
        "sharpness": None,
        "edge_density": None,
    }

    if not _HAS_CV2:
        results["error"] = "OpenCV not available for image analysis"
        # Try with PIL instead
        try:
            with Image.open(image_path) as img:
                results["width"] = img.width
                results["height"] = img.height
                results["channels"] = len(img.getbands())
                results["success"] = True
                results["error"] = None
        except Exception as e:
            results["pil_error"] = str(e)
        return results

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            results["error"] = "Failed to read image file"
            return results

        height, width, channels = img.shape

        # Brightness: mean of grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        # Contrast: standard deviation of grayscale
        contrast = float(np.std(gray))

        # Sharpness: Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())

        # Edge density: count of strong edges / total pixels
        edges = cv2.Canny(gray, 100, 200)
        edge_density = float(np.count_nonzero(edges)) / (edges.shape[0] * edges.shape[1]) * 100

        results.update({
            "width": width,
            "height": height,
            "channels": channels,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "sharpness": round(sharpness, 2),
            "edge_density": round(edge_density, 2),
            "success": True,
        })
    except Exception as e:
        if logger:
            logger.error(f"Error analyzing image {image_path}: {e}")
        results["error"] = str(e)

    return results


# Export vision_analyzer for API route compatibility
class VisionAnalyzer:
    """Compatibility wrapper for vision_analyzer API.""" 
    def analyze_image(self, image_path: Path) -> Dict[str, Any]:
        return compute_image_metrics(image_path)
    
    def compare_images(self, img1_path: Path, img2_path: Path) -> Dict[str, Any]:
        return compare_images(img1_path, img2_path)
    
    def describe_scene(self, image_path: Path, prompt: str = "Describe this scene") -> Dict[str, Any]:
        """Describe a scene using the available analysis functions."""
        metrics = compute_image_metrics(image_path)
        if metrics.get("success"):
            parts = []
            if metrics.get("width") and metrics.get("height"):
                parts.append(f"image metrics: {metrics['width']}x{metrics['height']}")
            if metrics.get("brightness") is not None:
                parts.append(f"brightness: {metrics['brightness']}")
            if metrics.get("sharpness") is not None:
                parts.append(f"sharpness: {metrics['sharpness']}")
            if metrics.get("edge_density") is not None:
                parts.append(f"edge density: {metrics['edge_density']}")
            summary = ". ".join(parts) if parts else "Image analysis complete"
        else:
            summary = metrics.get("error", "Image analysis failed")
        
        return {
            "success": metrics.get("success", False),
            "summary": summary,
            "metrics": metrics
        }

vision_analyzer = VisionAnalyzer()


def compare_images(img1_path: Path, img2_path: Path) -> Dict[str, Any]:
    """Compare two images for similarity metrics."""
    start_time = time.perf_counter()
    results: Dict[str, Any] = {"success": _HAS_CV2, "error": None, "similarity": None}

    if not _HAS_CV2:
        results["error"] = "OpenCV not available for image comparison"
        return results

    try:
        img1 = cv2.imread(str(img1_path))
        img2 = cv2.imread(str(img2_path))

        if img1 is None or img2 is None:
            results["error"] = "Failed to read one or both image files"
            return results

        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

        # Mean squared error
        mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)

        # Structural similarity index (approximation)
        if mse == 0:
            results["similarity"] = 100.0
        else:
            psnr = 10 * np.log10(255 ** 2 / mse)
            results["similarity"] = round(min(100.0, 100 - psnr * 10 / 50), 2)

        results["success"] = True
    except Exception as e:
        if logger:
            logger.error(f"Error comparing images: {e}")
        results["error"] = str(e)

    return results