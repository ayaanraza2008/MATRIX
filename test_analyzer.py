"""Test VisionAnalyzer functions with real image files."""
import sys
import os
from pathlib import Path
from vision.detection.analyzer import compute_image_metrics, compare_images, vision_analyzer

# Check if there are any test images
test_images_dir = Path("tests/images")
if test_images_dir.exists():
    images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
    print(f"Found {len(images)} test images in tests/images")
else:
    print("No tests/images directory, checking project root for samples")
    # Look for any sample images
    for root, dirs, files in os.walk("."):
        for f in files:
            if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                print(f"  Found: {os.path.join(root, f)}")

# Test compute_image_metrics with a known image if available
print("\n--- Testing compute_image_metrics ---")

# Test with PIL fallback (no OpenCV needed)
from PIL import Image
test_img = Path("README.md")
if test_img.exists():
    try:
        with Image.open(test_img) as img:
            print(f"README.md: {img.width}x{img.height}, bands: {len(img.getbands())}")
    except Exception as e:
        print(f"Could not read README.md: {e}")

# Test compare_images with two identical files
print("\n--- Testing compare_images ---")
# Just test the function exists and returns correct structure
result = compare_images(Path("README.md"), Path("README.md"))
print(f"compare_images identical: success={result.get('success')}, similarity={result.get('similarity')}")

# Test vision_analyzer describe_scene
print("\n--- Testing vision_analyzer.describe_scene ---")
try:
    # Use the describe_scene method on the exported vision_analyzer
    result = vision_analyzer.describe_scene(Path("README.md"))
    print(f"describe_scene: success={result.get('success')}")
    if result.get('success'):
        print(f"  Summary: {result.get('summary')}")
except Exception as e:
    print(f"Error: {e}")

# Test compute_image_metrics directly
print("\n--- Testing compute_image_metrics directly ---")
result = compute_image_metrics(Path("README.md"))
print(f"compute_image_metrics: success={result.get('success')}")
if result.get('success'):
    print(f"  Width: {result.get('width')}")
    print(f"  Height: {result.get('height')}")
else:
    print(f"  Error: {result.get('error')}")