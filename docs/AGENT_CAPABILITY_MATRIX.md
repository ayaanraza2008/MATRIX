# MATRIX — AGENT CAPABILITY & VERIFICATION MATRIX
**Status**: Certified 16/16 Active & Production Ready  
**Execution Environment**: AMD Ryzen 7 5700U, Windows 11  
**Reference Base**: [`agents/base_agent.py`](file:///C:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/agents/base_agent.py)  

---

## 1. Full Agent Specification Table

| # | Agent Name | Domain Description | Supported Operations | Max Autonomy | Timeout | Verification Hook | Production Status |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **1** | **Computer** | Windows 11 OS control, apps & CLI | `open`, `close`, `command`, `screenshot`, `list_windows`, `list_processes` | Level 2 | 30s | `is_process_running`, exit code | **PASS** |
| **2** | **Browser** | Headless web navigation & DOM scraping | `search_web`, `navigate_url`, `extract_text` | Level 2 | 45s | DOM text verification, HTTP 200 | **PASS** |
| **3** | **Research** | Multi-source cited intelligence | `web_research`, `compile_dossier` | Level 1 | 40s | Minimum 1 valid source URL | **PASS** |
| **4** | **Coding** | AST analysis, syntax validation, tests | `analyze_ast`, `run_tests`, `validate_syntax` | Level 2 | 30s | AST node inspection, return code | **PASS** |
| **5** | **Files** | Sandbox storage & document inspection | `list_storage_files`, `read`, `write`, `search` | Level 1 | 20s | Path validation & byte size | **PASS** |
| **6** | **Voice** | Edge TTS neural speech synthesis | `speak`, `generate_audio` | Level 0 | 25s | MP3 audio byte inspection | **PASS** |
| **7** | **Vision** | Display OCR, camera & scene density | `inspect_screen`, `capture_camera`, `analyze` | Level 1 | 30s | Valid image file on disk | **PASS** |
| **8** | **Android** | Companion pairing, alerts & sync | `pair`, `notify`, `list_devices`, `revoke` | Level 2 | 20s | SQLite device record | **PASS** |
| **9** | **System** | Kernel telemetry (CPU, RAM, threads) | `get_telemetry`, `poll_telemetry` | Level 0 | 10s | psutil hardware metrics | **PASS** |
| **10**| **Personal** | Assistant identity & direct QA | `personal_assist`, `answer` | Level 0 | 15s | Non-empty response content | **PASS** |
| **11**| **Automation** | Multi-step DAG workflows & cron | `create_workflow`, `execute_workflow` | Level 2 | 35s | Task ID & state checkpoint | **PASS** |
| **12**| **Creative** | Prompts, scripts, storyboards, diagrams | `mermaid`, `svg`, `image_prompt`, `script` | Level 2 | 20s | Valid Mermaid/SVG structure | **PASS** |
| **13**| **Memory** | User preferences & SQLite knowledge RAG | `save_memory`, `list_memory`, `delete_memory` | Level 1 | 15s | SQLite database row update | **PASS** |
| **14**| **Repo Intel**| 65-repository catalog discovery | `select_tool`, `detect_gap`, `list_catalog` | Level 1 | 25s | Adapter metadata & hardware score | **PASS** |
| **15**| **Security** | Payload audit & risk gate evaluation | `evaluate_payload`, `audit_check` | Level 3 | 15s | Risk rating 0-4 calculated | **PASS** |
| **16**| **Data Analysis**| Built-in statistics & tabular CSV | `data_status`, `analyze_csv` | Level 1 | 20s | Numerical output calculated | **PASS** |

---

## 2. Agent Architectural Guarantees

Every agent subclassing `BaseAgent` implements:
1. **Pydantic Structured Results**: Always returns typed `AgentResult(success, agent_name, action_taken, data, verification, error, execution_time_ms)`.
2. **Deterministic Timeouts**: Calls wrapped in `asyncio.wait_for` (default 30 seconds), preventing infinite hangs.
3. **Cancellation Handling**: Supports `cancel()` token, allowing instantaneous emergency stops.
4. **Post-Action Verification**: Automatically executes `verify()` before returning `success=True`.
5. **Autonomy Tier Enforcement**: Validates permitted risk level against system security level before tool dispatch.
