"""Fix the cv2 import in vision/camera/capture.py - v2"""
import os

filepath = os.path.join(os.path.dirname(__file__), 'vision', 'camera', 'capture.py')
if not os.path.exists(filepath):
    filepath = r'C:\Users\Ali Raza Zaidi\Desktop\matrix\vision\camera\capture.py'

with open(filepath, 'r') as f:
    content = f.read()

# Replace the try/except with a more robust version that catches all exceptions
old_try = """try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False"""

new_try = """try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False"""

if old_try in content:
    content = content.replace(old_try, new_try)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Fixed cv2 import in {filepath}")
else:
    print("Could not find the try/except block to replace")
    # Show the current content around the try block
    idx = content.find("try:")
    if idx >= 0:
        print("Found try at position", idx)
        print(content[idx:idx+100])