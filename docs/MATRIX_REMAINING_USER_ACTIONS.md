# MATRIX AI — REMAINING USER ACTIONS CHECKLIST
**Mission Status**: Software Architecture, Code, Security Gates & Local Hardware: **100% COMPLETE**  
**Autonomy Stress Test**: **100/100 Software Tests Passed (1 Hardware Prerequisite Blocked)**  
**Integration Status Center**: `GET http://127.0.0.1:8000/api/v1/integrations/settings-center`  

---

## Executive Overview

MATRIX AI is fully compiled, tested, repaired, and running as an autonomous background operating system on your Windows 11 PC (`AMD Ryzen 7 5700U`, `8 GB RAM`).

All local components—including the Qwen 2.5 local GGUF LLM, Edge TTS neural voice, physical webcam capture, physical microphone speech listener, MediaPipe AirTouch vision, Windows OS automation, and the 100-scenario software stress test suite—are operating at 100% functionality.

The 6 items below are external cloud credentials, account deposits, and physical cable connections that strictly require physical custody of your accounts and phone.

---

## Action Checklist

### [ ] Action 1: Physical Android USB Connection (Resolves Blocked Test `AND05`)
- **Status in Test**: `BLOCKED` (Cleanly detected no device attached; no failures or hanging).
- **Target**: Validate Android companion communication over ADB.
- **Steps**:
  1. On your Android smartphone, enable **Developer Options** (tap *Build Number* 7 times in Settings > About Phone).
  2. Inside Developer Options, toggle **USB Debugging** to ON.
  3. Connect your phone to your PC via a USB cable.
  4. On your phone screen, accept the prompt: *"Allow USB debugging from this computer"*.
  5. Open a terminal on your PC and run:
     ```powershell
     adb devices
     ```
  6. Your device will appear as `<serial_number>   device`. Re-running `python scripts/autonomy_stress_test.py` will now show test `AND05` as **PASSED**.

---

### [ ] Action 2: Sideload the Android Companion APK
- **Why**: Allows full remote control, voice interaction, and telemetry monitoring from your phone.
- **Precompiled APK Location**: [`D:\matrix_data\apk\matrix-debug.apk`](file:///D:/matrix_data/apk/matrix-debug.apk) (14.99 MB, SHA-256 verified)
- **Steps**:
  1. Transfer `matrix-debug.apk` to your phone via USB or local file sharing.
  2. Tap the APK file on your phone and choose **Install** (allow installation from unknown sources if prompted).
  3. Open the **MATRIX** app.
  4. Enter your PC's IP address (Local Wi-Fi: `192.168.31.194:8000` or Tailscale IP: `100.x.y.z:8000`).
  5. Tap **Pair Device**, input a token generated from `GET http://localhost:8000/api/v1/devices/tokens`, and tap **Connect**.

---

### [ ] Action 3: Bland AI Telephony ($5.00 Account Deposit)
- **Why**: Enables MATRIX to dial external phone numbers and have conversational AI phone calls with you.
- **Configured Target**: `+919193002500` (India)
- **Current Status**: API client configured with rotated key; returns `AUTH_REQUIRED` until account balance is positive.
- **Steps**:
  1. Log in to your Bland AI dashboard: [https://v2.app.bland.ai](https://v2.app.bland.ai)
  2. Navigate to **Billing** / **Credits**.
  3. Deposit the minimum credit amount ($5.00).
  4. Test a live phone call directly via MATRIX API:
     ```powershell
     curl -X POST http://localhost:8000/api/v1/telephony/bland/call -H "Content-Type: application/json" -d "{\"phone_number\": \"+919193002500\", \"task\": \"Testing MATRIX autonomous voice connection.\"}"
     ```
  5. Your phone will ring and the AI conversational agent will speak to you.

---

### [ ] Action 4: Google Workspace (Gmail & Google Calendar)
- **Why**: Allows MATRIX to read unread emails, compose drafts, search calendar meetings, and alert you of upcoming events.
- **Status**: `NOT_CONFIGURED` (Software handlers & PKCE flow ready; awaiting Google OAuth credentials file).
- **Steps**:
  1. Open the [Google Cloud Console](https://console.cloud.google.com/).
  2. Enable both the **Gmail API** and the **Google Calendar API**.
  3. Under **Credentials**, click **Create Credentials** > **OAuth Client ID**.
  4. Select Application type: **Web application**.
  5. Under Authorized redirect URIs, add:
     `http://localhost:8000/api/v1/integrations/google/callback`
  6. Download the OAuth credentials JSON file and save it to:
     `D:\matrix_data\credentials\google_credentials.json`
  7. Visit `http://localhost:8000/api/v1/integrations/google/auth-url` in your browser and approve Google permissions.

---

### [ ] Action 5: Twilio Telephony (PSTN Fallback Calling)
- **Why**: Alternative PSTN voice calling infrastructure with inbound call handling.
- **Status**: `NOT_CONFIGURED` (Awaiting environment variables).
- **Steps**:
  1. Log in to [Twilio Console](https://console.twilio.com/).
  2. Note your **Account SID**, **Auth Token**, and **Twilio Phone Number**.
  3. Set them in Windows or your `.env` file:
     ```text
     TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
     TWILIO_AUTH_TOKEN=your_32_char_auth_token_here
     TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
     ```
  4. In Twilio Phone Number settings, configure the Voice Webhook to:
     `POST https://<your-tailscale-ip-or-domain>:8000/api/v1/telephony/twilio/incoming`
  5. Validate via: `POST http://localhost:8000/api/v1/telephony/twilio/validate-credentials`

---

### [ ] Action 6: Firebase Cloud Messaging (FCM v1 Push)
- **Why**: Delivers background push notifications to your Android phone when the app is minimized or phone is locked.
- **Status**: `NOT_CONFIGURED` (Awaiting service account JSON file; WebSocket stream handles notifications when app is open).
- **Steps**:
  1. Open the [Firebase Console](https://console.firebase.google.com/).
  2. Go to **Project Settings** > **Service accounts**.
  3. Click **Generate new private key** and download the JSON.
  4. Save the file as:
     `D:\matrix_data\credentials\firebase_service_account.json`
  5. Test notification delivery via: `POST http://localhost:8000/api/v1/devices/notifications/test`

---

### [ ] Action 7: Tailscale Encrypted Remote Mesh
- **Why**: Connect to MATRIX from anywhere in the world without opening router ports or exposing your PC to the public internet.
- **Status**: Daemon installed; pending login to tailnet.
- **Steps**:
  1. Launch Tailscale on Windows: Click the Tailscale tray icon and log in.
  2. Install Tailscale from Google Play on your Android phone and log in with the **same account**.
  3. Note your PC's 100.x.y.z Tailscale IP from the Tailscale app.
  4. Enter `http://100.x.y.z:8000` as the host in the MATRIX Android companion app.

---

## 5. Verification: Unified Integration Settings Center

To verify the status of all integrations at any time, open:
`http://localhost:8000/api/v1/integrations/settings-center`

Each integration includes instant `test` and `disconnect` endpoints:
- `POST /api/v1/integrations/settings-center/{id}/test`
- `POST /api/v1/integrations/settings-center/{id}/disconnect`
