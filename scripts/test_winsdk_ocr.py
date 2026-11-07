import asyncio
from pathlib import Path
from PIL import Image, ImageDraw

# Create a test image with text
test_img_path = Path("D:/matrix_data/test_ocr.png")
test_img_path.parent.mkdir(parents=True, exist_ok=True)
img = Image.new("RGB", (400, 100), color=(255, 255, 255))
draw = ImageDraw.Draw(img)
draw.text((20, 35), "MATRIX AI OPERATING SYSTEM 2026", fill=(0, 0, 0))
img.save(str(test_img_path))

async def test_ocr():
    import winsdk.windows.media.ocr as ocr
    import winsdk.windows.graphics.imaging as imaging
    import winsdk.windows.storage as storage
    import winsdk.windows.storage.streams as streams

    storage_file = await storage.StorageFile.get_file_from_path_async(str(test_img_path.resolve()))
    stream = await storage_file.open_async(storage.FileAccessMode.READ)
    decoder = await imaging.BitmapDecoder.create_async(stream)
    software_bitmap = await decoder.get_software_bitmap_async()

    engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    ocr_result = await engine.recognize_async(software_bitmap)
    print("OCR Recognized Text:", ocr_result.text)

if __name__ == "__main__":
    asyncio.run(test_ocr())
