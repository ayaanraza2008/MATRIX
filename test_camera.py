"""Test webcam capture with graceful OpenCV fallback."""
import sys
sys.path.insert(0, '.')
from vision.camera.capture import CameraCapture, _HAS_CV2
cap = CameraCapture(device_index=0)
devices = cap.list_devices()
print(f'Camera available: {_HAS_CV2}')
print(f'Devices found: {len(devices)}')
for d in devices:
    print(f'  - {d["name"]} (index {d["index"]}, backend {d["backend"]})')
# Try capturing a frame
res = cap.capture_frame()
print(f'Capture result: success={res.get("success")}')
if res.get('success'):
    print(f'  File saved: {res.get("filepath")}')
    print(f'  Resolution: {res.get("width")}x{res.get("height")}')
    print(f'  Backend: {res.get("backend")}')
else:
    print(f'  Error: {res.get("error")}')