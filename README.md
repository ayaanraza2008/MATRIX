# MATRIX: Personal AI Ecosystem (PC + Android)

> **"JARVIS-inspired digital operating layer for your devices, tools, workflows, files, and multi-agent systems."**

---

## 1. System Overview

MATRIX is an autonomous personal AI ecosystem designed for Windows 11 PC and Android phones. It operates under a **local-first** paradigm optimized for the AMD Ryzen 7 5700U (8 cores, 16 threads, AVX2) and 8 GB system RAM, with modular fallback to cloud models.

- **Primary Storage**: `D:\matrix_data` when that drive is writable, otherwise `<repo>/data`
  (override with `MATRIX_DATA_DIR`) so MATRIX runs on hosts and CI runners without a D: drive
- **Database**: SQLite with `aiosqlite` async ORM
- **Backend**: Python 3.12 + FastAPI + WebSockets + Pydantic v2
- **Command HUD**: React 19 + TypeScript + Vite + Tailwind CSS + Three.js 3D Holographic Core
- **Mobile Companion**: Kotlin + Jetpack Compose (located in `mobile/android_app/`)
- **Intelligence**: 16 Specialized Agents + Multi-Model Manager (Local GGUF + Ollama + Gemini + FreeLLMAPI)

---

## 2. Verified Implementation Status (54 automated tests)

- [x] **Project Scaffold & Env**: 49 package modules with typed initializers.
- [x] **Settings & Storage**: Pydantic BaseSettings mapped to `D:\matrix_data`.
- [x] **SQLite Async Database**: 7 ORM tables (`devices`, `user_preferences`, `sessions`, `messages`, `tasks`, `audit_logs`, `capabilities`).
- [x] **FastAPI REST API**: Endpoints for `/health`, `/system`, `/sessions`, `/capabilities`, `/devices`, `/memory`, `/voice`, `/vision`, `/repositories`.
- [x] **System Hardware Telemetry**: Live verified CPU load, RAM pressure, storage partitions.
- [x] **WebSocket Real-time Broker**: `/ws/events` bidirectional event channel and telemetry loop.
- [x] **3D Holographic Command Interface**: React 19 + Three.js holographic core with 14 functional modules.
- [x] **Model Manager & Benchmarking**: Memory-aware model router tailored to 8 GB RAM and AVX2 CPU.
  Measured on reference hardware: Qwen2.5-0.5B-Instruct Q4_K_M runs at **44.6 tokens/s** with
  **+590 MB** resident memory (2 threads). See `docs/benchmarks/llm-cpu-github-runner-2026-11-10.md`.
  The 0.5B model is the safe default for 8 GB hosts; the 1.5B candidate is unmeasured on target hardware.
- [x] **Intent Classification Engine**: Classifies commands, queries, research, coding, workflows, and dialog.
- [x] **Reasoning Engine & Planner**: Formulates step-by-step ExecutionPlans with verification hooks.
- [x] **16 Specialized Agents Grid**:
  1. `ComputerAgent` (PyAutoGUI, PyWinAuto, Windows 11 app launcher, screenshot)
  2. `BrowserAgent` (Web navigation, page content extraction)
  3. `ResearchAgent` (Multi-source research, citation synthesis)
  4. `CodingAgent` (Workspace inspector, syntax validation, pytest runner)
  5. `FileAgent` (PDF, DOCX, XLSX, CSV, TXT parser with protected D:\matrix_data boundary)
  6. `VoiceAgent` (Edge-TTS neural + SAPI5 offline fallback, faster-whisper STT, wake-word)
  7. `VisionAgent` (Integrated Camera capture + desktop inspection)
  8. `AndroidAgent` (Device pairing, mobile notifications, remote task routing)
  9. `SystemAgent` (Hardware monitoring, RAM/CPU load, disk metrics)
  10. `PersonalAgent` (User identity, reminders, calendar)
  11. `AutomationAgent` (Workflow DAGs, SQLite checkpoints, crash recovery)
  12. `CreativeAgent` (ComfyUI / media rendering adapter)
  13. `MemoryAgent` (Zero-fabrication SQLite preferences & factual recall)
  14. `RepoIntelAgent` (65 GitHub starred repositories catalog & adapter generator)
  15. `SecurityAgent` (Deterministic policy enforcement Levels 0-4, command sandbox)
  16. `DataAnalysisAgent` (Descriptive statistics & tabular data processing)
- [x] **Repository Intelligence Engine**: Audited catalog of all 65 GitHub starred repositories from `@ayaanraza2008`.
- [x] **Native Android Companion**: Kotlin + Jetpack Compose app project with OkHttp & WebSocket client.
- [x] **Automated Test Suite**: 54 Pytest tests (foundation, agents, workflows, security, lifecycle,
  adapter truthfulness).
  CI runs the full suite on GitHub's `windows-latest` runner plus a ruff correctness gate — see
  `.github/workflows/ci.yml`. Voice, camera and Android behaviour require real hardware and are not
  covered by CI; see `docs/AUDIT_MILESTONE_1.md` for the honest status matrix.

---

## 2a. Security defaults (read before exposing MATRIX to a LAN)

- Local (loopback) clients are trusted. Any other host must send
  `Authorization: Bearer <MATRIX_API_TOKEN>` or a paired device token.
- `POST /api/v1/developer/execute` (arbitrary Python) stays **disabled** unless
  `MATRIX_DEVELOPER_MODE=true`.
- Only `/api/v1/health`, device pairing and the signed Twilio/Bland webhooks are public.
- Generate a token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

## 3. Quick Start & Execution

### Launch Unified PC Server & Command HUD
```bash
python run_matrix.py
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** to access the complete Command Center.  
Interactive OpenAPI documentation is available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

### Run Full Automated Test Suite
```bash
python -m pytest tests/ -v
```

### Launch React Frontend in Vite Development Mode (Hot-Reload)
```bash
cd desktop/ui
npm run dev
```

### Build & Run the Android Companion App
A debug APK is built on every push by GitHub Actions and published as the
`matrix-android-debug-apk` artifact (≈16 MB) — no local Android SDK required to obtain one.

To build locally instead:
1. Open Android Studio.
2. Select **Open an Existing Project** and navigate to `mobile/android_app/`.
3. Let Gradle sync dependencies (Jetpack Compose BOM, OkHttp, Kotlin Coroutines).
4. Connect an Android phone (with USB Debugging enabled) or start an Android Emulator.
5. Click **Run 'app'** (`Shift + F10`).
6. Set the PC IP in the companion app to connect to `http://<YOUR_PC_IP>:8000/` and provide the
   `MATRIX_API_TOKEN` configured on the PC (required for non-loopback clients).
