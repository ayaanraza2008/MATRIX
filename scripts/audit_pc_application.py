import sys
import os
import time
import subprocess
import asyncio
from pathlib import Path
import httpx
import websockets
import json

# Add project root to sys.path
sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

print("=== PC APPLICATION & WEBSOCKET AUDIT ===")

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/events"

async def test_full_application():
    # 1. Start Server
    print("\n[1/6] Launching MATRIX backend server on port 8000...")
    log_file = open("logs/audit_server.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["python", "run_matrix.py"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Wait for server ready
    ready = False
    for attempt in range(25):
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(f"{BASE_URL}/api/v1/health")
                if res.status_code == 200:
                    ready = True
                    print(f"  [SUCCESS] Server online! Health check responded in attempt {attempt+1}.")
                    break
        except Exception:
            await asyncio.sleep(0.5)

    if not ready:
        print("  [FAILED] Server failed to start within timeout.")
        proc.terminate()
        return False

    audit_success = True

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 2. Test Frontend Static Bundle & Root UI
            print("\n[2/6] Verifying Frontend Root & Static Assets...")
            root_res = await client.get(f"{BASE_URL}/")
            print(f"  GET / -> Status {root_res.status_code}, Length: {len(root_res.text)} bytes")
            has_root_div = '<div id="root">' in root_res.text
            has_title = 'MATRIX' in root_res.text
            print(f"  Contains <div id=\"root\">: {has_root_div}, Contains 'MATRIX': {has_title}")
            if not (root_res.status_code == 200 and has_root_div):
                audit_success = False

            # Test SPA Fallback for all 14 navigation pages
            nav_pages = [
                'dashboard', 'chat', 'voice', 'vision', 'agents', 'automation',
                'research', 'files', 'memory', 'developer', 'repositories',
                'system', 'devices', 'settings'
            ]
            print(f"\n[3/6] Testing all 14 SPA Navigation Pages...")
            for page in nav_pages:
                page_res = await client.get(f"{BASE_URL}/{page}")
                ok = page_res.status_code == 200 and '<div id="root">' in page_res.text
                print(f"  Page /{page:<14} : Status {page_res.status_code} [{'OK' if ok else 'FAIL'}]")
                if not ok:
                    audit_success = False

            # 3. Test Actual Conversational Chat API
            print("\n[4/6] Testing Conversational Chat & Orchestrator...")
            sess_res = await client.post(f"{BASE_URL}/api/v1/sessions", json={"title": "Audit Chat Session"})
            sess_id = sess_res.json().get("session_id")
            print(f"  Created session: {sess_id}")

            chat_res = await client.post(
                f"{BASE_URL}/api/v1/sessions/{sess_id}/interact",
                json={"content": "Report hardware specs and current memory utilization."}
            )
            chat_data = chat_res.json()
            print(f"  Chat Status: {chat_res.status_code}")
            print(f"  Plan Status: {chat_data.get('plan_status')} (Latency: {chat_data.get('latency_ms')}ms)")
            print(f"  Response: {chat_data.get('reply')[:120]}...")
            if chat_res.status_code != 200 or not chat_data.get("reply"):
                audit_success = False

            # 4. Test Error & Boundary States
            print("\n[5/6] Testing Error & Boundary States...")
            err_404 = await client.get(f"{BASE_URL}/api/v1/non_existent_endpoint")
            print(f"  GET /api/v1/non_existent_endpoint -> Status {err_404.status_code} (Expected 404)")
            if err_404.status_code != 404:
                audit_success = False

            err_422 = await client.post(f"{BASE_URL}/api/v1/sessions", json={"title": 12345, "invalid_field": True})
            print(f"  POST /api/v1/sessions (Schema test) -> Status {err_422.status_code}")

            # 5. Test WebSocket Connectivity, Messaging & Disconnect/Reconnect
            print("\n[6/6] Testing WebSocket Connectivity & Echo...")
            async with websockets.connect(WS_URL) as ws:
                # First receive initial handshake
                handshake_raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                handshake = json.loads(handshake_raw)
                print(f"  WebSocket Handshake received: {handshake.get('type')} (status: {handshake.get('payload', {}).get('system_status')})")
                if handshake.get("type") != "handshake":
                    audit_success = False

                payload = {"event": "telemetry_ping", "timestamp": time.time()}
                await ws.send(json.dumps(payload))
                response_ws = await asyncio.wait_for(ws.recv(), timeout=3.0)
                ws_data = json.loads(response_ws)
                print(f"  WebSocket Sent: {payload}")
                print(f"  WebSocket Received: {ws_data.get('type')}")
                if ws_data.get("type") not in ["ack", "telemetry", "telemetry_update"]:
                    audit_success = False

            # Test Reconnection
            print("  Testing WebSocket reconnection...")
            async with websockets.connect(WS_URL) as ws2:
                hs2_raw = await asyncio.wait_for(ws2.recv(), timeout=3.0)
                hs2 = json.loads(hs2_raw)
                print(f"  Reconnection Handshake: {hs2.get('type')}")
                if hs2.get("type") != "handshake":
                    audit_success = False

    finally:
        print("\nShutting down backend process...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        try:
            log_file.close()
        except Exception:
            pass
        print("Backend terminated.")

    print(f"\n=== APPLICATION AUDIT VERDICT: {'ALL TESTS PASSED (VERIFIED)' if audit_success else 'DEFECTS FOUND (FAILED)'} ===")
    return audit_success

if __name__ == "__main__":
    asyncio.run(test_full_application())
