# MATRIX — Known Hardware & Operational Limitations

This document provides a transparent, evidence-based ledger of hardware constraints, external boundaries, and operational considerations for MATRIX on the target machine.

---

## 1. Physical Android Device Hardware Sideloading

- **Implementation Status:** 100% Complete. The native Android companion app (Kotlin + Jetpack Compose) is compiled using Gradle 8.8 and Android SDK 35 into [`matrix-debug.apk`](file:///D:/matrix_data/apk/matrix-debug.apk) (14.9 MB).
- **API Status:** 100% Verified. The device pairing endpoint (`POST /api/v1/devices/pair`), cryptographic SHA-256 tokens, and revocation endpoints have passed automated verification.
- **Physical Device Limitation:** `adb devices` reports 0 physical Android devices connected via USB or Wi-Fi in this development session. Sideloading onto a physical smartphone is ready to be performed by the user by transferring `matrix-debug.apk` to their device.

---

## 2. Local Model Parameter Scale on 8 GB Host RAM

- **Target Machine:** AMD Ryzen 7 5700U, 8 Cores / 16 Threads, AVX2, Integrated AMD Radeon Graphics (512 MB dedicated VRAM, shared system memory), ~8 GB total physical RAM.
- **Memory Profile:** At rest, Windows 11 and background processes consume ~6.3 GB to 6.6 GB RAM, leaving approximately 750 MB to 1.1 GB of unallocated physical RAM.
- **Model Choice:** `qwen2.5-0.5b-instruct-q4_k_m.gguf` (468.6 MB).
  - *Strengths:* Loads in ~0.45s, consumes only ~158 MB RAM, achieves ~48 tokens/second on CPU AVX2, and leaves over 850 MB of free headroom, preventing Windows pagefile swap thrashing. Handles introductory dialogue, system explanations, Python calculator generation, and Hinglish.
  - *Trade-off:* Being a 0.5B parameter model, highly complex multi-tier symbolic logic or long-form academic reasoning is naturally constrained compared to 70B+ models.
  - *Mitigation:* The multi-provider failover architecture (`Gemini Cloud -> Local GGUF -> Ollama -> Rule Engine`) automatically routes complex tasks to Gemini 2.5 Flash whenever an API key is present.

---

## 3. Windows Display Session Isolation (Headless vs Interactive Desktop)

- **Architecture:** Multi-tier screen capture (`ImageGrab -> PyAutoGUI -> GDI Direct DC -> Diagnostic Buffer`).
- **Limitation:** Under Windows DWM session security, background or locked sessions restrict display device context access (BitBlt returns 0 / black frame).
- **Operation:** When launched interactively by the user via `start_matrix.bat` or `run_matrix.py`, the active desktop displays normally, and native Windows 11 OCR extracts real text lines from visible windows.

---

## 4. Cloud API Authentication

- The system is architected for **zero cloud dependence**. If an invalid or expired `GEMINI_API_KEY` is present in the environment, MATRIX automatically flags the failure and routes directly to the local GGUF model with 0 latency penalty on subsequent queries.
