"""System and Database Comprehensive Inspection Script."""
import os
import sys
import sqlite3
import json
from pathlib import Path

print("=== 1. DATABASE INSPECTION ===")
db_path = Path(r"D:\matrix_data\matrix.db")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Database: {db_path} ({db_path.stat().st_size} bytes)")
    print(f"Total tables: {len(tables)}")
    for t in tables:
        cursor.execute(f"SELECT count(*) FROM {t}")
        cnt = cursor.fetchone()[0]
        print(f"  - {t}: {cnt} rows")
    conn.close()
else:
    print(f"Database not found at {db_path}")

print("\n=== 2. PERSISTENT JSON STORES ===")
for jf in [
    r"D:\matrix_data\security\authorization_profiles.json",
    r"D:\matrix_data\goals.json",
    r"D:\matrix_data\integrations_state.json",
    r"D:\matrix_data\call_history.json",
    r"D:\matrix_data\incidents.json"
]:
    p = Path(jf)
    if p.exists():
        print(f"  - {p.name}: exists ({p.stat().st_size} bytes)")
    else:
        print(f"  - {p.name}: NOT FOUND")

print("\n=== 3. HARDWARE & PYTHON SPECS ===")
import platform
import psutil
print(f"OS: {platform.system()} {platform.release()} (Version: {platform.version()})")
print(f"Machine: {platform.machine()}, Processor: {platform.processor()}")
print(f"Python: {sys.version.split()[0]} ({sys.executable})")
print(f"CPU Physical Cores: {psutil.cpu_count(logical=False)}, Logical Cores: {psutil.cpu_count(logical=True)}")
vm = psutil.virtual_memory()
print(f"RAM Total: {round(vm.total / (1024**3), 2)} GB, Available: {round(vm.available / (1024**3), 2)} GB, Used: {vm.percent}%")

print("\n=== 4. ANDROID PROJECT INSPECTION ===")
android_dir = Path("mobile")
if android_dir.exists():
    print(f"Mobile dir found: {list(android_dir.iterdir())}")
    gradlew = android_dir / "gradlew.bat"
    print(f"gradlew.bat exists: {gradlew.exists()}")
else:
    print("Mobile directory not found")

print("\n=== 5. FRONTEND PROJECT INSPECTION ===")
desktop_dir = Path("desktop")
if desktop_dir.exists():
    pkg = desktop_dir / "package.json"
    dist = desktop_dir / "dist"
    print(f"Desktop package.json exists: {pkg.exists()}")
    print(f"Desktop dist exists: {dist.exists()}")
    if dist.exists():
        print(f"Desktop dist contents: {[f.name for f in dist.iterdir()]}")
else:
    print("Desktop directory not found")
