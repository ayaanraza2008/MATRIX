"""MATRIX Unified System Launcher.
Performs pre-flight checks and launches the FastAPI backend and React HUD.
"""
import sys
import os
import time
import webbrowser
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def preflight_check():
    print("=" * 70)
    print("        MATRIX — JARVIS-INSPIRED AI ECOSYSTEM LAUNCHER")
    print("=" * 70)
    
    # 1. Check Python version
    py_ver = sys.version_info
    print(f"[*] Python Runtime: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 10):
        print("[!] Warning: MATRIX requires Python 3.10+.")
        
    # 2. Check Data Root
    data_dir = Path("D:/matrix_data")
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"[+] Created data root: {data_dir}")
        except Exception as e:
            print(f"[!] Warning: Could not create {data_dir} ({e}). Falling back to local storage.")
    else:
        print(f"[+] Storage Root: {data_dir} (Verified)")

    # 3. Check Local AI Model
    model_path = data_dir / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    if model_path.exists():
        size_mb = round(model_path.stat().st_size / (1024 * 1024), 1)
        print(f"[+] Local AI Brain: {model_path.name} ({size_mb} MB) [Online]")
    else:
        print(f"[!] Local GGUF model not found at {model_path}. Fallback models active.")

    # 4. Check UI Build
    ui_dist = PROJECT_ROOT / "desktop" / "ui" / "dist" / "index.html"
    if ui_dist.exists():
        print(f"[+] React Command HUD: Built and ready ({ui_dist.parent})")
    else:
        print("[!] Frontend dist not found. Run 'npm run build' inside desktop/ui.")

    # 5. Check Android APK
    apk_path = data_dir / "apk" / "matrix-debug.apk"
    if apk_path.exists():
        apk_mb = round(apk_path.stat().st_size / (1024 * 1024), 1)
        print(f"[+] Android Companion APK: Ready at {apk_path} ({apk_mb} MB)")
    else:
        print(f"[*] Android APK available in mobile/android_app/app/build/outputs/apk/debug/")

    print("=" * 70)

def main():
    preflight_check()
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/"
    
    print(f"\n[+] Starting MATRIX Core Server at {url}...")
    print("[+] Press CTRL+C to safely terminate the system.\n")
    
    # Open browser after a slight delay
    def open_browser():
        time.sleep(1.8)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Launch uvicorn
    import uvicorn
    uvicorn.run("api.server:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
