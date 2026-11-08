# MATRIX — THIRD-PARTY INTEGRATION SETUP GUIDE

This document contains step-by-step configuration guides, exact portal URLs, required environment variables, token storage paths, and permission scopes for all MATRIX connectors.

---

## 1. GOOGLE WORKSPACE CONNECTOR (Gmail & Google Calendar)

### Overview
MATRIX uses OAuth2 with PKCE (Proof Key for Code Exchange) to securely connect to Google Calendar and Gmail without storing hardcoded user passwords.

### Step-by-Step Configuration
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one (e.g., `Matrix-AI-Workstation`).
3. Navigate to **APIs & Services** → **Library**.
4. Enable the following two APIs:
   - **Google Calendar API**
   - **Gmail API**
5. Navigate to **APIs & Services** → **OAuth consent screen**:
   - Choose **External** (or Internal if using a Google Workspace domain).
   - Fill in the App Name (e.g., `MATRIX Personal AI`) and User Support Email.
   - Add Scopes:
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/calendar.events`
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.compose`
     - `https://www.googleapis.com/auth/gmail.send`
   - Add your personal Google account as a **Test User**.
6. Navigate to **APIs & Services** → **Credentials**:
   - Click **Create Credentials** → **OAuth client ID**.
   - Select Application Type: **Desktop app** (or Web application).
   - Set Redirect URI to: `http://localhost:8000/api/v1/integrations/google/callback`
   - Download the client credentials JSON or copy the **Client ID** and **Client Secret**.
7. Save client secrets to disk:
   - File path: `D:\matrix_data\credentials\google_client_secrets.json`
   - Format:
     ```json
     {
       "installed": {
         "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
         "client_secret": "YOUR_CLIENT_SECRET",
         "redirect_uris": ["http://localhost:8000/api/v1/integrations/google/callback"]
       }
     }
     ```
   - Or set environment variables:
     ```powershell
     [System.Environment]::SetEnvironmentVariable("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID", "User")
     [System.Environment]::SetEnvironmentVariable("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET", "User")
     ```
8. Authorize MATRIX:
   - Call `GET http://127.0.0.1:8000/api/v1/integrations/google/auth-url`.
   - Open the returned URL in your browser and approve permissions.
   - Copy the authorization code and post it to:
     `POST http://127.0.0.1:8000/api/v1/integrations/google/exchange` with payload `{"code": "AUTH_CODE"}`.

---

## 2. GITHUB DEVELOPER CONNECTOR

### Overview
Allows MATRIX to inspect repositories, commit history, pull requests, open issues, and automate releases.

### Step-by-Step Configuration
1. Go to [GitHub Settings → Developer Settings → Personal Access Tokens](https://github.com/settings/tokens).
2. Click **Generate new token (classic)** or create a **Fine-grained personal access token**.
3. Select Scopes:
   - `repo` (Full control of private repositories)
   - `read:user` (Read user profile data)
   - `workflow` (If automating GitHub Actions workflows)
4. Generate the token and copy the secret string (`ghp_...`).
5. Configure in MATRIX using either method:
   - **Method A (API)**:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/integrations/marketplace/github_api/configure \
       -H "Content-Type: application/json" \
       -d '{"token": "ghp_YOUR_GITHUB_TOKEN"}'
     ```
   - **Method B (File)**: Save token to `D:\matrix_data\credentials\github_token.txt`.
   - **Method C (Environment)**:
     ```powershell
     [System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_YOUR_GITHUB_TOKEN", "User")
     ```

---

## 3. TELEGRAM BOT COMPANION CONNECTOR

### Overview
Enables two-way remote conversation and push notifications with MATRIX outside your home network via your private Telegram bot.

### Step-by-Step Configuration
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to name your bot (e.g., `Matrix_Personal_Bot`).
3. Copy the Bot API Token provided (format: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).
4. To get your personal Telegram Chat ID:
   - Message `@userinfobot` or `@GetMyIdBot` in Telegram.
   - Copy the numerical ID (e.g., `987654321`).
5. Configure in MATRIX:
   - **Method A (API)**:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/integrations/marketplace/telegram_bot/configure \
       -H "Content-Type: application/json" \
       -d '{"token": "YOUR_BOT_TOKEN", "chat_id": "YOUR_CHAT_ID"}'
     ```
   - **Method B (Files)**:
     - Save token to `D:\matrix_data\credentials\telegram_token.txt`
     - Save chat ID to `D:\matrix_data\credentials\telegram_chat_id.txt`

---

## 4. NOTION WORKSPACE CONNECTOR

### Overview
Enables MATRIX to read tasks, query databases, append notes, and document research in your Notion workspace.

### Step-by-Step Configuration
1. Go to [Notion Developers Integrations Portal](https://www.notion.so/profile/integrations).
2. Click **+ New integration**.
3. Name it (e.g., `MATRIX Assistant`) and associate it with your Notion Workspace.
4. Set Capabilities:
   - Read content
   - Update content
   - Insert content
5. Copy the **Internal Integration Secret** (`ntn_...` or `secret_...`).
6. **Important**: Open the Notion pages or databases you want MATRIX to access, click **•••** (top right) → **Connections** → Add your `MATRIX Assistant` integration.
7. Configure in MATRIX:
   - **Method A (API)**:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/integrations/marketplace/notion_api/configure \
       -H "Content-Type: application/json" \
       -d '{"token": "secret_YOUR_NOTION_TOKEN"}'
     ```
   - **Method B (File)**: Save token to `D:\matrix_data\credentials\notion_token.txt`.

---

## 5. HOME ASSISTANT IOT GATEWAY CONNECTOR

### Overview
Connects MATRIX to your local Home Assistant instance for smart lights, thermostats, room sensors, and scenes. Sensitive physical controls (door locks, security alarms) require Level 4 confirmation tokens.

### Step-by-Step Configuration
1. Open your Home Assistant Web Interface (typically `http://homeassistant.local:8123` or your local IP).
2. Click your **User Profile** icon (bottom left).
3. Scroll down to **Long-Lived Access Tokens**.
4. Click **Create Token**, name it `MATRIX-AI`, and copy the token string.
5. Configure in MATRIX:
   - **Method A (API)**:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/integrations/marketplace/home_assistant/configure \
       -H "Content-Type: application/json" \
       -d '{"base_url": "http://192.168.1.100:8123", "token": "YOUR_LONG_LIVED_TOKEN"}'
     ```
   - **Method B (Files)**:
     - Save URL to `D:\matrix_data\credentials\hass_url.txt`
     - Save token to `D:\matrix_data\credentials\hass_token.txt`

---

## 6. TWILIO TELEPHONY PSTN GATEWAY

### Overview
Enables MATRIX to answer incoming telephone phone calls and make outbound PSTN calls to your verified telephone number with TwiML speech synthesis.

### Step-by-Step Configuration
1. Sign up or log into [Twilio Console](https://console.twilio.com/).
2. Copy your **Account SID** and **Auth Token** from the Dashboard.
3. Purchase a Twilio phone number with Voice capabilities.
4. Verify your personal mobile phone number under **Phone Numbers** → **Verified Caller IDs**.
5. Set environment variables:
   ```powershell
   [System.Environment]::SetEnvironmentVariable("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "User")
   [System.Environment]::SetEnvironmentVariable("TWILIO_AUTH_TOKEN", "your_auth_token", "User")
   [System.Environment]::SetEnvironmentVariable("TWILIO_PHONE_NUMBER", "+1xxxxxxxxxx", "User")
   [System.Environment]::SetEnvironmentVariable("USER_PHONE_NUMBER", "+1yyyyyyyyyy", "User")
   ```
6. For inbound calls: Configure the Twilio Phone Number Voice Webhook to point to your public or tunnel URL:
   `POST https://<your-public-url>/api/v1/telephony/inbound`

---

## 7. TAILSCALE PRIVATE REMOTE NETWORK GATEWAY

### Overview
Tailscale creates an encrypted WireGuard mesh network connecting your Windows 11 PC and your Android phone securely without opening public firewall ports or using third-party port forwarders.

### Step-by-Step Configuration
1. Install Tailscale on Windows 11:
   - Download installer from [Tailscale Download](https://tailscale.com/download/windows).
   - Run the installer and sign in with your account.
2. Install Tailscale on your Android phone from Google Play Store:
   - Sign in with the **same account** used on Windows 11.
3. Verify connection:
   - In PowerShell, run: `tailscale status` or `tailscale ip -4`.
   - Your Windows 11 PC will have an IP in the `100.64.0.0/10` CGNAT range (e.g. `100.85.120.44`).
4. MATRIX Tailscale auto-discovery:
   - MATRIX automatically detects `tailscale.exe` and reads your CGNAT IP via `GET /api/v1/devices/tailscale`.
   - In the Android app, enter `100.x.y.z:8000` as the Server Host for seamless connection anywhere in the world.

---

## 8. FIREBASE CLOUD MESSAGING (FCM PUSH NOTIFICATIONS)

### Overview
Delivers background push alerts to the MATRIX Android companion app even when the app is minimized or the screen is off.

### Step-by-Step Configuration
1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Create a project (e.g. `matrix-companion`).
3. Add an Android app with package name: `com.matrix.ai`.
4. Go to **Project Settings** → **Service accounts**.
5. Click **Generate new private key** (downloads a JSON file).
6. Save the downloaded JSON file as:
   `D:\matrix_data\credentials\firebase_service_account.json`
7. In the Android app, the FCM registration token is automatically sent to `POST /api/v1/devices/{device_id}/fcm-token`.
8. Fallback: If Firebase is not configured, MATRIX automatically falls back to broadcasting alerts over active authenticated WebSockets (`/ws/events`).
