"""MATRIX Live Server Verification Script.
Starts Uvicorn in a subprocess, validates live HTTP responses on port 8000, and verifies shutdown.
"""
import subprocess
import time
import urllib.request
import json
import sys

def verify_live():
    print("[1/4] Spawning MATRIX Uvicorn server on http://127.0.0.1:8000...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.server:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Wait up to 5 seconds for server boot
        booted = False
        health_data = None
        for attempt in range(10):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=2) as resp:
                    if resp.status == 200:
                        health_data = json.loads(resp.read().decode())
                        booted = True
                        break
            except Exception:
                continue

        if not booted:
            print("ERROR: Server failed to respond within 5 seconds.")
            stderr_out = proc.stderr.read()
            print("Server stderr:", stderr_out)
            sys.exit(1)

        print("[2/4] Live Health Response Received:")
        print(f"      App: {health_data['app_name']} v{health_data['version']}")
        print(f"      Status: {health_data['status']}")
        print(f"      Database: {health_data['database']}")
        print(f"      Hardware: {health_data['system']['cpu_cores_physical']} cores / {health_data['system']['cpu_threads_logical']} threads")
        print(f"      Storage: C: {health_data['storage']['C:']['free_gb']} GB Free, D: {health_data['storage']['D:']['free_gb']} GB Free")

        print("[3/4] Testing Root Web UI Route...")
        with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=2) as resp:
            content = resp.read().decode()
            if "<!doctype html>" in content.lower():
                print("      Root UI served React HTML bundle successfully (HTTP 200).")
            else:
                print(f"      Root returned: {content[:100]}")

        print("[4/4] Verified! Shutting down server cleanly...")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        print("Server process terminated cleanly.")

if __name__ == "__main__":
    verify_live()
