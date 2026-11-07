# MATRIX — Autonomous Capability & Repository Intelligence Guide

This guide details the design, architecture, policy gates, adapter contracts, and execution workflows for the **MATRIX Autonomous Capability Engine**.

---

## 1. Architectural Blueprint

```
                      +---------------------------------------+
                      |             USER REQUEST              |
                      |  "Matrix, create a voice assistant"   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |       CAPABILITY GAP DETECTOR         |
                      |  Detects missing vs active tools      |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   REPOSITORY INTELLIGENCE ENGINE      |
                      |  Indexes & ranks 65 starred repos     |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      3-TIER AUTONOMY POLICY GATE      |
                      | Level 1: Auto | Level 2: Policy Gate  |
                      | Level 3: Mandatory User Authorization |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |    RESOURCE GUARD (AMD Ryzen 7 5700U)  |
                      | Checks RAM (<90%), CPU, D: Disk Space |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |        MODULAR TOOL ADAPTERS          |
                      | BrowserUse | HexStrike | VoiceStudio  |
                      | Gravitas   | OpenViking| FreeLLM      |
                      | Diagrams   | Ultron    | Science      |
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |       POST-EXECUTION VERIFICATION     |
                      | Proves output & updates SQLite audit  |
                      +---------------------------------------+
```

---

## 2. The 3-Tier Autonomy Policy

| Level | Name | Scope & Permissions | User Confirmation Required? |
| :--- | :--- | :--- | :---: |
| **LEVEL 1** | **Automatic Execution** | Searching catalog, reading docs, comparing libraries, selecting installed tools, running approved adapters, creating workspace temp files, registering verified local capabilities, retry loops. | **NO** (Fully Autonomous) |
| **LEVEL 2** | **Policy-Controlled Automation** | Installing pre-approved dependencies from verified provenance list, downloading model files under 5GB, starting background services, making outbound web requests, updating local configs within allowlists. | **NO** (Gated by Resource & Provenance rules) |
| **LEVEL 3** | **User Authorization Required** | Deleting user files, formatting drives, private credentials access, sending private data externally, financial transactions, changing security boundaries, executing untrusted binaries, offensive exploits. | **YES** (Strict Human Sign-off Required) |

---

## 3. Modular Adapter Contract

Every adapter inherits from `BaseAdapter` (`core/tool_adapters/base_adapter.py`) and exposes:

1. **`supported_operations`**: Explicit list of verbs (e.g. `["browse_page", "extract_text"]`).
2. **`input_schema`**: Typed JSON-schema of arguments.
3. **`output_schema`**: Typed JSON-schema of return structures.
4. **`resource_requirements`**: Memory footprint (MB), CPU threads, GPU requirement.
5. **`permission_requirements`**: Security capabilities needed (`network`, `filesystem_read`, `system_metrics`).
6. **`execute(operation, parameters)`**: Main execution hook with timing.
7. **`verify_result(operation, result)`**: Post-execution check proving real-world outcome.

---

## 4. Hardware Optimization Guidelines

- **CPU-First AVX2**: All local neural models (faster-whisper, openWakeWord, Qwen2.5 GGUF) run strictly with AVX2 vectorization.
- **RAM Budgeting**: Host system has ~8GB RAM. High-risk GPU repositories requiring CUDA (>12GB VRAM like MoCha or Diorama) are classified as `INCOMPATIBLE` by the Capability Gap Detector, providing transparent explanations and CPU-friendly alternatives.
- **Storage**: All models, virtual environments, tool caches, and SQLite databases persist under `D:\matrix_data\`.
