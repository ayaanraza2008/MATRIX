import sys
import os
import urllib.request
import zipfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

GRADLE_URL = "https://services.gradle.org/distributions/gradle-8.8-bin.zip"
TOOLS_DIR = Path("D:/matrix_data/tools")
TOOLS_DIR.mkdir(parents=True, exist_ok=True)
ZIP_PATH = TOOLS_DIR / "gradle-8.8-bin.zip"
EXTRACT_DIR = TOOLS_DIR

print(f"Target zip path: {ZIP_PATH}")

if not (TOOLS_DIR / "gradle-8.8" / "bin" / "gradle.bat").exists():
    print(f"Downloading Gradle 8.8 from {GRADLE_URL}...")
    headers = {"User-Agent": "Mozilla/5.0 MATRIX Personal AI Build System"}
    req = urllib.request.Request(GRADLE_URL, headers=headers)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp, open(ZIP_PATH, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        last_print = time.time()
        while True:
            chunk = resp.read(1024 * 1024 * 2)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if time.time() - last_print > 3:
                print(f"Downloaded {downloaded / (1024*1024):.1f} / {total / (1024*1024):.1f} MB...")
                last_print = time.time()

    print(f"Download complete in {time.time() - t0:.1f}s. Extracting to {EXTRACT_DIR}...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(EXTRACT_DIR)
    print("Extraction complete!")
else:
    print("Gradle 8.8 already extracted and ready.")

gradle_bat = TOOLS_DIR / "gradle-8.8" / "bin" / "gradle.bat"
print(f"Gradle executable: {gradle_bat} (Exists: {gradle_bat.exists()})")
