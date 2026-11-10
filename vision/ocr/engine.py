"""MATRIX Native Windows 11 OCR Engine.
Uses Windows Media OCR via WinSDK for offline, high-speed optical character recognition on screenshots and images.
"""
from typing import Dict, Any
from pathlib import Path
import time
from config.logging_config import get_logger

logger = get_logger("vision.ocr")


class OCREngine:
    """Offline OCR engine using native Windows 11 Optical Character Recognition."""

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                import winsdk.windows.media.ocr as ocr
                self._engine = ocr.OcrEngine.try_create_from_user_profile_languages()
                if self._engine:
                    logger.info(f"Initialized native Windows OCR ({self._engine.recognizer_language.display_name})")
            except Exception as e:
                logger.error(f"Failed to initialize native Windows OCR engine: {e}")
                self._engine = None
        return self._engine

    async def extract_text(self, image_path: Path) -> Dict[str, Any]:
        """Extract text lines and words from an image file."""
        start_time = time.perf_counter()
        if not image_path.exists():
            return {"success": False, "text": "", "error": f"Image file not found: {image_path}"}

        engine = self._get_engine()
        if not engine:
            return {"success": False, "text": "", "error": "Native Windows OCR engine is unavailable"}

        try:
            import winsdk.windows.graphics.imaging as imaging
            import winsdk.windows.storage as storage

            storage_file = await storage.StorageFile.get_file_from_path_async(str(image_path.resolve()))
            stream = await storage_file.open_async(storage.FileAccessMode.READ)
            decoder = await imaging.BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()

            ocr_result = await engine.recognize_async(software_bitmap)
            full_text = ocr_result.text or ""

            lines = []
            for line in ocr_result.lines:
                lines.append(line.text)

            latency = (time.perf_counter() - start_time) * 1000
            logger.info(f"OCR extracted {len(lines)} lines ({len(full_text)} chars) in {latency:.1f}ms")

            return {
                "success": True,
                "text": full_text,
                "lines": lines,
                "line_count": len(lines),
                "char_count": len(full_text),
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            logger.error(f"OCR extraction failed on {image_path.name}: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2)
            }


# Global OCR singleton
ocr_engine = OCREngine()
