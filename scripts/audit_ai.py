import sys
import psutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

print("=== MATRIX AUDIT: ENVIRONMENT & AI PACKAGES ===")
packages = [
    'torch', 'transformers', 'llama_cpp', 'ollama', 'ctransformers', 
    'onnxruntime', 'cv2', 'PIL', 'sounddevice', 'pyaudio', 'pyttsx3', 
    'edge_tts', 'faster_whisper', 'fastapi', 'uvicorn', 'sqlalchemy'
]

for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'Installed (no __version__)')
        print(f"  [FOUND] {pkg:<16} : {version}")
    except ImportError as e:
        print(f"  [MISSING] {pkg:<14} : Not installed ({e})")

print("\n=== SYSTEM MEMORY STATUS ===")
vm = psutil.virtual_memory()
print(f"  Total RAM:     {vm.total / (1024**3):.2f} GB")
print(f"  Available RAM: {vm.available / (1024**3):.2f} GB ({vm.available / (1024**2):.1f} MB)")
print(f"  Used RAM:      {vm.used / (1024**3):.2f} GB ({vm.percent}%)")

print("\n=== LOCAL MODEL DIRECTORY AUDIT ===")
model_dir = Path("D:/matrix_data/models")
if model_dir.exists():
    files = list(model_dir.glob("*"))
    print(f"  Directory D:/matrix_data/models exists: {len(files)} files found.")
    for f in files:
        size_mb = f.stat().st_size / (1024**2)
        print(f"    - {f.name} ({size_mb:.2f} MB)")
else:
    print(f"  Directory D:/matrix_data/models DOES NOT EXIST or is empty.")
