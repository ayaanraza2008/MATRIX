# MATRIX — Autonomous Operations & User Manual

**Version**: 2.0 Production  
**Target Hardware**: AMD Ryzen 7 5700U • 8 GB RAM • Windows 11 Home  
**Storage Partition**: `D:\matrix_data\`  
**Gateway**: `0.0.0.0:8000`  

---

## 1. Quick Start Guide

### Launching MATRIX
To start the unified server and command HUD, execute from the workspace directory:
```powershell
python run_matrix.py
```
This automatically:
1. Validates Python 3.10+ runtime and AVX2 CPU extensions.
2. Initializes the SQLite database at `D:\matrix_data\matrix.db`.
3. Loads the local Qwen 2.5 0.5B GGUF model into CPU memory.
4. Binds the Core Gateway server to `0.0.0.0:8000`.
5. Opens the browser to the Desktop Command HUD (`http://127.0.0.1:8000/`).
6. Displays the Host LAN IP (e.g. `192.168.31.194:8000`) for mobile pairing.

---

## 2. Hands-Free Voice Control

MATRIX runs a continuous low-resource background acoustic listener on Windows 11.

### Activation Wake Words:
Say either:
- **"Matrix"**
- **"Snap"**

### Operating Modes:
1. **Continuous Mode** (`matrix listen` or `matrix continue listening after answering`):
   - MATRIX will answer your request and automatically resume listening for follow-up commands without requiring another wake word.
2. **Wake-Word Only Mode** (`matrix go to sleep`):
   - Returns to low-resource standby.
3. **Barge-In Interruption** (`matrix stop` or `stop`):
   - Instantly terminates TTS speaker playback (<50ms) and halts the active task.

---

## 3. Android Mobile Companion

The companion app connects your Android phone directly to MATRIX over your local Wi-Fi router.

### Pairing:
1. Ensure both your PC and phone are on the same Wi-Fi network.
2. Generate a pairing token via:
   ```powershell
   python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/devices/token').read().decode())"
   ```
3. Open the companion app (`matrix-debug.apk` in `D:\matrix_data\apk\`).
4. Scan the QR code or open the pairing URI:
   ```
   matrix://pair?token=mtx_pair_<hex>&host=192.168.31.194:8000
   ```
5. Status displays `CORE LINK: NOMINAL` with active command synchronization.

See [Android Acceptance Test Guide](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/ANDROID_DEVICE_ACCEPTANCE_TEST.md) for firewall setup and sideloading details.

---

## 4. 3-Tier Autonomy Policy & Safety Confirmation Gates

MATRIX implements a strict safety policy in `core/autonomy_policy/policy.py`:

- **Level 1 (Autonomous)**: Read-only operations (telemetry, search, memory recall, screen reading). Executes immediately.
- **Level 2 (Semi-Autonomous)**: Reversible write operations (creating scratch files, scaffolding projects, setting preferences). Executes with an audit log.
- **Level 3 (Supervised)**: Potentially destructive actions (file deletion, process termination, system configuration changes).
  - The plan is paused in `WAITING_FOR_INPUT` state.
  - Requires explicit user approval through the Command HUD or voice confirmation.

---

## 5. Maintenance & Backup

- **Database Backup**: The primary SQLite database is located at `D:\matrix_data\matrix.db`. Regular snapshots can be created by copying this file while the server is idle.
- **Model Storage**: Quantized GGUF models are stored in `D:\matrix_data\models\`.

---

## 6. Cross-Reference Documentation
- [System Architecture](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/ARCHITECTURE.md)
- [Architecture Diagrams](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/ARCHITECTURE_DIAGRAM.md)
- [Master Build Status](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/MASTER_BUILD_STATUS.md)
- [Known Limitations](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/KNOWN_LIMITATIONS.md)
