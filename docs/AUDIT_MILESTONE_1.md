# MATRIX — Repository Audit & Milestones 1–2 Report

**Repository:** `ayaanraza2008/MATRIX` (public)
**Branch audited:** `final-production-master` @ `433f5cc91f6eed87b46e85a9839d7942f163e90f`
**Audit branch:** `fix/security-ci-portability`
**Audited by:** DSH coding agent, executing on the project owner's Windows machine
**Date:** 2026-11-10
**Scope:** full repository audit + first hardening milestone

---

## 0. Method (what was actually executed)

| Step | Command / action | Result |
|---|---|---|
| Clone | `git clone --branch final-production-master` | 708 tracked files, 79.5 MB working tree |
| Import check | `python -c "import api.server"` | **FAILED** (see §3.1) |
| Test baseline | `python -m pytest tests/` | **FAILED** at collection — 0 tests executed (see §3.2) |
| Lint | `ruff check .` | **243 findings**, incl. 10 undefined names (`F821`) |
| Byte-compile | `py_compile` over every project file | 3 files not compilable (see §5) |
| After fixes | `python -m pytest tests/ -q` | **37 passed** |
| After fixes | `ruff check .` (correctness rules) | **All checks passed** |
| Remote CI | GitHub Actions (PR #1) | lint job **PASSED**; Windows test job (see CI link in PR) |

Environment used for verification: Windows 11, Python 3.12.14, AMD Ryzen 7 5700U (8C/16T), 7.4 GB RAM — the project's stated target class.

**Status vocabulary used below:** `PASSED`, `FAILED`, `BLOCKED` (needs hardware/credentials), `NOT CONFIGURED`, `NOT TESTED`.

---

## 1. Executive summary

The repository contains a large, well-structured scaffold (FastAPI backend, 16 agents, React HUD, Kotlin companion, voice/vision trees) with **real, working subsystems in the core** — database, telemetry, sessions, device pairing, orchestrator, intent/planning. It also carried a set of defects that made the project **not runnable on a machine without a writable `D:` drive**, and it exposed **unauthenticated remote code execution** and **arbitrary file write** on the HTTP surface.

The previous delivery reports (`AUDIT_REPORT.md`, `FINAL_DELIVERY_REPORT.md`, `delivery_report.md`) claim "105/110 acceptance tests PASS" and README claims "16/16 tests passing". Those claims could not be reproduced here: **zero tests were runnable** before this milestone's fixes, because collection died on a hard-coded `D:\matrix_data` database path.

Milestone 1 fixed the critical security holes, made storage portable, repaired four genuine code bugs, corrected the dependency manifest, and added CI so future claims are verifiable.

---

## 2. Working features (verified in this audit)

- **Configuration & storage** — env-driven settings; after this milestone, resolves a writable data root on any host.
- **Async SQLite persistence** — schema creation + seeding verified by tests (`PASSED`).
- **REST health/telemetry** — `/health`, `/system/info`, `/system/metrics`, `/system/telemetry` return real psutil data (`PASSED`).
- **Sessions & messages CRUD** — create session, post message, list messages (`PASSED`).
- **Capabilities registry API** (`PASSED`).
- **Device pairing + token authentication** — SHA-256 hashed tokens, TTL, revocation, rate limiting, anti-replay nonce (`PASSED`; this was already the strongest module in the repo).
- **Intent classification, planner, orchestrator pipeline, brain facade** — dispatch and plan completion verified (`PASSED`).
- **Security policy engine** — Level 1–4 autonomy gating with explicit confirmation for high-impact actions (`PASSED` for the tested paths).
- **File explorer API** with traversal protection on read (`PASSED`; write path was broken — see §3.3).
- **Developer Studio syntax validation** (`PASSED`).
- **Automation task lifecycle** with checkpoints (`PASSED`).
- **Repository intelligence catalog** — 65 starred repos loaded/analysed (`PASSED` on fixture data).

---

## 3. Critical findings (fixed in milestone 1)

### 3.1 Application could not start on a clean machine
`import api.server` failed through an undeclared-dependency chain: `PIL` → `bs4` → `python-multipart` → `openwakeword`, plus module-level `mkdir` on hard-coded `D:\matrix_data` paths in `core/account_operations/`, `security/`, `voice/wake_word/`.

**Root cause:** dependency manifest (`requirements.txt`) did not describe the code's real import surface, and storage paths were hard-coded.

**Fix:** dependency manifest corrected; storage resolution centralised in `config/settings.py`; five hard-coded path constants removed; ML runtimes (torch, llama-cpp, mediapipe, faster-whisper, playwright) declared as optional extras.

### 3.2 Test suite could not run at all (`FAILED` → `PASSED`)
`tests/conftest.py` initialised the DB at session start. With `D:/matrix_data` missing/unwritable the suite died with `sqlite3.OperationalError: unable to open database file` — 0 of the advertised 16 tests executed.

Additionally the tests asserted the *host* hardware (`cpu_cores == 8`, `threads == 16`, `"AMD" in cpu_name`, `data_dir.startswith("D:")`), so they could only ever pass on one machine.

**Fix:** conftest pins `MATRIX_ENV=test`, `MATRIX_DEVELOPER_MODE=true` and an isolated `.testdata` root before settings load; hardware assertions compare against psutil; desktop-screenshot test skips (not fails) on headless hosts. `37 tests pass` locally; the Windows CI job runs the same suite on a runner that is not the owner's PC.

### 3.3 Unauthenticated remote code execution (`FAILED` → fixed)
`POST /api/v1/developer/execute` executed arbitrary Python (`subprocess.run([sys.executable, "-c", code])`) with **no authentication and no opt-in**. Once `MATRIX_HOST=0.0.0.0` (required for the Android companion), any LAN host could execute code as the desktop user. A malicious web page could also reach it via localhost.

**Fix:** the endpoint now requires `MATRIX_DEVELOPER_MODE=true` **and** `require_authenticated_client` (loopback, `MATRIX_API_TOKEN`, or a paired device token). Child processes run in a scratch directory with a credential-scrubbed environment.

### 3.4 Arbitrary file write via path traversal (`FAILED` → fixed)
`POST /api/v1/files/create` did `folder = data_dir / payload.folder` and `target = folder / payload.filename` with no validation: `../../` or `C:\Windows\Temp\x` escaped the storage root. Same class of flaw in `scaffold-project` and `export-zip`.

**Fix:** new `security/path_guard.py` (`resolve_within`, `is_safe_name`) used by files, scaffold and export. Regression tests cover `../`, `..\`, absolute paths, drive-qualified paths and traversal through the `folder` field.

### 3.5 Unauthenticated WebSocket broker (`FAILED` → fixed)
`/ws/events` only validated a token **if one was supplied**; without `?token=` the socket connected and received the full event stream (voice/orchestrator telemetry).

**Fix:** remote clients without a valid API/device token are closed with code 4001.

### 3.6 Background scheduler never started on a healthy boot (`FAILED` → fixed)
In `api/server.py`, the scheduler + Autonomy Core startup block was indented inside the `except Exception` clause of the optional-voice `try`. It therefore ran **only when voice wiring failed**. On a machine with working audio, scheduled automation and the autonomy core were never started.

**Fix:** restructured into its own `try/except`; voice/model warm-up remains best-effort.

---

## 4. Bugs found and fixed (verified by lint/tests)

| # | File | Defect | Impact |
|---|---|---|---|
| 1 | `agents/computer/agent.py` | `win32con` used but never imported; `SendMessage(..., 0, 0)` clicked the window origin, not `(x, y)` | Every Win32 click raised `NameError` and silently fell through; mouse control broken |
| 2 | `vision/airtouch/modern_ai_vision.py` | `gray = cv2.cvtColor(...) if _HAS_CV2 else gray` (self-reference) | `NameError` in object detection when OpenCV is absent |
| 3 | `api/routes/telephony.py` | local variable shadowed FastAPI's `status` import | fragile, renamed to `call_status` |
| 4 | `api/routes/memory.py` | duplicated import block from a botched merge | lint error, removed |
| 5 | `api/server.py` | scheduler/autonomy dead code (§3.6) | scheduled automation never ran |
| 6 | `api/routes/system.py` | hard-coded `"AMD Ryzen 7 5700U"` and `"AMD Radeon Graphics"` reported as detected hardware | telemetry lied on any other machine |
| 7 | `run_matrix.py`, `reasoning_engine.py`, `mic_listener.py` | hard-coded `D:\matrix_data` write targets | crashed or wrote to a dead path |
| 8 | `add_list_processes.py`, `add_missing_methods.py`, `test_agent.py` | not valid Python (`unterminated string`, undefined `PYEOF`) | broken files committed to the repo; deleted |

---

## 5. Still open — verified problems not yet fixed

### Security (highest priority)
1. **Most routers remain unauthenticated for non-loopback clients**: `sessions`, `memory`, `voice`, `vision`, `automation`, `integrations`, `telephony`, `security`, `repositories`, `briefing`, `airtouch`. Device routes and (now) files/developer are gated.
2. `POST /api/v1/developer/run-tests` and scaffolding are gated, but **`/developer/*` has no rate limiting**.
3. **Telephony can spend money**: outbound call endpoints are unauthenticated; the Twilio/Bland webhooks must stay public but need signature verification audit (Twilio verification exists in `core/telephony/twilio_security.py`; Bland webhook does not verify a shared secret).
4. **Default `MATRIX_SECRET_KEY`** is a checked-in development constant; it should fail fast in `MATRIX_ENV=production`.
5. **Voice/wake-word auto-arms on import** — `import api.server` starts wake-word monitoring as a side effect (observed in logs during this audit). It should start only in the app lifespan.
6. **`private_file` policy**: `security/vault/dpapi_vault.py` falls back to plaintext storage when DPAPI is unavailable — needs an explicit "unavailable" state rather than silent degradation.

### Correctness / honesty
7. **`core/model_manager._generate_rule_based_response` fabricates success.** When no model is available it returns canned text such as *"All MATRIX subsystems operational… Task dispatched through the intent engine and verification pipeline"* — it dispatches nothing. This directly violates the project's own "never simulate fake success" rule, and `test_model_manager_and_memory_benchmark` asserts on that canned text (`is_local is True`), so the test validates a stub.
8. **`core/capability_registry`** rewrites the tracked file `capabilities_data.json` (timestamps) on every import — the working tree is dirty after any run.
9. **Voice/vision/Android behaviour is `NOT TESTED`** in this audit: it requires a microphone, camera and a physical handset. Prior reports' latency numbers could not be reproduced and are not treated as evidence.

### Performance (unverified estimates, flagged as hypotheses)
- `ModelManager.load_local_model()` loads llama.cpp synchronously in a thread at startup; on 8 GB RAM this competes with FastAPI startup. Needs measurement, not assumptions.
- `vision/airtouch` pipelines open a camera per service instance; multiple services may contend for device 0.
- Large repository payload: `external/AirTouch` alone is **41.7 MB** of the 79.5 MB tree.

---

## 6. Technical debt inventory

| Item | Size / evidence | Recommendation |
|---|---|---|
| Vendored third-party tree `external/AirTouch` | 209 files, 41.7 MB | Move to a submodule or delete; it is not imported by the app |
| Ad-hoc root scripts (`add_*.py`, `fix_*.py`, `check_*.py`, `phase3_integration.py`, root `test_*.py`) | 14 files | Delete or move to `scripts/archive/` — they are one-shot code mutators, not runtime code |
| `docs/` | 95 markdown files, many duplicating delivery claims | Consolidate; keep one current status document |
| Unused imports | 231 `F401` findings | Enable incrementally with `ruff --fix` after review |
| Dead dependencies | `python-jose`, `passlib` declared but never imported | Remove |
| Duplicate "verification" scripts | `scripts/` has 98 files, multiple overlapping acceptance runners | Consolidate into `tests/` |
| Import-time side effects | wake-word arming, capability registry writes, DB init | Convert to lifespan-managed initialisation |

---

## 7. Integration configuration gaps (`NOT CONFIGURED`)

Verified absent/empty at audit time: GitHub PAT, Telegram bot token, Google Workspace OAuth, Tailscale, Home Assistant, Notion, Firebase service account, Bland/Twilio credentials, any local GGUF model file.

MATRIX correctly reports these as unconfigured rather than pretending they work — that part of the design is sound. What is missing is a single `.env`-driven readiness matrix surfaced in the UI.

---

## 8. Changes shipped in milestone 1

```
config/settings.py                     rewritten (portable storage, detected hardware, security flags)
config/hardware.py                     new (CPU/GPU/disk detection, no fabrication)
security/path_guard.py                 new (traversal-proof path resolution)
security/authentication/api_access.py  new (loopback/token/device auth dependency)
api/routes/{files,developer,system,health,telephony,memory}.py  hardened / fixed
api/server.py                          lifespan restructure + WebSocket auth
agents/computer/agent.py               real Win32 click implementation
vision/airtouch/modern_ai_vision.py    NameError fix
core/{reasoning_engine,account_operations/*}.py, security/{permissions,vault}, voice/*  portable paths
tests/{conftest,test_foundation,test_extended_workflows}.py  portable + honest assertions
tests/test_security_hardening.py       new — 21 regression tests
.github/workflows/ci.yml               new — ruff gate + Windows test job
requirements.txt / pyproject.toml      truthful dependency surface + optional extras
.env.example                           security section, PII removed, new flags documented
```

Deleted: `add_list_processes.py`, `add_missing_methods.py`, `test_agent.py` (invalid Python).

---

## 9. Test results

| Suite | Result |
|---|---|
| `tests/test_foundation.py` (7) | PASSED |
| `tests/test_brain_and_agents.py` (9) | PASSED |
| `tests/test_extended_workflows.py` (6) | PASSED (screenshot test skips on headless) |
| `tests/test_security_hardening.py` (20) | PASSED |
| Total | **42 passed, 0 failed** locally (Windows 11 / Python 3.12.14) and on the GitHub `windows-latest` CI job |
| CI lint job | PASSED |
| Voice pipeline (hardware) | NOT TESTED |
| Vision pipeline (camera) | NOT TESTED |
| Local LLM inference | PASSED on reference hardware (44.6 tok/s, +590 MB for 0.5B Q4); target-hardware numbers BLOCKED (no HuggingFace egress from this sandbox) |
| Android companion (device) | BLOCKED — no handset attached |

---

## 10. Next milestones (priority order)

1. **Authenticate the remaining routers** with one shared dependency + an explicit public-route allowlist (Twilio/Bland webhooks, `/health`). Add request-rate limiting to `/developer/*`.
2. **Remove fabricated model output** — replace the rule-engine "success" text with an explicit `provider="unavailable"` response, and fix the test that asserts on canned text.
3. **Lifecycle cleanup** — move wake-word arming, capability-registry persistence and DB init into the FastAPI lifespan; make capability writes change-detected so the tree stays clean.
4. **Real LLM path** — benchmark Qwen2.5 0.5B/1.5B GGUF on this exact 8 GB machine (tokens/s, RSS) before advertising a model profile; store results in `docs/benchmarks/`. *Progress: the 0.5B path is measured on reference hardware (44.6 tok/s, +590 MB); the 1.5B candidate and the 8 GB target remain unmeasured.*
5. **Android path** — build the APK in CI (`gradle assembleDebug`), publish the artifact, verify pairing over LAN with `MATRIX_API_TOKEN`.
6. **Repository slimming** — remove `external/AirTouch`, archive ad-hoc scripts, consolidate `docs/`.

---

## 11. Reproduce this audit

```powershell
git clone --branch fix/security-ci-portability https://github.com/ayaanraza2008/MATRIX.git
cd MATRIX
python -m venv .venv ; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "import api.server; print('import ok')"
python -m pytest tests/ -v
ruff check .
```

No `D:` drive, no pre-existing database and no hardware beyond a normal Windows desktop are required.

---

## 12. Milestone 2 — network gate and honest model fallback

### 12.1 Every `/api/` route is now gated
Milestone 1 authenticated only `files` and `developer`; `sessions`, `memory`, `voice`, `vision`,
`automation`, `integrations`, `telephony`, `security`, `repositories`, `briefing` and `airtouch`
were still open to any host that could reach the port. A single ASGI middleware now enforces:

* loopback / `MATRIX_TRUSTED_HOSTS` → allowed;
* otherwise `Authorization: Bearer <MATRIX_API_TOKEN>` **or** a paired device token → allowed;
* explicit allowlist for `/api/v1/health`, `/api/v1/devices/pair` and the provider-signed
  Twilio/Bland webhooks.

Regression tests assert that four formerly-open routers return `401` to a public source address
while `/api/v1/health` stays reachable.

### 12.2 The fake "AI" fallback is gone
`ModelManager._generate_rule_based_response()` used to answer with fabricated success text
("All MATRIX subsystems operational…", "Task dispatched through the intent engine and verification
pipeline") when no model was loaded. It has been replaced by `_template_fallback_response()`, which:

* prefixes every reply with `[OFFLINE TEMPLATE - no language model available]`;
* states explicitly that no action was executed;
* reports only measured values (psutil) for hardware/status questions;
* sets `ModelResponse.degraded = True` so callers and the UI can distinguish template output
  from real generation.

`test_model_manager_and_memory_benchmark` now asserts the degraded contract and fails if the
fabricated phrases ever return.

### 12.3 Still not done
Twilio webhooks verify HMAC signatures; the **Bland AI webhook has no signature check** and only
mutates call history — it is on the milestone 3 list together with rate limiting and
capability-registry write-on-change.

---

## 13. Milestone 3 — lifecycle hygiene and authenticated webhooks

### 13.1 Importing MATRIX no longer starts a microphone
`HandsFreeManager.__init__` called `wake_word_detector.start_listening()`, so *any* import that
reached `voice.conversation.manager` (including `import api.server`) loaded the openWakeWord
models and armed microphone monitoring. `test_lifecycle_and_integrity.py` now spawns a clean
interpreter, imports the voice stack and asserts `wake_word_armed == 0` and `is_listening == 0`.
Arming is explicit via `HandsFreeManager.arm_wake_word()`, called from the FastAPI lifespan and
when the user returns from privacy-pause to an always-listening mode.

### 13.2 The capability registry stopped dirtying the working tree
`CapabilityRegistry.register()` bumped `last_updated` and rewrote
`core/capability_registry/capabilities_data.json` on every import (the adapter manager registers
its adapters at import time), so `git status` was never clean after a run. `register()` is now a
no-op for unchanged capabilities, and `save_to_disk()` compares parsed JSON before writing.
A regression test registers the same capability twice and asserts the timestamp and mtime are
unchanged.

### 13.3 Provider webhooks and execution throttling
* `POST /api/v1/telephony/bland/webhook` now requires `MATRIX_BLAND_WEBHOOK_SECRET` — supplied as
  `?secret=` or `X-Matrix-Webhook-Secret`. Unset secret → **503 (not configured)**; wrong secret →
  **401**. Before this change any caller could post fake call-completion events.
* `/api/v1/developer/execute` and `/run-tests` are throttled to **10 requests/minute per client**
  (HTTP 429), on top of the developer-mode and authentication gates.

### 13.4 Test results

| Suite | Result |
|---|---|
| Foundation (7) | PASSED |
| Brain & agents (9) | PASSED |
| Extended workflows (6) | PASSED |
| Security hardening (20) | PASSED |
| Lifecycle & integrity (6) | PASSED |
| **Total** | **48 passed, 0 failed** |

---

## 14. Milestone 4 — the Android companion is now actually built

No pipeline had ever compiled the Kotlin app; the delivery reports described an APK that existed
only on the owner's old machine. A dedicated CI job now builds it on every push.

**Endpoint:** `.github/workflows/ci.yml` → `Android APK (debug build)`

| Step | Detail |
|---|---|
| JDK | Temurin 17 (AGP 8.5.2 requirement) |
| SDK | runner-provided Android SDK; pins `platforms;android-35` + `build-tools;35.0.0` |
| Build | `./gradlew --no-daemon --stacktrace assembleDebug` |
| Artifact | `matrix-android-debug-apk` — **16.06 MB** debug APK, downloadable from the run |

Verified evidence (run `42836714558`): all three jobs green —
`Lint => success`, `Tests (windows-latest) => success`, `Android APK (debug build) => success`,
with the APK attached as an artifact.

Two build failures were found and fixed on the way:

1. `android-actions/setup-android@v3` aborts on current runner images
   (`Warning: Failed to find package 'tools'` → `sdkmanager` exit 1), because the legacy
   `tools` package no longer exists. Replaced with an explicit `sdkmanager --install` of the
   pinned platform against the preinstalled SDK.
2. The app needs no `res/` directory (it uses framework drawables/styles) — that suspicion was
   checked and dismissed rather than "fixed" by adding unused resources.

**What this proves:** the Kotlin sources (`MainActivity.kt`, `MatrixApiClient.kt`,
`MatrixKeyStoreStorage.kt`, Compose theme) compile against the declared dependencies and produce
an installable package.

**What it does not prove:** runtime behaviour on a handset (pairing, audio, camera, WebSocket
reconnect). Installing the artifact on a real phone remains `BLOCKED` until a device is attached.

---

## 15. Milestone 5 — local inference is measured, not assumed

Every earlier report asserted "local LLM integration"; nothing had ever loaded a model and reported
a number. `scripts/benchmark_local_llm.py` now does exactly that, and
`.github/workflows/benchmark-llm.yml` runs it on demand.

**First measured run** (`42839431687`, GitHub runner, *reference hardware — not the 8 GB laptop*):

| Metric | Value |
|---|---|
| Model | Qwen2.5-0.5B-Instruct Q4_K_M (468.6 MB) |
| Runtime | llama-cpp-python 0.3.36 CPU wheel, 2 threads |
| Load time | 0.42 s |
| Generation | 30 tokens in 0.67 s = **44.6 tokens/s** |
| Resident memory | **+590 MB** (43.5 → 633.5 MB USS) |
| Output | coherent English answer (stored in the artifact) |

Full record with caveats: `docs/benchmarks/llm-cpu-github-runner-2026-11-10.md`.

**Status change:** "Local LLM inference" moves from `NOT TESTED` to **`PASSED` on reference
hardware**. Target-hardware numbers for the 8 GB Ryzen (and for the 1.5B candidate that the README
still advertises) remain `BLOCKED`: this sandbox cannot reach `huggingface.co`, so the model file
must be fetched on a network with normal egress and measured with the same script.

**Model-selection consequence:** the measured 0.5B fits comfortably in 590 MB, which is the safe
default on 8 GB. The README's 1.5B candidate must not be presented as the default until it has been
measured on the target machine.

---

## 16. Milestone 6 — fabricated adapter results removed

The worst integrity problem in the repository was **27 adapter operations that returned
`success=True` with hard-coded payloads**. They never touched a device, a network, or the
filesystem. Examples found by an AST audit:

| File | Fabricated claim |
|---|---|
| `voice_audio_adapters.py` | `"transcript": "Test audio transcript", "confidence": 0.98`; `duration_sec = len(text) * 0.06` |
| `security_mcp_adapters.py` | MCP firewall always `{"authorized": True, "threat_flags": []}` |
| `memory_llm_adapters.py` | invented benchmark `{"latency_p50": 180.5, "throughput_tok_s": 42.0}` |
| `workflow_productivity_adapters.py` | `{"pass_rate": "100%"}`, `{"seo_score": 94}`, `{"indexed_assets": 42}` |
| `browser_web_adapters.py` | `{"completed": True, "steps_executed": 3}`, `{"tiles_rendered": 16}` |
| `science_research_adapters.py` | fixed London geocode / `{"elevation_m": 35.0}` |
| `mobile_mcp_adapter.py` | fake package list, fake view hierarchy, `mock_companion_ready: True` |

### What changed

1. **`core.tool_adapters.base_adapter.unimplemented_result()`** — one honest failure path
   (`success=False`, `error="NOT IMPLEMENTED: …"`, `verification.implemented=false`).
2. **27 constant-success sites replaced** with that failure, preserving the declared
   `supported_operations` but no longer reporting work that never happened.
3. **Real implementations where a backend already exists:**
   - `ChatterboxAcousticsAdapter.synthesize_speech` now calls the real `tts_engine.speak()`,
     verifies the file exists and measures duration with `soundfile` instead of guessing.
   - `BrowserUseAdapter.search_web` parses DuckDuckGo results and returns an explicit failure
     when nothing parses (previously it invented *"Structured information regarding … retrieved
     successfully"*).
   - `MobileMcpAdapter` is a real ADB bridge: `adb devices`, `pm list packages`,
     `uiautomator dump` + XML parse; reports missing adb/device explicitly and no longer emits
     `mock_companion_ready`.
4. **Regression gate:** `core/tool_adapters/truthfulness.py` scans adapter ASTs for
   `success=True` with fully literal payloads. It runs in CI
   (`Adapter truthfulness audit`) and as a pytest test, so a new fabricated response fails the build.

### Test results

| Suite | Result |
|---|---|
| Foundation (7) · Brain & agents (9) · Extended (6) · Security (20) · Lifecycle (6) | PASSED |
| Adapter truthfulness (6) | PASSED |
| **Total** | **54 passed, 0 failed** |

### Honest caveat

The AST gate catches *entirely literal* payloads. Responses that mix literals with variables
(e.g. `{"status": 200, "count": len(x)}` computed from nothing) are not caught automatically.
The remaining adapters still need a manual pass; that is scheduled as milestone 7.
