import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true"
TARGET_PATH = Path("D:/matrix_data/models/qwen2.5-0.5b-instruct-q4_k_m.gguf")

TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
print(f"Downloading model to {TARGET_PATH}...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MATRIX AI Assistant"
}
req = urllib.request.Request(MODEL_URL, headers=headers)

t0 = time.time()
with urllib.request.urlopen(req, timeout=30) as resp:
    total_bytes = int(resp.headers.get("Content-Length", 0))
    print(f"Content Length: {total_bytes / (1024*1024):.2f} MB")
    
    downloaded = 0
    chunk_size = 1024 * 1024 * 2 # 2 MB chunks
    last_print = time.time()
    
    with open(TARGET_PATH, "wb") as f:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if time.time() - last_print > 3:
                pct = (downloaded / total_bytes * 100) if total_bytes else 0
                speed = (downloaded / (1024*1024)) / (time.time() - t0)
                print(f"Progress: {downloaded / (1024*1024):.1f} / {total_bytes / (1024*1024):.1f} MB ({pct:.1f}%) @ {speed:.2f} MB/s")
                last_print = time.time()

elapsed = time.time() - t0
print(f"Download complete: {TARGET_PATH.stat().st_size / (1024*1024):.2f} MB in {elapsed:.1f}s!")
