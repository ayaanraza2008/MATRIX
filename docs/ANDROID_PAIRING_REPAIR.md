# MATRIX — Android LAN Pairing & Companion Subsystem Repair Report

## 1. Executive Summary

- **Component**: Android Companion Bridge & Device Pairing Subsystem
- **Status**: **AUTOMATED VERIFIED / PHYSICAL HARDWARE BLOCKED (NO DEVICE CONNECTED)**
- **Audit Date**: 2026-11-08
- **Lead Architect**: Autonomous Lead AI Systems Engineer
- **Environment**: Windows 11 Home Single Language (AMD Ryzen 7 5700U, 8 GB RAM)
- **Host LAN IP**: `192.168.31.194`
- **Listening Interface**: `0.0.0.0:8000` (All network interfaces)

---

## 2. Issues Identified & Root Cause Analysis

### Issue A: Hardcoded Loopback (`127.0.0.1`) in QR URI Payloads
- **Defect**: In `agents/android/agent.py`, the pairing QR protocol string was hardcoded as:
  ```python
  "qr_protocol": f"matrix://pair?token={pairing_token}&host=127.0.0.1:8000"
  ```
- **Root Cause**: When an Android phone connected to the same Wi-Fi router scanned the QR code, it resolved `127.0.0.1` to the phone's internal loopback interface rather than the PC host, immediately failing connection.
- **Resolution**: Created `core/pairing_manager.py` featuring `get_lan_ip()`, dynamically routing via UDP socket query to detect the machine's primary subnet IPv4 address (`192.168.31.194`). The QR payload now renders:
  ```
  matrix://pair?token=mtx_pair_<hex>&host=192.168.31.194:8000
  ```

### Issue B: Missing Pairing Token Expiration & Replay Protection
- **Defect**: Previously, `api/routes/devices.py` accepted any token starting with `mtx_pair_` indefinitely, with no TTL and no replay prevention.
- **Root Cause**: Lack of an active token lifecycle registry.
- **Resolution**: Implemented `PairingManager` with thread-safe singleton state:
  - Cryptographic token generation with 300-second TTL.
  - Strict validation: checks prefix, existence, expiration, and one-time consumption.
  - Rejection with HTTP 400 for consumed tokens, expired tokens, and malformed formats.

### Issue C: Gateway Server Exclusively Bound to Localhost
- **Defect**: `run_matrix.py` previously launched `uvicorn.run("api.server:app", host="127.0.0.1", port=8000)`.
- **Root Cause**: Windows network stack prevented any remote Wi-Fi clients from establishing TCP handshakes on port 8000.
- **Resolution**: Changed binding to `0.0.0.0:8000`, allowing simultaneous connections from local desktop browser (`127.0.0.1:8000`) and Wi-Fi mobile clients (`192.168.31.194:8000`).

---

## 3. Implementation Details

### Files Modified & Created:
1. `core/pairing_manager.py`: Core LAN discovery and token lifecycle state manager.
2. `agents/android/agent.py`: Integrated `pairing_manager.create_token()` and dynamic host endpoint.
3. `api/routes/devices.py`: Added `POST /api/v1/devices/token` and `GET /api/v1/devices/tokens`; updated `POST /api/v1/devices/pair` with strict `validate_and_consume()` checks.
4. `run_matrix.py`: Bound uvicorn to `0.0.0.0:8000` and displays both Local Desktop HUD and Mobile Companion endpoints on startup.
5. `scripts/test_android_pairing_lan.py`: 11-step comprehensive automated verification suite.

---

## 4. Test Suite Execution & Verification Evidence

Test suite executed: `python scripts/test_android_pairing_lan.py`  
Raw log: `docs/android_pairing_raw.json`

| Test # | Test Name | Description | Status | Latency |
|---|---|---|---|---|
| 1 | `lan_ip_qr_generation` | Dynamic LAN IP discovery and QR URI generation over LAN | **PASS** | 107.8 ms |
| 2 | `android_agent_token_generation` | AndroidAgent generates valid payload with LAN IP | **PASS** | 1.7 ms |
| 3 | `device_pairing_handshake` | Secure token exchange returning SHA-256 auth token | **PASS** | 21.4 ms |
| 4 | `consumed_token_rejection` | Rejection of used one-time token (HTTP 400) | **PASS** | 3.5 ms |
| 5 | `expired_token_rejection` | Rejection of expired token > TTL (HTTP 400) | **PASS** | 2.9 ms |
| 6 | `malformed_token_rejection` | Rejection of invalid prefix/format (HTTP 400) | **PASS** | 1.8 ms |
| 7 | `device_registry_listing` | SQLite DB persistence of paired companion device | **PASS** | 4.6 ms |
| 8 | `mobile_command_dispatch` | Session command execution from mobile client | **PASS** | 32.1 ms |
| 9 | `device_revocation` | Remote unpairing and DB cleanup | **PASS** | 8.2 ms |
| 10 | `android_apk_build_verification` | Compiled APK bytecode verification (14.9 MB) | **PASS** | 15.0 ms |
| 11 | `physical_adb_hardware_detection` | ADB check for connected physical phone | **BLOCKED BY MISSING DEVICE** | 25.0 ms |

**Total Tests**: 11  
**Automated Tests Passed**: 10 (100.0%)  
**Physical Hardware Blocked**: 1 (No physical device connected via USB/Wi-Fi adb)  
**Failed**: 0  

---

## 5. Android Companion APK Specification

- **Path 1**: `mobile/android_app/app/build/outputs/apk/debug/app-debug.apk`
- **Path 2**: `D:\matrix_data\apk\matrix-debug.apk`
- **Size**: 15,622,267 bytes (14.9 MB)
- **SHA-256**: `51039e2148a718036e3746f8574a6de69e211cbed2b5acbec135fcaa7c9423a4`
- **Architecture**: Kotlin + Jetpack Compose + OkHttp + Gson
