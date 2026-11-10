"""Test VisionAnalyzer with actual image files."""
from pathlib import Path
from vision.detection.analyzer import compute_image_metrics, compare_images, vision_analyzer

# Use an actual image from cloned repos
img_path = Path(r".\cloned_repos\agentmemory\assets\banner.png")
img_path2 = Path(r".\cloned_repos\agentmemory\assets\icon-400.png")

print(f"Testing with: {img_path.exists()=}, {img_path2.exists()=}")

# Test compute_image_metrics with PIL fallback
print("\n--- Testing compute_image_metrics ---")
result = compute_image_metrics(img_path)
print(f"compute_image_metrics: success={result.get('success')}")
if result.get('success'):
    print(f"  Width: {result.get('width')}")
    print(f"  Height: {result.get('height')}")
    print(f"  Brightness: {result.get('brightness')}")
    print(f"  Contrast: {result.get('contrast')}")
    print(f"  Sharpness: {result.get('sharpness')}")
    print(f"  Edge density: {result.get('edge_density')}")
else:
    print(f"  Error: {result.get('error')}")
    print(f"  PIL error: {result.get('pil_error', 'N/A')}")

# Test compare_images with two different images
print("\n--- Testing compare_images ---")
result = compare_images(img_path, img_path2)
print(f"compare_images different: success={result.get('success')}, similarity={result.get('similarity')}")

# Test with same image
result2 = compare_images(img_path, img_path)
print(f"compare_images same: success={result2.get('success')}, similarity={result2.get('similarity')}")

# Test vision_analyzer describe_scene
print("\n--- Testing vision_analyzer.describe_scene ---")
try:
    result = vision_analyzer.describe_scene(img_path)
    print(f"describe_scene: success={result.get('success')}")
    if result.get('success'):
        print(f"  Summary: {result.get('summary')}")
        print(f"  Metrics: {result.get('metrics')}")
    else:
        print(f"  Error: {result.get('error')}")
except Exception as e:
    print(f"Error: {e}")

# Test analyze_image method
print("\n--- Testing vision_analyzer.analyze_image ---")
try:
    result = vision_analyzer.analyze_image(img_path)
    print(f"analyze_image: success={result.get('success')}")
    if result.get('success'):
        print(f"  Width: {result.get('width')}")
        print(f"  Height: {result.get('height')}")
        print(f"  Brightness: {result.get('brightness')}")
except Exception as e:
    print(f"Error: {e}")