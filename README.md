# MATRIX: Personal AI Ecosystem (PC + Android)

> **"JARVIS-inspired digital operating layer for your devices, tools, workflows, files, and multi-agent systems."**

---

## 1. System Overview

MATRIX is an autonomous personal AI ecosystem designed for Windows 11 PC and Android phones. It operates under a **local-first** paradigm optimized for the AMD Ryzen 7 5700U (8 cores, 16 threads, AVX2) and 8 GB system RAM, with modular fallback to cloud models.

- **Primary Storage**: `D:\matrix_data` (Preserves OS drive C: space)
- **Database**: SQLite with `aiosqlite` async ORM
- **Backend**: Python 3.12 + FastAPI + WebSockets + Pydantic v2
- **Command HUD**: React 19 + TypeScript + Vite + Tailwind CSS + Three.js 3D Holographic Core
- **Mobile Companion**: Kotlin + Jetpack Compose (located in `mobile/android_app/`)
- **Intelligence**: 16 Specialized Agents + Multi-Model Manager (Local GGUF + Ollama + Gemini + FreeLLMAPI)

---

## 2. Verified Implementation Status (16/16 Tests Passing)

- [x] **Project Scaffold & Env**: 49 package modules with typed initializers.
- [x] **Settings & Storage**: Pydantic BaseSettings mapped to `D:\matrix_data`.
- [x] **SQLite Async Database**: 7 ORM tables (`devices`, `user_preferences`, `sessions`, `messages`, `tasks`, `audit_logs`, `capabilities`).
- [x] **FastAPI REST API**: Endpoints for `/health`, `/system`, `/sessions`, `/capabilities`, `/devices`, `/memory`, `/voice`, `/vision`, `/repositories`.
- [x] **System Hardware Telemetry**: Live verified CPU load, RAM pressure, storage partitions.
- [x] **WebSocket Real-time Broker**: `/ws/events` bidirectional event channel and telemetry loop.
- [x] **3D Holographic Command Interface**: React 19 + Three.js holographic core with 14 functional modules.
- [x] **Model Manager & Benchmarking**: Memory-aware model router tailored to 8 GB RAM and AVX2 CPU.
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
- [x] **Automated Test Suite**: 16 Pytest tests passing with 100% success rate in 13.80s.

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
1. Open Android Studio.
2. Select **Open an Existing Project** and navigate to `mobile/android_app/`.
3. Let Gradle sync dependencies (Jetpack Compose BOM, OkHttp, Kotlin Coroutines).
4. Connect an Android phone (with USB Debugging enabled) or start an Android Emulator.
5. Click **Run 'app'** (`Shift + F10`).
6. Set the PC IP in the companion app to connect to `http://<YOUR_PC_IP>:8000/`.
