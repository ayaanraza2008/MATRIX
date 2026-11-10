"""Fix the cv2 import in vision/camera/capture.py"""
import os

filepath = os.path.join(os.path.dirname(__file__), 'vision', 'camera', 'capture.py')
if not os.path.exists(filepath):
    filepath = r'C:\Users\Ali Raza Zaidi\Desktop\matrix\vision\camera\capture.py'

with open(filepath, 'r') as f:
    content = f.read()

# Replace the direct cv2 import with a try/except that provides fallback
old_import = "import cv2"
new_import = """try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False"""

if old_import in content:
    content = content.replace(old_import, new_import)
    # Also replace the backends line that uses cv2.CAP_*
    old_backends = "backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW] if os.name == 'nt' else [cv2.CAP_ANY]"
    new_backends = """backends = ([cv2.CAP_MSMF, cv2.CAP_DSHOW] if _HAS_CV2 and os.name == 'nt' else [cv2.CAP_ANY] if _HAS_CV2 else [])"""
    if old_backends in content:
        content = content.replace(old_backends, new_backends)
    
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Fixed cv2 import in {filepath}")
else:
    print("Could not find the import statement to replace")