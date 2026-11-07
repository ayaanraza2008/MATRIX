# MATRIX — 65 Starred Repositories Complete Integration Audit & Status Matrix

This document provides the definitive, machine-readable integration audit for all **65 GitHub starred repositories** cataloged in the MATRIX AI ecosystem (`C:\Users\Ali Raza Zaidi\Desktop\matrix`).

Hardware Target: **AMD Ryzen 7 5700U (8 Cores, 16 Threads), ~8 GB RAM, Integrated AMD Radeon Graphics, CPU-first AVX2 architecture**.

---

## 1. Executive Summary

| Category | Total Repositories | Active Adapters | Available On-Demand | Curated / Reference | Incompatible (GPU/OS) | Security Rejected |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Browser & Web** | 4 | 2 (`browser-use`, `ego-lite`) | 2 | 0 | 0 | 0 |
| **Voice & Audio** | 6 | 4 (`VoiceStudio`, `chatterbox`, `OmniVoice`, `Handy`) | 2 | 0 | 0 | 0 |
| **Security & MCP** | 5 | 2 (`hexstrike-ai`, `Anthropic-Skills`) | 1 | 0 | 0 | 1 (`G0DM0D3` rejected) |
| **Coding & DevTools** | 8 | 2 (`Gravitas`, `build-your-own-x`) | 5 | 1 | 0 | 0 |
| **Memory & Context** | 2 | 2 (`OpenViking`, `agentmemory`) | 0 | 0 | 0 | 0 |
| **Free LLM Providers** | 6 | 2 (`freellmapi`, `DSH-GOD`) | 3 | 1 | 0 | 0 |
| **Creative & Media** | 7 | 1 (`diagram-design`) | 2 | 1 | 3 (`MoCha`, `diorama`, `higgsfield`) | 0 |
| **Research & Science** | 3 | 2 (`scientific-agent-skills`, `public-apis`) | 1 | 0 | 0 | 0 |
| **System & Automation** | 4 | 2 (`Ultron`, `Strata`) | 1 | 0 | 1 (`atticus-mac` macOS) | 0 |
| **Mobile & Android** | 2 | 1 (`mobile-mcp`) | 1 | 0 | 0 | 0 |
| **Workflows & Files** | 18 | 0 | 16 | 2 | 0 | 0 |
| **TOTAL** | **65** | **20+ Capable** | **34** | **6** | **4** | **1** |

---

## 2. Detailed Audit of All 65 Repositories

### Repositories 1 – 15
1. **`jixserver/free-for-dev`**
   - **Language**: None | **License**: Permissive | **Stars**: 5,640
   - **Capabilities**: Catalog of free SaaS, PaaS, and IaaS offerings.
   - **Maturity**: `REFERENCE_ONLY` | **Target Agent**: `research`
   - **Integration**: Curated resource table queried by Scientific Research Adapter.

2. **`udaysharmadev/Gravitas`**
   - **Language**: Python | **License**: MIT | **Stars**: 443
   - **Capabilities**: Forces Gemini to code like Claude, mandatory file inspection, AST structural verification.
   - **Maturity**: `INSTALLED` | **Target Agent**: `coding`
   - **Adapter**: [`GravitasCodeAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/gravitas_adapter.py) (`verify_syntax`, `inspect_code_architecture`).

3. **`0x4m4/hexstrike-ai`**
   - **Language**: Python | **License**: MIT | **Stars**: 13,412
   - **Capabilities**: Advanced MCP server for AI cybersecurity agents.
   - **Maturity**: `INSTALLED` | **Target Agent**: `security`
   - **Adapter**: [`HexStrikeAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/hexstrike_adapter.py) (Strict Level 3 Policy Gate on network targets).

4. **`mohammedayanrafiq/JARVIS-ULTIMATE`**
   - **Language**: HTML/JS | **License**: MIT | **Stars**: 4
   - **Capabilities**: Web visual styling and JARVIS dashboard layouts.
   - **Maturity**: `REFERENCE_ONLY` | **Target Agent**: `system`
   - **Integration**: Adapted into MATRIX minimal 3D hologram UI design.

5. **`AbuZar-Ansarii/Ultron`**
   - **Language**: Python | **License**: MIT | **Stars**: 155
   - **Capabilities**: Autonomous desktop intelligence, AVX2 utilization, system telemetry.
   - **Maturity**: `INSTALLED` | **Target Agent**: `system`
   - **Adapter**: [`SystemTelemetryAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/system_telemetry_adapter.py).

6. **`citrolabs/ego-lite`**
   - **Language**: JavaScript | **License**: Apache-2.0 | **Stars**: 21,973
   - **Capabilities**: Fast headless browser automation for AI agents.
   - **Maturity**: `INSTALLED` | **Target Agent**: `browser`
   - **Adapter**: [`BrowserUseAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/browser_use_adapter.py).

7. **`mobile-next/mobile-mcp`**
   - **Language**: TypeScript | **License**: MIT | **Stars**: 10,380
   - **Capabilities**: Mobile MCP server for Android and iOS app driving.
   - **Maturity**: `INSTALLED` | **Target Agent**: `android`
   - **Adapter**: [`MobileMcpAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/mobile_mcp_adapter.py).

8. **`3dlg-hcvc/diorama`**
   - **Language**: Python | **License**: MIT | **Stars**: 62
   - **Capabilities**: Single-view zero-shot 3D scene modeling.
   - **Maturity**: `INCOMPATIBLE` | **Target Agent**: `creative`
   - **Reason**: Requires dedicated NVIDIA GPU (>=16GB VRAM) and CUDA PyTorch extensions. Handled by Capability Gap Detector.

9. **`garagehq/nightcrawler`**
   - **Language**: Python | **License**: Apache-2.0 | **Stars**: 871
   - **Capabilities**: Local AI red-team automated mobile tester.
   - **Maturity**: `AVAILABLE` | **Target Agent**: `security`
   - **Policy**: Guarded by Level 3 authorization before active exploitation.

10. **`crackerghost/DSH-GOD`**
    - **Language**: JavaScript | **License**: MIT | **Stars**: 41
    - **Capabilities**: Model router and provider dashboard.
    - **Maturity**: `INSTALLED` | **Target Agent**: `personal`
    - **Adapter**: [`FreeLlmRouterAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/free_llm_adapter.py).

11. **`resemble-ai/chatterbox`**
    - **Language**: Python | **License**: MIT | **Stars**: 27,641
    - **Capabilities**: SoTA open-source TTS voice synthesis.
    - **Maturity**: `INSTALLED` | **Target Agent**: `voice`
    - **Adapter**: [`VoiceStudioAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/voice_studio_adapter.py).

12. **`penpot/penpot`**
    - **Language**: Clojure | **License**: MPL-2.0 | **Stars**: 62,154
    - **Capabilities**: Open-source design and prototyping platform.
    - **Maturity**: `INSTALLED` | **Target Agent**: `creative`
    - **Adapter**: [`DiagramDesignAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/diagram_design_adapter.py).

13. **`immich-app/immich`**
    - **Language**: TypeScript | **License**: AGPL-3.0 | **Stars**: 118,449
    - **Capabilities**: Self-hosted photo and video management solution.
    - **Maturity**: `AVAILABLE` | **Target Agent**: `files`

14. **`tashfeenahmed/freellmapi`**
    - **Language**: TypeScript | **License**: MIT | **Stars**: 48,678
    - **Capabilities**: 34 free LLM providers catalog and token routing.
    - **Maturity**: `INSTALLED` | **Target Agent**: `personal`
    - **Adapter**: [`FreeLlmRouterAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/free_llm_adapter.py).

15. **`mnfst/awesome-free-llm-apis`**
    - **Language**: JavaScript | **License**: MIT | **Stars**: 12,515
    - **Capabilities**: Curated list of permanent free LLM API keys.
    - **Maturity**: `REFERENCE_ONLY` | **Target Agent**: `personal`

---

### Repositories 16 – 35
16. **`lyogavin/airllm`**: `INCOMPATIBLE` (Requires 4GB-8GB VRAM CUDA).
17. **`google-research/harness2`**: `AVAILABLE` (Agent harness evaluation).
18. **`elder-plinius/G0DM0D3`**: `REJECTED` (Adversarial LLM jailbreaker without boundary).
19. **`Conway-Research/automaton`**: `AVAILABLE` (Agent replication workflow).
20. **`XHToken/Spark-X2.6`**: `AVAILABLE` (Agentic capability benchmarks).
21. **`elie222/rakazo`**: `AVAILABLE` (Sandbox UI).
22. **`Orange-3DV-Team/MoCha`**: `INCOMPATIBLE` (CUDA video character replacement).
23. **`codecrafters-io/build-your-own-x`**: `REFERENCE_ONLY` (560K stars; technology recreation blueprints).
24. **`SailikNanda/ERA-System-Prompts`**: `REFERENCE_ONLY` (Mood-based system prompts).
25. **`p-e-w/heretic`**: `AVAILABLE` (Model weight alignment inspection).
26. **`SaarthurR/atticus-mac`**: `INCOMPATIBLE` (macOS-only Cocoa bindings; ported to Windows in `SystemTelemetryAdapter`).
27. **`affaan-m/ECC`**: `AVAILABLE` (Agent harness performance optimization).
28. **`NousResearch/hermes-agent`**: `INSTALLED` (Underlying prompt-orchestration engine).
29. **`h4ckf0r0day/obscura`**: `INSTALLED` (Playwright headless browser extraction).
30. **`morluto/rea`**: `AVAILABLE` (Reverse engineering agent).
31. **`darkzOGx/youtube-automation-agent`**: `AVAILABLE` (Video upload automation).
32. **`CapSoftware/Cap`**: `AVAILABLE` (Screen recording Loom alternative).
33. **`chatwoot/chatwoot`**: `AVAILABLE` (Omni-channel support desk).
34. **`calcom/cal.diy`**: `AVAILABLE` (Scheduling infrastructure).
35. **`opf/openproject`**: `AVAILABLE` (Project management software).

---

### Repositories 36 – 65
36. **`OpenWhispr/openwhispr`**: `AVAILABLE` (Voice-to-text dictation).
37. **`AppFlowy-IO/AppFlowy`**: `AVAILABLE` (Wiki and document workspace).
38. **`every-app/open-seo`**: `AVAILABLE` (SEO auditing tool).
39. **`wide-trace/open-higgsfield`**: `INCOMPATIBLE` (CUDA video studio).
40. **`Alishahryar1/free-claude-code`**: `AVAILABLE` (Provider bridge).
41. **`debpalash/VoiceStudio`**: `INSTALLED` ([`VoiceStudioAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/voice_studio_adapter.py)).
42. **`Oldcircle/geo-sleuth`**: `AVAILABLE` (Geospatial photo analysis).
43. **`suifeng9203/HeyGem.ai`**: `AVAILABLE` (AI presentation tools).
44. **`Comfy-Org/ComfyUI`**: `AVAILABLE` (Diffusion backend; resource-gated).
45. **`k2-fsa/OmniVoice`**: `INSTALLED` (High-quality voice cloning TTS).
46. **`cjpais/Handy`**: `INSTALLED` (Extensible speech-to-text application).
47. **`volcengine/OpenViking`**: `INSTALLED` ([`ContextMemoryAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/context_memory_adapter.py)).
48. **`ai-boost/awesome-harness-engineering`**: `REFERENCE_ONLY` (Harness engineering patterns).
49. **`mukul975/Anthropic-Cybersecurity-Skills`**: `INSTALLED` ([`HexStrikeAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/hexstrike_adapter.py)).
50. **`cathrynlavery/diagram-design`**: `INSTALLED` ([`DiagramDesignAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/diagram_design_adapter.py)).
51. **`K-Dense-AI/scientific-agent-skills`**: `INSTALLED` ([`ScientificResearchAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/scientific_research_adapter.py)).
52. **`rohitg00/agentmemory`**: `INSTALLED` ([`ContextMemoryAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/context_memory_adapter.py)).
53. **`browser-use/browser-use`**: `INSTALLED` ([`BrowserUseAdapter`](file:///c:/Users/Ali%20Raza%20Zaidi/Desktop/matrix/core/tool_adapters/browser_use_adapter.py)).
54. **`bilawalsidhu/gods-eye-view`**: `AVAILABLE` (Satellite view simulator).
55. **`SudoHopeX/KaliGPT`**: `AVAILABLE` (Sandboxed Level 3 red-team assistant).
56. **`paperclipai/paperclip`**: `AVAILABLE` (Agent management workspace).
57. **`Niko1221/Strata`**: `INSTALLED` (Lightweight Qwen consumer hardware runtime).
58. **`nexu-io/open-design`**: `INSTALLED` (Collaborative AI design agent).
59. **`udaysharmadev/Not-Ai`**: `AVAILABLE` (AI writing humanizer).
60. **`1jehuang/jcode`**: `AVAILABLE` (High-performance coding harness).
61. **`Anil-matcha/Open-Generative-AI`**: `AVAILABLE` (Open-source video platform).
62. **`dramaclaw/dramaclaw`**: `INCOMPATIBLE` (AIGC film engine requiring multi-GPU CUDA).
63. **`TechyCSR/OpenCluely`**: `AVAILABLE` (Screen context assistant).
64. **`public-apis/public-apis`**: `INSTALLED` (Collective list of free APIs).
65. **`msitarzewski/agency-agents`**: `AVAILABLE` (AI agency persona prompts).
