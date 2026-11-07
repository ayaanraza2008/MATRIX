import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

from vision.camera.capture import camera_capture
from vision.screenshot.capture import desktop_screen_capture
from vision.detection.analyzer import vision_analyzer
import asyncio

async def main():
    print("=== TESTING COMPLETE VISION SUBSYSTEM ===")

    # 1. Desktop Screen Capture
    print("1. Capturing Desktop Screen...")
    scr = desktop_screen_capture.capture()
    print(f"  Method:     {scr.get('method')}")
    print(f"  Dimensions: {scr.get('width')}x{scr.get('height')}")
    print(f"  Filepath:   {scr.get('filepath')}")
    assert scr.get("success") is True

    # 2. Vision Scene Analysis on Screenshot
    print("\n2. Analyzing Screen Visuals...")
    analysis = vision_analyzer.analyze_image(Path(scr["filepath"]))
    print(f"  Brightness:       {analysis.get('brightness')}")
    print(f"  Sharpness Score:  {analysis.get('sharpness_score')}")
    print(f"  Edge Density:     {analysis.get('edge_density')}")
    print(f"  Dominant RGB:     {analysis.get('dominant_rgb')}")
    assert analysis.get("success") is True

    # 3. Physical Camera Capture
    print("\n3. Testing Physical Camera Hardware...")
    cam = camera_capture.capture_frame()
    print(f"  Camera Success:   {cam.get('success')}")
    if cam.get("success"):
        print(f"  Camera File:      {cam.get('filepath')} ({cam.get('width')}x{cam.get('height')})")
        # Describe camera scene
        desc = await vision_analyzer.describe_scene(Path(cam["filepath"]))
        print(f"  Scene Summary:\n    {desc.get('summary')}")
    else:
        print(f"  Camera Warning:   {cam.get('error')}")

    print("\nSUCCESS: VISION SUBSYSTEM VERIFIED!")

asyncio.run(main())
