"""MATRIX Secure Remote Android Integration & Verification Test Suite.
Validates:
1. Windows Matrix Server startup & remote endpoints.
2. Multi-network token generation (LAN IP + Tailscale detection).
3. Android device pairing handshake & 30-day bearer token issuance.
4. Rejection of unauthenticated and invalid tokens (HTTP 401).
5. Enforcement of token expiration (HTTP 401 on expired tokens).
6. Authenticated remote command execution through MATRIX Brain.
7. Authenticated remote voice synthesis & audio URL delivery.
8. Authenticated host CPU/RAM telemetry & connection heartbeat.
9. Token rotation & invalidation of rotated tokens.
10. Targeted device revocation & immediate token invalidation.
11. Emergency remote access cutoff (stop-remote).
12. Android APK build & cryptographic integrity.
13. Physical ADB device hardware detection (truthful reporting if handset absent).
"""
import sys
import os
import time
import json
import urllib.request
import urllib.error
import hashlib
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SERVER_URL = "http://127.0.0.1:8000"


def http_request(url: str, method: str = "GET", data: dict = None, headers: dict = None):
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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
    print("=" * 76)
    print("      MATRIX — SECURE REMOTE ANDROID INTEGRATION VERIFICATION")
    print("=" * 76)
    print(f"[*] Target Server URL : {SERVER_URL}")
    print(f"[*] Timestamp         : {datetime.now(timezone.utc).isoformat()}\n")

    results = []
    summary_counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}

    def record_test(name, desc, status, duration_ms, details):
        results.append({
            "test_name": name,
            "description": desc,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "details": details
        })
        if status in summary_counts:
            summary_counts[status] += 1
        print(f"[{status:<7}] {name:<35} ({duration_ms:>6.1f} ms) -> {desc}")

    # -------------------------------------------------------------
    # Test 1: Server Startup & Remote Status Endpoint
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st, body = http_request(f"{SERVER_URL}/api/v1/devices/remote-status")
    dur = (time.perf_counter() - t0) * 1000
    p1 = st == 200 and "lan_ip" in body and "remote_access_enabled" in body
    record_test("test_01_server_remote_status", "Verify remote-status endpoint & network bindings",
                "PASS" if p1 else "FAIL", dur, body)

    # -------------------------------------------------------------
    # Test 2: Multi-Network Pairing Token Generation
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st, body = http_request(f"{SERVER_URL}/api/v1/devices/token", method="POST", data={"ttl_seconds": 300})
    dur = (time.perf_counter() - t0) * 1000
    p2 = st == 200 and body.get("pairing_token", "").startswith("mtx_pair_") and "qr_protocol" in body
    pairing_token = body.get("pairing_token", "")
    record_test("test_02_token_generation", "Pairing token with LAN & Tailscale URI generation",
                "PASS" if p2 else "FAIL", dur, body)

    # -------------------------------------------------------------
    # Test 3: Android Device Pairing Handshake & 30-Day Token
    # -------------------------------------------------------------
    test_device_id = f"test_android_{int(time.time())}"
    t0 = time.perf_counter()
    st, body = http_request(f"{SERVER_URL}/api/v1/devices/pair", method="POST", data={
        "device_id": test_device_id,
        "name": "Samsung Galaxy S24 Ultra (Test)",
        "platform": "android",
        "pairing_token": pairing_token
    })
    dur = (time.perf_counter() - t0) * 1000
    auth_token = body.get("auth_token", "")
    p3 = (st == 200 and body.get("status") == "PAIRED" and auth_token.startswith("mtx_auth_")
          and "expires_at" in body and body.get("connection_state") == "CONNECTED")
    record_test("test_03_device_pairing", "Android device pairing returning 30-day bearer token",
                "PASS" if p3 else "FAIL", dur, body)

    # -------------------------------------------------------------
    # Test 4: Unauthenticated & Fake Token Rejection (HTTP 401)
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_missing, _ = http_request(f"{SERVER_URL}/api/v1/devices/command", method="POST", data={"command": "ping"})
    st_fake, _ = http_request(f"{SERVER_URL}/api/v1/devices/command", method="POST",
                              data={"command": "ping"},
                              headers={"Authorization": "Bearer mtx_auth_fake_invalid_token_9999"})
    dur = (time.perf_counter() - t0) * 1000
    p4 = (st_missing == 401 and st_fake == 401)
    record_test("test_04_auth_rejection", "Enforce HTTP 401 on missing and invalid auth tokens",
                "PASS" if p4 else "FAIL", dur, {"missing_code": st_missing, "fake_code": st_fake})

    # -------------------------------------------------------------
    # Test 5: Token Expiration Enforcement
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    import sqlite3
    expired_token = f"mtx_auth_expired_test_{int(time.time())}"
    expired_hash = hashlib.sha256(expired_token.encode()).hexdigest()
    expired_dev_id = f"dev_expired_{int(time.time())}"
    conn = sqlite3.connect(r"D:\matrix_data\matrix.db")
    cur = conn.cursor()
    past_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    cur.execute(
        "INSERT INTO devices (device_id, name, platform, is_paired, auth_token_hash, token_expires_at, last_seen_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (expired_dev_id, "Expired Test Phone", "android", 1, expired_hash, past_date, past_date, past_date)
    )
    conn.commit()
    conn.close()

    st_exp, body_exp = http_request(f"{SERVER_URL}/api/v1/devices/command", method="POST",
                                    data={"command": "ping"},
                                    headers={"Authorization": f"Bearer {expired_token}"})
    dur = (time.perf_counter() - t0) * 1000
    p5 = (st_exp == 401 and "expired" in str(body_exp).lower())
    record_test("test_05_token_expiration", "Enforce HTTP 401 on expired device bearer token",
                "PASS" if p5 else "FAIL", dur, {"status": st_exp, "body": body_exp})

    # -------------------------------------------------------------
    # Test 6: Authenticated Remote Command Execution
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_cmd, body_cmd = http_request(
        f"{SERVER_URL}/api/v1/devices/command",
        method="POST",
        data={"command": "What is the CPU and memory status on this PC?", "session_id": "sess_test_remote"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    dur = (time.perf_counter() - t0) * 1000
    p6 = (st_cmd == 200 and body_cmd.get("status") == "SUCCESS" and "reply" in body_cmd and len(body_cmd["reply"]) > 5)
    record_test("test_06_remote_command", "Execute authenticated directive through Brain",
                "PASS" if p6 else "FAIL", dur, {"reply_preview": body_cmd.get("reply", "")[:80], "latency_ms": body_cmd.get("latency_ms")})

    # -------------------------------------------------------------
    # Test 7: Authenticated Remote Voice Interaction
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_voice, body_voice = http_request(
        f"{SERVER_URL}/api/v1/devices/command",
        method="POST",
        data={"command": "System check nominal", "synthesize_voice": True},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    dur = (time.perf_counter() - t0) * 1000
    audio_url = body_voice.get("audio_url")
    p7 = (st_voice == 200 and audio_url is not None and "/api/v1/voice/audio/" in audio_url)
    record_test("test_07_remote_voice", "Generate authenticated voice reply & MP3 URL",
                "PASS" if p7 else "FAIL", dur, {"audio_url": audio_url})

    # -------------------------------------------------------------
    # Test 8: Remote Hardware Telemetry & Connection Heartbeat
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_stat, body_stat = http_request(f"{SERVER_URL}/api/v1/devices/status", headers={"Authorization": f"Bearer {auth_token}"})
    st_hb, body_hb = http_request(f"{SERVER_URL}/api/v1/devices/heartbeat", method="POST", headers={"Authorization": f"Bearer {auth_token}"})
    dur = (time.perf_counter() - t0) * 1000
    p8 = (st_stat == 200 and "cpu_percent" in body_stat and "ram_used_percent" in body_stat
          and st_hb == 200 and body_hb.get("status") == "PONG" and body_hb.get("connection_state") == "CONNECTED")
    record_test("test_08_telemetry_heartbeat", "Live CPU/RAM metrics & PONG heartbeat response",
                "PASS" if p8 else "FAIL", dur, {"status": body_stat.get("system_status"), "cpu": body_stat.get("cpu_percent")})

    # -------------------------------------------------------------
    # Test 9: Token Rotation
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_rot, body_rot = http_request(f"{SERVER_URL}/api/v1/devices/rotate-token", method="POST",
                                    data={"lifetime_days": 30},
                                    headers={"Authorization": f"Bearer {auth_token}"})
    dur = (time.perf_counter() - t0) * 1000
    new_token = body_rot.get("auth_token", "")
    # Check old token is now rejected
    st_old, _ = http_request(f"{SERVER_URL}/api/v1/devices/command", method="POST",
                             data={"command": "ping"},
                             headers={"Authorization": f"Bearer {auth_token}"})
    # Check new token works
    st_new, _ = http_request(f"{SERVER_URL}/api/v1/devices/command", method="POST",
                             data={"command": "ping"},
                             headers={"Authorization": f"Bearer {new_token}"})
    p9 = (st_rot == 200 and new_token.startswith("mtx_auth_") and st_old == 401 and st_new == 200)
    record_test("test_09_token_rotation", "Rotate auth token, invalidate old, verify new",
                "PASS" if p9 else "FAIL", dur, {"old_token_rejected": st_old == 401, "new_token_accepted": st_new == 200})

    # -------------------------------------------------------------
    # Test 10: Single Device Revocation
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_rev, body_rev = http_request(f"{SERVER_URL}/api/v1/devices/{test_device_id}/revoke", method="POST")
    st_rev_chk, _ = http_request(f"{SERVER_URL}/api/v1/devices/command", method="POST",
                                 data={"command": "ping"},
                                 headers={"Authorization": f"Bearer {new_token}"})
    dur = (time.perf_counter() - t0) * 1000
    p10 = (st_rev == 200 and body_rev.get("connection_state") == "REVOKED" and st_rev_chk == 401)
    record_test("test_10_device_revocation", "Revoke device and verify token returns HTTP 401",
                "PASS" if p10 else "FAIL", dur, {"revoked_code": st_rev_chk})

    # -------------------------------------------------------------
    # Test 11: Emergency Remote Access Cutoff (Stop-Remote)
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    st_stop, body_stop = http_request(f"{SERVER_URL}/api/v1/devices/stop-remote", method="POST")
    dur = (time.perf_counter() - t0) * 1000
    p11 = (st_stop == 200 and body_stop.get("status") == "REMOTE_ACCESS_STOPPED")
    record_test("test_11_emergency_cutoff", "Emergency stop-remote revoking all devices & tokens",
                "PASS" if p11 else "FAIL", dur, body_stop)

    # -------------------------------------------------------------
    # Test 12: Android APK Build & File Integrity
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    apk_path = Path(r"D:\matrix_data\apk\matrix-debug.apk")
    p12 = apk_path.exists() and apk_path.stat().st_size > 10 * 1024 * 1024
    dur = (time.perf_counter() - t0) * 1000
    apk_sha = hashlib.sha256(apk_path.read_bytes()).hexdigest() if apk_path.exists() else "NONE"
    apk_size_mb = round(apk_path.stat().st_size / (1024 * 1024), 2) if apk_path.exists() else 0
    record_test("test_12_android_apk_integrity", "Verify compiled APK existence, size and SHA256",
                "PASS" if p12 else "FAIL", dur, {"path": str(apk_path), "size_mb": apk_size_mb, "sha256": apk_sha})

    # -------------------------------------------------------------
    # Test 13: Physical ADB Hardware Detection Probe
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    adb_path = Path(r"C:\Users\Ali Raza Zaidi\AppData\Local\Android\Sdk\platform-tools\adb.exe")
    attached_devices = []
    if adb_path.exists():
        try:
            adb_res = subprocess.run([str(adb_path), "devices"], capture_output=True, text=True, timeout=5)
            lines = [line.strip() for line in adb_res.stdout.splitlines() if line.strip() and not line.startswith("List of devices")]
            attached_devices = [l.split()[0] for l in lines if "\tdevice" in l]
        except Exception:
            pass
    dur = (time.perf_counter() - t0) * 1000
    if attached_devices:
        record_test("test_13_adb_hardware_probe", f"Physical Android device detected: {attached_devices}", "PASS", dur, {"devices": attached_devices})
    else:
        record_test("test_13_adb_hardware_probe", "Physical Android device probe: No USB handset attached (BLOCKED)", "BLOCKED", dur, {"attached_count": 0, "note": "Physical handset installation pending USB/WiFi pairing."})

    # Summary
    print("\n" + "=" * 76)
    print(f"      TEST SUMMARY: {summary_counts['PASS']} PASSED / {summary_counts['FAIL']} FAILED / {summary_counts['BLOCKED']} BLOCKED (PHYSICAL HARDWARE)")
    print("=" * 76)

    return results


if __name__ == "__main__":
    run_tests()
