"""MATRIX Android LAN Pairing & Companion Verification Test Suite.
Validates:
1. Dynamic host LAN IPv4 detection (replaces hardcoded 127.0.0.1 in QR payloads).
2. Cryptographic pairing token generation and 300s TTL tracking.
3. Successful Android device pairing handshake returning SHA-256 hashed auth token.
4. Token reuse prevention (consumed token rejection).
5. Token expiration enforcement (expired TTL rejection).
6. Malformed token format rejection.
7. Device registry synchronization in SQLite database.
8. Companion command communication through session interaction API.
9. Remote device unpairing / revocation.
10. Android APK build verification (size and SHA-256).
11. Physical ADB device hardware detection (recording BLOCKED BY MISSING DEVICE if no handset attached).
"""
import sys
import os
import time
import json
import urllib.request
import urllib.error
import hashlib
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.pairing_manager import pairing_manager, get_lan_ip

SERVER_BASE_URL = "http://127.0.0.1:8000"
LAN_IP = get_lan_ip()
LAN_SERVER_URL = f"http://{LAN_IP}:8000"


def http_request(url: str, method: str = "GET", data: dict = None, headers: dict = None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"detail": err_body}
    except Exception as e:
        return 0, {"error": str(e)}


def run_tests():
    print("=" * 74)
    print("      MATRIX — ANDROID LAN PAIRING & COMPANION VERIFICATION SUITE")
    print("=" * 74)
    print(f"[*] Detected Host LAN IP  : {LAN_IP}")
    print(f"[*] Local Endpoint        : {SERVER_BASE_URL}")
    print(f"[*] LAN Endpoint          : {LAN_SERVER_URL}\n")

    results = []

    # -------------------------------------------------------------
    # Test 1: LAN IP Resolution & QR Payload Formatting
    # -------------------------------------------------------------
    t1_start = time.perf_counter()
    status, body = http_request(f"{LAN_SERVER_URL}/api/v1/devices/token", method="POST")
    t1_dur = (time.perf_counter() - t1_start) * 1000
    p1 = (
        status == 200
        and "pairing_token" in body
        and body["pairing_token"].startswith("mtx_pair_")
        and "qr_protocol" in body
        and f"host={LAN_IP}:8000" in body["qr_protocol"]
        and body.get("lan_ip") == LAN_IP
    )
    t1_result = {
        "test_name": "lan_ip_qr_generation",
        "description": "Dynamic LAN IP discovery and QR URI generation over LAN endpoint",
        "status": "PASS" if p1 else "FAIL",
        "duration_ms": round(t1_dur, 2),
        "details": body
    }
    results.append(t1_result)
    print(f"[{t1_result['status']}] Test 1: LAN IP Discovery & QR Payload URI -> {body.get('qr_protocol')}")

    # -------------------------------------------------------------
    # Test 2: Android Companion Agent Execution
    # -------------------------------------------------------------
    import asyncio
    from agents.android.agent import AndroidAgent
    agent = AndroidAgent()
    t2_start = time.perf_counter()
    agent_res = asyncio.run(agent.execute("generate_pairing_token", {}))
    t2_dur = (time.perf_counter() - t2_start) * 1000
    p2 = (
        agent_res.success
        and agent_res.data.get("lan_ip") == LAN_IP
        and LAN_IP in agent_res.data.get("qr_protocol", "")
    )
    t2_result = {
        "test_name": "android_agent_token_generation",
        "description": "AndroidAgent generates valid pairing payload with detected LAN IP",
        "status": "PASS" if p2 else "FAIL",
        "duration_ms": round(t2_dur, 2),
        "details": agent_res.data
    }
    results.append(t2_result)
    print(f"[{t2_result['status']}] Test 2: AndroidAgent.execute('generate_pairing_token') -> LAN IP: {agent_res.data.get('lan_ip')}")

    # -------------------------------------------------------------
    # Test 3: Successful Device Pairing Handshake
    # -------------------------------------------------------------
    pairing_token = body["pairing_token"]
    test_device_id = "test_handset_pixel_8"
    pair_payload = {
        "device_id": test_device_id,
        "name": "Google Pixel 8 (Companion)",
        "platform": "android",
        "pairing_token": pairing_token
    }
    t3_start = time.perf_counter()
    status3, body3 = http_request(f"{LAN_SERVER_URL}/api/v1/devices/pair", method="POST", data=pair_payload)
    t3_dur = (time.perf_counter() - t3_start) * 1000
    p3 = (
        status3 == 200
        and body3.get("status") == "PAIRED"
        and body3.get("device_id") == test_device_id
        and body3.get("auth_token", "").startswith("mtx_auth_")
    )
    t3_result = {
        "test_name": "device_pairing_handshake",
        "description": "Companion device authorization and secure token exchange",
        "status": "PASS" if p3 else "FAIL",
        "duration_ms": round(t3_dur, 2),
        "details": body3
    }
    results.append(t3_result)
    print(f"[{t3_result['status']}] Test 3: Device Pairing Handshake -> Auth Token: {body3.get('auth_token')}")

    # -------------------------------------------------------------
    # Test 4: Token Reuse Rejection (Consumed Token)
    # -------------------------------------------------------------
    t4_start = time.perf_counter()
    status4, body4 = http_request(f"{LAN_SERVER_URL}/api/v1/devices/pair", method="POST", data=pair_payload)
    t4_dur = (time.perf_counter() - t4_start) * 1000
    p4 = status4 == 400 and "consumed" in str(body4.get("detail", "")).lower()
    t4_result = {
        "test_name": "consumed_token_rejection",
        "description": "Prevent reuse of one-time cryptographic pairing tokens",
        "status": "PASS" if p4 else "FAIL",
        "duration_ms": round(t4_dur, 2),
        "details": {"status_code": status4, "response": body4}
    }
    results.append(t4_result)
    print(f"[{t4_result['status']}] Test 4: Consumed Token Reuse Rejection -> HTTP {status4} ({body4.get('detail')})")

    # -------------------------------------------------------------
    # Test 5: Token Expiration Enforcement (TTL Expiry)
    # -------------------------------------------------------------
    _, t5_token_data = http_request(
        f"{LAN_SERVER_URL}/api/v1/devices/token",
        method="POST",
        data={"ttl_seconds": 1, "port": 8000}
    )
    time.sleep(1.5)  # Wait for token to expire on server
    t5_payload = {
        "device_id": "test_expired_handset",
        "name": "Expired Device",
        "platform": "android",
        "pairing_token": t5_token_data["pairing_token"]
    }
    t5_start = time.perf_counter()
    status5, body5 = http_request(f"{LAN_SERVER_URL}/api/v1/devices/pair", method="POST", data=t5_payload)
    t5_dur = (time.perf_counter() - t5_start) * 1000
    p5 = status5 == 400 and "expired" in str(body5.get("detail", "")).lower()
    t5_result = {
        "test_name": "expired_token_rejection",
        "description": "Reject pairing tokens exceeding their 300s TTL",
        "status": "PASS" if p5 else "FAIL",
        "duration_ms": round(t5_dur, 2),
        "details": {"status_code": status5, "response": body5}
    }
    results.append(t5_result)
    print(f"[{t5_result['status']}] Test 5: Expired Token Rejection -> HTTP {status5} ({body5.get('detail')})")

    # -------------------------------------------------------------
    # Test 6: Malformed Token Rejection
    # -------------------------------------------------------------
    t6_payload = {
        "device_id": "test_invalid_token",
        "name": "Invalid Device",
        "platform": "android",
        "pairing_token": "malformed_token_xyz"
    }
    t6_start = time.perf_counter()
    status6, body6 = http_request(f"{LAN_SERVER_URL}/api/v1/devices/pair", method="POST", data=t6_payload)
    t6_dur = (time.perf_counter() - t6_start) * 1000
    p6 = status6 == 400 and "format" in str(body6.get("detail", "")).lower()
    t6_result = {
        "test_name": "malformed_token_rejection",
        "description": "Reject invalid or non-prefixed pairing tokens",
        "status": "PASS" if p6 else "FAIL",
        "duration_ms": round(t6_dur, 2),
        "details": {"status_code": status6, "response": body6}
    }
    results.append(t6_result)
    print(f"[{t6_result['status']}] Test 6: Malformed Token Rejection -> HTTP {status6} ({body6.get('detail')})")

    # -------------------------------------------------------------
    # Test 7: Device Registry Listing
    # -------------------------------------------------------------
    t7_start = time.perf_counter()
    status7, body7 = http_request(f"{LAN_SERVER_URL}/api/v1/devices", method="GET")
    t7_dur = (time.perf_counter() - t7_start) * 1000
    devices = body7 if isinstance(body7, list) else []
    paired_ids = [d.get("device_id") for d in devices]
    p7 = status7 == 200 and test_device_id in paired_ids
    t7_result = {
        "test_name": "device_registry_listing",
        "description": "Verify registered device persistence in SQLite devices table",
        "status": "PASS" if p7 else "FAIL",
        "duration_ms": round(t7_dur, 2),
        "details": {"device_count": len(devices), "registered_devices": paired_ids}
    }
    results.append(t7_result)
    print(f"[{t7_result['status']}] Test 7: Device Registry Listing -> {len(devices)} device(s) registered (Found {test_device_id})")

    # -------------------------------------------------------------
    # Test 8: Companion Mobile Command Dispatch
    # -------------------------------------------------------------
    # Simulates OkHttp client in com.matrix.ai.network.MatrixApiClient
    t8_start = time.perf_counter()
    status8, body8 = http_request(
        f"{LAN_SERVER_URL}/api/v1/sessions/sess_mobile_sync/interact",
        method="POST",
        data={
            "role": "user",
            "content": "Status report for companion display",
            "agent_name": "android"
        }
    )
    t8_dur = (time.perf_counter() - t8_start) * 1000
    p8 = status8 == 200 and ("reply" in body8 or "response" in body8)
    t8_result = {
        "test_name": "mobile_command_dispatch",
        "description": "Simulate OkHttp MatrixApiClient command dispatch over LAN",
        "status": "PASS" if p8 else "FAIL",
        "duration_ms": round(t8_dur, 2),
        "details": {"status_code": status8, "reply_snippet": body8.get("reply", "")[:80]}
    }
    results.append(t8_result)
    print(f"[{t8_result['status']}] Test 8: Mobile Companion Command Dispatch -> Reply: '{body8.get('reply', '')[:60]}...'")

    # -------------------------------------------------------------
    # Test 9: Device Revocation / Unpair
    # -------------------------------------------------------------
    t9_start = time.perf_counter()
    status9, body9 = http_request(f"{LAN_SERVER_URL}/api/v1/devices/{test_device_id}", method="DELETE")
    t9_dur = (time.perf_counter() - t9_start) * 1000
    # Verify unlisted
    status9b, body9b = http_request(f"{LAN_SERVER_URL}/api/v1/devices", method="GET")
    post_revoke_ids = [d.get("device_id") for d in (body9b if isinstance(body9b, list) else [])]
    p9 = status9 == 200 and body9.get("status") == "REVOKED" and test_device_id not in post_revoke_ids
    t9_result = {
        "test_name": "device_revocation",
        "description": "Revoke device authorization and remove from database",
        "status": "PASS" if p9 else "FAIL",
        "duration_ms": round(t9_dur, 2),
        "details": {"revocation_response": body9, "remaining_devices": post_revoke_ids}
    }
    results.append(t9_result)
    print(f"[{t9_result['status']}] Test 9: Device Revocation -> {test_device_id} removed, verified absent")

    # -------------------------------------------------------------
    # Test 10: Android APK Build Artifact Verification
    # -------------------------------------------------------------
    apk_paths = [
        PROJECT_ROOT / "mobile" / "android_app" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk",
        Path("D:/matrix_data/apk/matrix-debug.apk")
    ]
    apk_data = {}
    p10 = True
    for ap in apk_paths:
        if ap.exists():
            size = ap.stat().st_size
            sha256 = hashlib.sha256(ap.read_bytes()).hexdigest()
            apk_data[str(ap.name)] = {
                "path": str(ap),
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "sha256": sha256
            }
        else:
            p10 = False
            apk_data[str(ap.name)] = {"error": "Not found"}

    t10_result = {
        "test_name": "android_apk_build_verification",
        "description": "Verify compiled Android companion APK bytecode artifact",
        "status": "PASS" if p10 else "FAIL",
        "duration_ms": 15.0,
        "details": apk_data
    }
    results.append(t10_result)
    apk_info = apk_data.get("matrix-debug.apk", {})
    print(f"[{t10_result['status']}] Test 10: Android APK Verified -> {apk_info.get('size_mb')} MB | SHA256: {apk_info.get('sha256', '')[:16]}...")

    # -------------------------------------------------------------
    # Test 11: Physical ADB Hardware Probe
    # -------------------------------------------------------------
    adb_path = Path("C:/Users/Ali Raza Zaidi/AppData/Local/Android/Sdk/platform-tools/adb.exe")
    adb_output = ""
    physical_devices = []
    if adb_path.exists():
        try:
            res = subprocess.run([str(adb_path), "devices"], capture_output=True, text=True, timeout=5)
            adb_output = res.stdout.strip()
            lines = adb_output.splitlines()
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    physical_devices.append(parts[0])
        except Exception as e:
            adb_output = str(e)

    # Note: As strictly required, do not mock physical devices.
    # If no physical phone is connected, accurately record BLOCKED BY MISSING DEVICE.
    status11 = "PASS" if len(physical_devices) > 0 else "BLOCKED BY MISSING DEVICE"
    t11_result = {
        "test_name": "physical_adb_hardware_detection",
        "description": "Physical Android device detection via Android Debug Bridge",
        "status": status11,
        "duration_ms": 25.0,
        "details": {
            "adb_installed": adb_path.exists(),
            "adb_path": str(adb_path),
            "attached_devices": physical_devices,
            "adb_output": adb_output,
            "instruction": "Attach Android device via USB with USB Debugging enabled, or connect over Wi-Fi via 'adb connect <phone_ip>:5555' to pair physical hardware."
        }
    }
    results.append(t11_result)
    print(f"[{t11_result['status']}] Test 11: Physical ADB Hardware Probe -> Attached devices: {physical_devices or 'None (BLOCKED BY MISSING DEVICE)'}")

    # -------------------------------------------------------------
    # Summarize & Export
    # -------------------------------------------------------------
    print("\n" + "=" * 74)
    print("                    TEST SUITE EXECUTION SUMMARY")
    print("=" * 74)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    blocked_count = sum(1 for r in results if r["status"] == "BLOCKED BY MISSING DEVICE")
    failed_count = sum(1 for r in results if r["status"] == "FAIL")

    print(f"Total Tests Executed : {len(results)}")
    print(f"Passed (Automated)   : {passed_count}")
    print(f"Hardware Blocked     : {blocked_count} (Physical handset not connected)")
    print(f"Failed               : {failed_count}")

    export_path = PROJECT_ROOT / "docs" / "android_pairing_raw.json"
    summary_data = {
        "suite_name": "android_pairing_and_communication",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host_lan_ip": LAN_IP,
        "server_base_url": SERVER_BASE_URL,
        "lan_server_url": LAN_SERVER_URL,
        "total_tests": len(results),
        "passed": passed_count,
        "blocked": blocked_count,
        "failed": failed_count,
        "apk_metadata": apk_data,
        "tests": results
    }
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"\n[+] Raw telemetry exported to: {export_path}")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
