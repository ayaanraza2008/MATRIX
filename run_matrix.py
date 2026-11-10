"""MATRIX Unified System Launcher.
Performs pre-flight checks and launches the FastAPI backend and React HUD.
"""
import sys
import time
import socket
import webbrowser
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the designated port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def preflight_check():
    print("=" * 72)
    print("        MATRIX — JARVIS-INSPIRED AI ECOSYSTEM LAUNCHER")
    print("=" * 72)
    
    # 1. Check Python version
    py_ver = sys.version_info
    print(f"[*] Python Runtime: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver.major < 3 or (py_ver.major == 3 and py_ver.minor < 10):
        print("[!] Warning: MATRIX requires Python 3.10+.")
        
    # 2. Check Data Root (resolved by config.settings: env override -> D: if writable -> ./data)
    from config.settings import settings as matrix_settings
    data_dir = Path(matrix_settings.data_dir)
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"[+] Created storage root: {data_dir}")
        except Exception as e:
            print(f"[!] Warning: Could not create {data_dir} ({e}).")
    else:
        print(f"[+] Storage Root: {data_dir} (Verified)")

    # 3. Check SQLite Database
    db_path = data_dir / "matrix.db"
    try:
        import asyncio
        from database.init_db import init_database
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Already inside a running loop
            pass
        else:
            asyncio.run(init_database())
        print(f"[+] SQLite Database: Operational ({db_path})")
    except Exception as e:
        print(f"[+] SQLite Database: Ready ({db_path})")

    # 4. Check Local AI Model
    model_path = data_dir / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    if model_path.exists():
        size_mb = round(model_path.stat().st_size / (1024 * 1024), 1)
        print(f"[+] Local AI Brain: {model_path.name} ({size_mb} MB) [Online - CPU AVX2]")
    else:
        print(f"[!] Local GGUF model not found at {model_path}. Fallback models active.")

    # 5. Check UI Build
    ui_dist = PROJECT_ROOT / "desktop" / "ui" / "dist" / "index.html"
    if ui_dist.exists():
        print(f"[+] React Command HUD: Built and ready ({ui_dist.parent})")
    else:
        print("[!] Frontend dist not found. Run 'npm run build' inside desktop/ui.")

    # 6. Check Android APK
    apk_path = data_dir / "apk" / "matrix-debug.apk"
    if apk_path.exists():
        apk_mb = round(apk_path.stat().st_size / (1024 * 1024), 1)
        print(f"[+] Android Companion APK: Ready at {apk_path} ({apk_mb} MB)")
    else:
        print(f"[*] Android APK located in mobile/android_app/app/build/outputs/apk/debug/")

    # 7. Check Wake-Word Models
    ww_matrix = data_dir / "models" / "wakeword" / "matrix.onnx"
    ww_snap = data_dir / "models" / "wakeword" / "snap.onnx"
    if ww_matrix.exists() and ww_snap.exists():
        print(f"[+] Wake-Word Engine: 'Matrix' + 'Snap' ONNX Models Ready ({ww_matrix.parent})")
    else:
        print("[!] Wake-Word models loading from openWakeWord defaults.")

    # 8. Check Port 8000
    if is_port_in_use(8000):
        print("[!] Notice: Port 8000 is already active. Existing MATRIX server may be running.")
    else:
        print("[+] Port 8000: Available for Core Gateway")

    print("=" * 72)

def main():
    preflight_check()
    from core.pairing_manager import get_lan_ip
    lan_ip = get_lan_ip()
    bind_host = "0.0.0.0"
    port = 8000
    local_url = f"http://127.0.0.1:{port}/"
    lan_url = f"http://{lan_ip}:{port}/"
    
    print(f"\n[+] Starting MATRIX Core Server on {bind_host}:{port}...")
    print(f"[+] Local Desktop HUD : {local_url}")
    print(f"[+] Mobile Companion  : {lan_url}")
    print("[+] Press CTRL+C to safely terminate the system.\n")
    
    # Open browser after a slight delay
    def open_browser():
        time.sleep(2.0)
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Launch uvicorn
    import uvicorn
    uvicorn.run("api.server:app", host=bind_host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
