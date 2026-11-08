# MATRIX — Android Physical Device Companion Acceptance Test & Guide

## 1. Acceptance Verdict

```
STATUS: BLOCKED BY MISSING DEVICE
AUTOMATED LOGIC VERIFIED: PASS (10/10 tests passed)
PHYSICAL HARDWARE TEST: BLOCKED (No physical Android phone attached via ADB)
```

> [!IMPORTANT]
> In accordance with release audit integrity guidelines, MATRIX will **never** simulate, mock, or fake physical hardware attachments. `adb devices` was executed against `C:\Users\Ali Raza Zaidi\AppData\Local\Android\Sdk\platform-tools\adb.exe` and returned an empty device list. Automated protocol, token lifecycle, and network endpoints are 100% verified. When a physical device is connected, follow the guide below to complete physical verification.

---

## 2. Companion Build Artifact Specifications

| Property | Value |
|---|---|
| **Artifact Name** | `matrix-debug.apk` |
| **Location 1** | `mobile/android_app/app/build/outputs/apk/debug/app-debug.apk` |
| **Location 2** | `D:\matrix_data\apk\matrix-debug.apk` |
| **Byte Size** | `15,622,267` bytes (~14.9 MB) |
| **SHA-256 Hash** | `51039e2148a718036e3746f8574a6de69e211cbed2b5acbec135fcaa7c9423a4` |
| **Minimum Android SDK**| API 26 (Android 8.0 Oreo) |
| **Target Android SDK** | API 34 (Android 14) |
| **UI Framework** | Jetpack Compose Material3 with holographic HUD theme |

---

## 3. Host Network & Firewall Configuration

To ensure your Android device can connect to the Windows PC running MATRIX:

### 1. Ensure Shared Local Network
- Connect both the Windows 11 PC and the Android handset to the **same Wi-Fi router / SSID**.
- PC Host LAN IP: `192.168.31.194`
- Gateway Port: `8000`

### 2. Windows Defender Firewall Permission
Run PowerShell as Administrator if inbound traffic is restricted:
```powershell
New-NetFirewallRule -DisplayName "MATRIX Core Gateway" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```
Or via Windows Command Prompt:
```cmd
netsh advfirewall firewall add rule name="MATRIX Core Server" dir=in action=allow protocol=TCP localport=8000
```

---

## 4. Physical Sideloading & Pairing Walkthrough

### Step 1: Install the APK on your Android Device
Choose either Option A (via USB ADB) or Option B (Direct Wi-Fi Sideload):

#### Option A: Via USB Cable & ADB
1. On your phone: Go to **Settings > About Phone** and tap **Build Number** 7 times to enable Developer Options.
2. Enable **USB Debugging** in Developer Options.
3. Connect your phone to the PC via USB cable.
4. On the PC, run:
   ```cmd
   "C:\Users\Ali Raza Zaidi\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r "D:\matrix_data\apk\matrix-debug.apk"
   ```

#### Option B: Direct Wi-Fi Download
1. Open the phone's web browser (e.g. Chrome) and navigate to:
   ```
   http://192.168.31.194:8000/
   ```
2. Download `matrix-debug.apk` and tap **Install** (allow installation from this source if prompted).

---

### Step 2: Launch & Pair Companion App
1. On the PC, open the MATRIX Command HUD or generate a pairing token via:
   ```cmd
   python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/devices/token').read().decode())"
   ```
2. The response will provide:
   ```
   matrix://pair?token=mtx_pair_<hex>&host=192.168.31.194:8000
   ```
3. Open the **MATRIX Mobile** app on your phone.
4. If launched via deep-link or scanned via QR code, the app will instantly submit `POST /api/v1/devices/pair`.
5. Upon successful handshake:
   - Top status displays `CORE LINK: NOMINAL` with green indicator.
   - Central holographic ring begins rotating.
   - Real-time command stream is active.

---

## 5. Verification Checklist for Physical Sign-Off

When physical testing is performed:
- [ ] Phone and PC on same Wi-Fi subnet.
- [ ] App launches without crashing.
- [ ] Top bar displays green Wi-Fi indicator (`CORE LINK: NOMINAL`).
- [ ] Holographic cyan core ring animates smoothly.
- [ ] Sending a text command from mobile returns assistant reply in conversation stream.
- [ ] Device appears under `GET /api/v1/devices` with `is_paired=True`.
- [ ] `DELETE /api/v1/devices/{device_id}` successfully unlinks the phone.
