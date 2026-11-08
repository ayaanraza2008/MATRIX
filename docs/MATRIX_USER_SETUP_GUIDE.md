# MATRIX AI — COMPREHENSIVE USER SETUP GUIDE
**Target System**: Windows 11 Home | AMD Ryzen 7 5700U | 8 GB RAM  
**Project Workspace**: `C:\Users\Ali Raza Zaidi\Desktop\matrix`  
**Persistent Storage**: `D:\matrix_data\`  

This guide provides exact, step-by-step instructions for configuring every external third-party integration and connecting your physical Android smartphone.

---

## 1. Google Workspace (Gmail & Google Calendar)

### Prerequisites
- A Google account (personal `@gmail.com` or Google Workspace domain).

### Setup Instructions
1. Open [Google Cloud Console](https://console.cloud.google.com/) in your browser.
2. Click **Select a project** > **New Project**. Name it `Matrix-AI` and click **Create**.
3. In the left navigation menu, go to **APIs & Services** > **Library**:
   - Search for **Google Calendar API** and click **Enable**.
   - Search for **Gmail API** and click **Enable**.
4. Go to **APIs & Services** > **OAuth consent screen**:
   - Select User Type **External** and click **Create**.
   - Fill in App Name (`MATRIX AI`) and your email for User Support Email and Developer Contact.
   - Click **Save and Continue**.
   - In **Scopes**, click **Add or Remove Scopes** and select:
     - `https://www.googleapis.com/auth/calendar.events`
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.compose`
     - `https://www.googleapis.com/auth/gmail.send`
   - In **Test users**, add your personal Google account email address. Click **Save and Continue**.
5. Go to **APIs & Services** > **Credentials**:
   - Click **+ Create Credentials** > **OAuth client ID**.
   - Select Application Type: **Web application**.
   - Under **Authorized redirect URIs**, click **+ Add URI** and paste:
     ```
     http://localhost:8000/api/v1/integrations/google/callback
     ```
   - Click **Create**.
6. Download the credentials JSON file:
   - Click the download icon (Download JSON) next to your newly created OAuth Client ID.
   - Rename the downloaded file to `google_credentials.json`.
   - Move or copy it to:
     ```
     D:\matrix_data\credentials\google_credentials.json
     ```
7. Authorize MATRIX:
   - Open your browser to:
     ```
     http://localhost:8000/api/v1/integrations/google/auth-url
     ```
   - Copy the returned `auth_url` and paste it into your browser.
   - Sign in with your Google account and click **Allow**.
   - You will be redirected to the MATRIX confirmation page (`http://localhost:8000/api/v1/integrations/google/callback`), confirming successful token exchange.

---

## 2. Twilio PSTN Telephony Gateway

### Prerequisites
- A Twilio account ([twilio.com](https://www.twilio.com/try-twilio)).

### Setup Instructions
1. Log in to your [Twilio Console](https://console.twilio.com/).
2. On the dashboard, locate your **Account SID** and **Auth Token**.
3. Under **Phone Numbers** > **Manage** > **Active numbers**, provision or purchase a phone number with **Voice** capabilities.
4. Click on your active phone number to configure its Voice webhooks:
   - Under **A CALL COMES IN**, select **Webhook** (HTTP POST).
   - If using Tailscale: `https://<tailscale-ip>:8000/api/v1/telephony/twilio/incoming`
   - If using a domain or reverse proxy: `https://<your-domain>/api/v1/telephony/twilio/incoming`
   - Under **CALL STATUS CHANGES**, select **Webhook** (HTTP POST) and enter:
     `https://<your-domain>/api/v1/telephony/twilio/status`
   - Click **Save configuration**.
5. Set environment variables on your Windows PC:
   Open PowerShell as Administrator and run:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('TWILIO_ACCOUNT_SID', 'ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX', 'User')
   [System.Environment]::SetEnvironmentVariable('TWILIO_AUTH_TOKEN', 'your_auth_token_here', 'User')
   [System.Environment]::SetEnvironmentVariable('TWILIO_PHONE_NUMBER', '+1XXXXXXXXXX', 'User')
   ```
6. Set your verified personal phone number in MATRIX:
   Make a POST request to update your calling policy:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/telephony/policy \
     -H "Content-Type: application/json" \
     -d '{"verified_phone_number": "+14155552671", "pstn_calling_enabled": true}'
   ```

---

## 3. Firebase Cloud Messaging (FCM HTTP v1)

### Prerequisites
- A Google account.

### Setup Instructions
1. Open the [Firebase Console](https://console.firebase.google.com/) and click **Add project** (select or name `matrix-companion`).
2. Go to **Project Settings** (gear icon) > **Service accounts**.
3. Click **Generate new private key** > **Generate key**.
4. A JSON file will be downloaded (e.g. `matrix-companion-firebase-adminsdk-xxxxx.json`).
5. Rename the downloaded file to `firebase_service_account.json` and move it to:
   ```
   D:\matrix_data\credentials\firebase_service_account.json
   ```
6. Verify FCM readiness by opening:
   ```
   http://127.0.0.1:8000/api/v1/devices/notifications/setup-wizard
   ```
   The endpoint will report `"configured": true` and show your project ID.

---

## 4. Tailscale Private Mesh Network

### Prerequisites
- Tailscale account (free for personal use, up to 100 devices at [tailscale.com](https://tailscale.com)).

### Setup Instructions
1. **Windows 11 Host**:
   - Download and install Tailscale for Windows from [tailscale.com/download/windows](https://tailscale.com/download/windows).
   - Launch Tailscale from the Windows Start menu or System Tray.
   - Click **Log in** and authenticate with your identity provider (Google, Microsoft, Apple, GitHub).
   - Once connected, right-click the Tailscale tray icon and copy your Tailscale IP (`100.x.y.z`).
2. **Android Smartphone**:
   - Open Google Play Store on your Android phone and install **Tailscale**.
   - Open Tailscale, click **Sign In**, and log in using the **exact same account** as on Windows.
   - Toggle the Tailscale switch to **Connected**.
3. **Configure MATRIX Android App**:
   - Open the MATRIX companion app on your phone.
   - In the Server Host configuration field, enter:
     ```
     100.x.y.z:8000
     ```
     (replacing `100.x.y.z` with your Windows PC's Tailscale IP).
   - Click **Test Connection**. All mobile traffic will now route encrypted through your private WireGuard mesh even when on cellular data or foreign Wi-Fi.

---

## 5. Physical Android Device APK Installation

### Prerequisites
- Android smartphone running Android 8.0 (API 26) or newer.
- USB-C cable or local network file transfer.

### Setup Instructions (Option A: USB Sideload via ADB)
1. On your Android phone, enable **Developer Options**:
   - Go to **Settings** > **About Phone**.
   - Tap **Build Number** 7 times until you see "You are now a developer!".
2. In **Settings** > **System** > **Developer Options**, toggle **USB Debugging** to **ON**.
3. Connect your smartphone to your Windows PC using a USB cable.
4. On your phone screen, accept the prompt: **"Allow USB debugging from this computer?"** and check **"Always allow"**.
5. In Windows PowerShell, run:
   ```powershell
   & "C:\Users\Ali Raza Zaidi\AppData\Local\Android\Sdk\platform-tools\adb.exe" devices -l
   ```
   Your phone will appear in the output.
6. Install the compiled MATRIX APK:
   ```powershell
   & "C:\Users\Ali Raza Zaidi\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r "D:\matrix_data\apk\matrix-debug.apk"
   ```
7. Launch the app on your phone:
   ```powershell
   & "C:\Users\Ali Raza Zaidi\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.matrix.ai/.MainActivity
   ```

### Setup Instructions (Option B: Direct File Transfer)
1. Copy `D:\matrix_data\apk\matrix-debug.apk` directly to your phone via USB file transfer, Google Drive, or local file sharing.
2. On your phone, tap the file in your Files app and tap **Install**. If prompted, toggle **"Allow from this source"**.
3. Open **MATRIX AI** from your phone's app drawer.
4. Enter your host IP (`192.168.31.194:8000` on local Wi-Fi or `100.x.y.z:8000` via Tailscale).
5. Generate a pairing token on your PC (`GET http://localhost:8000/api/v1/devices/tokens`), enter the 6-character token in the app, and tap **Pair**.
