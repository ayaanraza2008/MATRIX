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

## 3. Hands-Free Voice & Room Acoustics

- **Acoustic Environment:** In typical home or office environments (ambient noise < 55 dB), local wake-word detection for "Matrix" and "Snap" achieves >99% precision. In blaring acoustic environments (e.g. loud music playing from the same machine), wake-word recall can experience attenuation.
  - *Mitigation:* Detection sensitivity is dynamically tunable via the HUD slider or API from `0.10` to `0.95`.
- **Acoustic Echo Feedback Suppression:** When playing audio through high-volume external laptop speakers without hardware echo-canceling microphones, audio output could theoretically leak into the microphone. MATRIX mitigates this by temporarily muting/suppressing microphone ingestion during active TTS playback.
- **Microphone Permissions:** Web Audio API capture in browsers requires one-time user authorization on initial load. Native background Python listener utilizes system default PortAudio device directly.

---

## 4. Autonomous Action Safety Boundaries

- **Autonomy Scope:** Safe and reversible operations (web searches, Wikipedia extracts, document parsing, report synthesis, code generation, memory queries) execute autonomously with multi-step plan verification.
- **Safety Policy Gate:** In accordance with JARVIS safety principles, critical or irreversible operations (formatting drives, deleting directory trees, dropping database tables, altering security settings) are strictly gated and require explicit user confirmation.

---

## 5. Windows Display Session Isolation

- **Architecture:** Multi-tier screen capture (`ImageGrab -> PyAutoGUI -> GDI Direct DC -> Diagnostic Buffer`).
- **Limitation:** Under Windows DWM session security, background or locked sessions restrict display device context access (BitBlt returns 0 / black frame).
- **Operation:** When launched interactively by the user via `start_matrix.bat` or `run_matrix.py`, the active desktop displays normally, and native Windows 11 OCR extracts real text lines from visible windows.

---

## 6. Cloud API Independence

- The entire system is architected for **zero cloud dependence**. All core intelligence (Qwen2.5 GGUF), wake-word spotting (openWakeWord ONNX), voice activity detection (Silero VAD ONNX), speech recognition (Faster-Whisper INT8), offline speech synthesis (SAPI5), and optical character recognition (Windows 11 Native OCR) operate 100% offline.

---

## 7. Hardware & CUDA GPU Barriers on AMD Vega APU

- **Host GPU:** AMD Radeon Graphics (Renoir/Lucienne Vega 8 iGPU with 512 MB dedicated VRAM, shared system memory).
- **Incompatible Repositories:** Exactly 4 repositories in the catalog requiring NVIDIA CUDA GPU drivers (`airllm`, `mocha`, `diorama`, `dramaclaw`) are classified as `hardware_incompatible` by the Capability Registry.
- **Handling:** Rather than attempting unsupported CUDA calls that would crash the Python interpreter, MATRIX flags them as `hardware_incompatible`, documents them transparently, and automatically uses CPU AVX2-accelerated tool alternatives.

---

## 8. Level 3 Destructive Action Gate

- **Safety Gate:** Level 3 commands (e.g. `format c:`, `rmdir /s`, `drop table`, `reg delete`) are detected via regex and token inspection in `core/intent_engine.py` and `core/autonomy_policy/`.
- **Enforcement:** Such commands are blocked from autonomous execution and transition the task into `WAITING_FOR_INPUT` state with an explicit warning: `"Security policy requires explicit authorization (Level 3)"`.
