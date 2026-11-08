# MATRIX — Complete System Architecture & Component Diagrams

**Version**: 2.0 Production  
**Target Architecture**: AMD Ryzen 7 5700U (8 Cores / 16 Threads, AVX2) • 8 GB RAM • Windows 11 Home  
**Persistent Storage**: `D:\matrix_data\`  
**Gateway**: `0.0.0.0:8000` (Local Desktop + LAN Mobile Bridge)  

---

## 1. Global System Topology

```mermaid
flowchart TD
    subgraph Clients["Client Access Layers"]
        PC["Desktop Command HUD (React 19 + TypeScript + Vite)"]
        VOICE["Hands-Free Mic Engine (OpenWakeWord + Silero VAD)"]
        MOB["Android Companion App (Kotlin + Compose + OkHttp)"]
    end

    subgraph Gateway["MATRIX API Gateway (FastAPI on Port 8000)"]
        REST["REST API Endpoints (/api/v1/...)"]
        WS["WebSocket Stream (/ws/events)"]
        PAIR["Pairing Manager (300s TTL, LAN IP Discovery)"]
    end

    subgraph Core["Central Intelligence Engine (core/)"]
        BRAIN["AI Brain (core/brain.py)"]
        INTENT["Intent Engine (16 Intent Domains)"]
        REASON["Reasoning Engine (ExecutionPlan Generation)"]
        ORCH["Orchestrator & Coordinator (16 Specialized Agents)"]
        PLANNER["Dependency Task Planner & DAG"]
        STATE["Task State Machine (10 States)"]
    end

    subgraph Models["Dual Inference Engine"]
        LOCAL["Local LLM: Qwen 2.5 0.5B GGUF (CPU AVX2)"]
        REMOTE["Optional Cloud API Fallback (Gemini / Claude / OpenAI)"]
    end

    subgraph Storage["Hardware Storage Partition (D:\matrix_data\)"]
        DB[(SQLite Persistent DB: matrix.db)]
        MODELS[Models: GGUF, ONNX Wakewords, Silero VAD]
        AUDIO[Audio Cache: Edge TTS WAV/MP3]
        APK[Compiled APK: matrix-debug.apk]
    end

    PC -->|HTTP / WS| Gateway
    VOICE -->|PCM Frames| BRAIN
    MOB -->|LAN Wi-Fi| PAIR
    MOB -->|Session Interact| REST

    Gateway --> BRAIN
    BRAIN --> INTENT
    INTENT --> REASON
    REASON --> PLANNER
    PLANNER --> ORCH
    ORCH --> STATE
    BRAIN --> LOCAL
    LOCAL -.->|Fallback| REMOTE

    STATE --> DB
    BRAIN --> DB
    VOICE --> MODELS
    MOB --> APK
```

---

## 2. Hands-Free Voice Lifecycle

```mermaid
stateDiagram-v2
    [*] --> SLEEPING
    SLEEPING --> IDLE : Mode: Standby
    IDLE --> WAKE_DETECTED : Wake-Word Detected ('Matrix' / 'Snap')
    WAKE_DETECTED --> LISTENING : Silero VAD Speech Active
    LISTENING --> TRANSCRIBING : Speech Endpoint Silence Reached (1040ms)
    TRANSCRIBING --> THINKING : Faster-Whisper INT8 Text Output
    THINKING --> EXECUTING : Brain Dispatches Agent Task
    EXECUTING --> SPEAKING : Edge TTS Synthesizes Response
    SPEAKING --> LISTENING : Continuous Mode Resumes
    SPEAKING --> IDLE : Wake-Word Mode Standby
    SPEAKING --> INTERRUPTED : Barge-In Detected ('Stop' / New Speech)
    INTERRUPTED --> IDLE : Sound Device Aborted (<50ms)
```

---

## 3. Autonomy Policy & Security Tier

```mermaid
flowchart LR
    CMD["Incoming Command"] --> POL{"Autonomy Policy"}
    POL -->|Level 1: Read-Only| AUTO["Autonomous Execution (Zero Confirm)"]
    POL -->|Level 2: Reversible| USER_OPT["Autonomous with Log Audit"]
    POL -->|Level 3: Destructive| GATE["WAITING_FOR_INPUT (Hard Confirmation Gate)"]

    GATE -->|User Confirms| EXEC["Execute Destructive Action"]
    GATE -->|User Rejects / Timeout| ABORT["Abort Operation Safely"]
```

---

## 4. Cross-Reference Documentation
- [System Architecture Specification](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/ARCHITECTURE.md)
- [Master Build Status](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/MASTER_BUILD_STATUS.md)
- [Autonomous Operations Manual](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/docs/AUTONOMOUS_OPERATIONS_MANUAL.md)
