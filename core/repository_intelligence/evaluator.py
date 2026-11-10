"""MATRIX Repository Intelligence: Evaluator.
Performs thorough multi-dimensional evaluation of all 65 GitHub repositories:
license legality, hardware fit (Ryzen 7 5700U / 8GB RAM / CPU-only), security risk,
local vs cloud capability, and target agent assignment.
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from core.capability_registry.registry import CapabilityMaturity


class RepositoryEvaluation(BaseModel):
    full_name: str
    html_url: str
    stars: int
    language: str
    description: str
    category: str
    target_agent: str
    maturity: CapabilityMaturity
    integration_method: str  # Method A (Native Adapter), Method B (Isolated Service), Method C (Skill/Prompt), Method D (Incompatible)
    license: str
    license_verdict: str  # APPROVED, RESTRICTED, REFERENCE_ONLY
    hardware_fit: str     # OPTIMAL_AVX2, LIGHTWEIGHT_CPU, HIGH_RAM_GATED, GPU_REQUIRED_INCOMPATIBLE
    ram_estimate_mb: int
    requires_cuda: bool = False
    requires_network: bool = False
    security_level: int = 1  # 1 to 3
    security_verdict: str   # APPROVED, SANDBOXED_LEVEL2, STRICT_LEVEL3_GATE, REJECTED
    capabilities_provided: List[str] = Field(default_factory=list)


class RepositoryEvaluator:
    """Evaluates repositories according to MATRIX hardware and security constraints."""

    # CUDA / Heavy GPU repositories that cannot run natively on AMD Radeon Integrated Graphics
    GPU_REQUIRED_REPOS = {
        "Orange-3DV-Team/MoCha",
        "3dlg-hcvc/diorama",
        "lyogavin/airllm",
        "wide-trace/open-higgsfield",
        "dramaclaw/dramaclaw"
    }

    # Red-Team / Offensive Security repositories requiring Level 3 Policy Gate
    HIGH_RISK_SECURITY_REPOS = {
        "garagehq/nightcrawler",
        "SudoHopeX/KaliGPT",
        "elder-plinius/G0DM0D3",
        "0x4m4/hexstrike-ai"
    }

    # Reference / Catalog repositories that are curated resources without runnable engines
    REFERENCE_CATALOGS = {
        "jixserver/free-for-dev",
        "public-apis/public-apis",
        "mnfst/awesome-free-llm-apis",
        "ai-boost/awesome-harness-engineering",
        "codecrafters-io/build-your-own-x",
        "SailikNanda/ERA-System-Prompts"
    }

    def evaluate(self, repo: Dict[str, Any]) -> RepositoryEvaluation:
        full_name = repo.get("full_name", "")
        desc = (repo.get("description") or "").strip()
        lang = repo.get("language") or "Python"
        stars = repo.get("stars", 0)
        url = repo.get("html_url", f"https://github.com/{full_name}")
        lic_name = repo.get("license") or "MIT"

        fn_low = full_name.lower()
        desc_low = desc.lower()

        # 1. License Evaluation
        lic_low = str(lic_name).lower()
        if any(ok in lic_low for ok in ["mit", "apache", "bsd", "unlicense", "isc", "mpl"]):
            lic_verdict = "APPROVED"
        elif "gpl" in lic_low:
            lic_verdict = "RESTRICTED (Isolated Subprocess / Network API Only)"
        elif any(ref in full_name for ref in self.REFERENCE_CATALOGS):
            lic_verdict = "REFERENCE_ONLY"
        else:
            lic_verdict = "APPROVED (Open Permissive)"

        # 2. Hardware Compatibility (AMD Ryzen 7 5700U, 8GB RAM, Radeon Graphics)
        requires_cuda = full_name in self.GPU_REQUIRED_REPOS or any(k in desc_low for k in ["cuda", "gpu required", "multi-gpu"])
        ram_est = 250
        if requires_cuda:
            hw_fit = "GPU_REQUIRED_INCOMPATIBLE"
            ram_est = 8000
        elif any(k in fn_low or k in desc_low for k in ["browser", "playwright", "chromium"]):
            hw_fit = "LIGHTWEIGHT_CPU (Headless Browser ~400MB)"
            ram_est = 450
        elif any(k in fn_low or k in desc_low for k in ["tts", "whisper", "voice", "speech"]):
            hw_fit = "OPTIMAL_AVX2 (CPU Neural Inference ~300MB)"
            ram_est = 350
        elif any(k in fn_low or k in desc_low for k in ["comfy", "diffusion", "video"]):
            hw_fit = "HIGH_RAM_GATED (>6GB RAM)"
            ram_est = 6000
        else:
            hw_fit = "OPTIMAL_AVX2 (<200MB RAM)"
            ram_est = 150

        # 3. Security Risk Assessment
        if full_name in self.HIGH_RISK_SECURITY_REPOS:
            sec_level = 3
            sec_verdict = "STRICT_LEVEL3_GATE (Requires User Confirmation for Active Network/Exploit Operations)"
        elif any(k in fn_low or k in desc_low for k in ["provider", "api", "scraper", "free-claude-code"]):
            sec_level = 2
            sec_verdict = "SANDBOXED_LEVEL2 (Policy-Controlled Automation)"
        else:
            sec_level = 1
            sec_verdict = "APPROVED (Level 1 Automatic Execution)"

        # 4. Target Agent & Category Classification
        if any(k in fn_low or k in desc_low for k in ["browser", "scrape", "ego-lite", "obscura"]):
            cat = "Browser & Web"
            target_agent = "browser"
            caps = ["browse_page", "extract_content", "headless_automation", "take_screenshot"]
        elif any(k in fn_low or k in desc_low for k in ["voice", "tts", "speech", "chatterbox", "whisper", "handy", "omnivoice", "voicestudio"]):
            cat = "Voice & Audio"
            target_agent = "voice"
            caps = ["synthesize_speech", "transcribe_audio", "voice_cloning", "audio_filter"]
        elif any(k in fn_low or k in desc_low for k in ["security", "hexstrike", "cyber", "kali", "nightcrawler"]):
            cat = "Security & MCP"
            target_agent = "security"
            caps = ["port_scan", "vulnerability_audit", "mcp_defense", "payload_inspection"]
        elif any(k in fn_low or k in desc_low for k in ["mobile", "android", "ios"]):
            cat = "Mobile & Android"
            target_agent = "android"
            caps = ["adb_bridge", "mobile_mcp", "ui_hierarchy_dump", "intent_launch"]
        elif any(k in fn_low or k in desc_low for k in ["memory", "viking", "agentmemory"]):
            cat = "Memory & Context"
            target_agent = "memory"
            caps = ["episodic_storage", "vector_search", "context_retrieval", "session_cache"]
        elif any(k in fn_low or k in desc_low for k in ["freellm", "awesome-free", "free-claude-code", "airllm", "strata", "dsh-god"]):
            cat = "Free LLM Providers"
            target_agent = "personal"
            caps = ["llm_routing", "provider_fallback", "model_benchmarking", "token_budgeting"]
        elif any(k in fn_low or k in desc_low for k in ["gravitas", "jcode", "build-your-own-x", "hermes-agent", "ecc", "rea"]):
            cat = "Coding & DevTools"
            target_agent = "coding"
            caps = ["ast_linting", "code_architecture_inspection", "syntax_verification", "reverse_engineering"]
        elif any(k in fn_low or k in desc_low for k in ["penpot", "comfy", "design", "diagram", "mocha", "higgsfield", "dramaclaw"]):
            cat = "Creative & Media"
            target_agent = "creative"
            caps = ["diagram_generation", "svg_rendering", "creative_layout", "storyboarding"]
        elif any(k in fn_low or k in desc_low for k in ["scientific", "public-apis", "geo-sleuth"]):
            cat = "Research & Science"
            target_agent = "research"
            caps = ["public_api_query", "scientific_data_extraction", "fact_checking", "geo_lookup"]
        elif any(k in fn_low or k in desc_low for k in ["ultron", "atticus", "jarvis"]):
            cat = "System & Automation"
            target_agent = "system"
            caps = ["hardware_telemetry", "os_automation", "avx2_optimization", "power_management"]
        else:
            cat = "Workflow & Files"
            target_agent = "files"
            caps = ["document_workflow", "project_tracking", "file_indexing", "data_formatting"]

        # 5. Maturity Determination
        # Active verified adapters in the project
        installed_adapter_repos = {
            "browser-use/browser-use",
            "0x4m4/hexstrike-ai",
            "mobile-next/mobile-mcp",
            "udaysharmadev/Gravitas",
            "debpalash/VoiceStudio",
            "volcengine/OpenViking",
            "tashfeenahmed/freellmapi",
            "cathrynlavery/diagram-design",
            "AbuZar-Ansarii/Ultron",
            "K-Dense-AI/scientific-agent-skills"
        }

        if full_name in installed_adapter_repos:
            maturity = CapabilityMaturity.INSTALLED
            method = "Method A (Native Adapter)"
        elif full_name in self.REFERENCE_CATALOGS:
            maturity = CapabilityMaturity.REFERENCE_ONLY
            method = "Method C (Skill / Curated Knowledge)"
        elif requires_cuda or (full_name in self.GPU_REQUIRED_REPOS):
            maturity = CapabilityMaturity.INCOMPATIBLE
            method = "Method D (Hardware Incompatible - Requires Dedicated CUDA GPU)"
        elif sec_level == 3 and full_name == "elder-plinius/G0DM0D3":
            maturity = CapabilityMaturity.REJECTED
            method = "Method D (Rejected - Adversarial Jailbreak Engine without Safe Boundary)"
        else:
            maturity = CapabilityMaturity.AVAILABLE
            method = "Method B (Isolated Subprocess / On-Demand Adapter)"

        requires_network = any(k in fn_low or k in desc_low for k in ["api", "browser", "scrape", "network", "free-for-dev", "public-apis", "youtube"])

        return RepositoryEvaluation(
            full_name=full_name,
            html_url=url,
            stars=stars,
            language=lang,
            description=desc,
            category=cat,
            target_agent=target_agent,
            maturity=maturity,
            integration_method=method,
            license=lic_name,
            license_verdict=lic_verdict,
            hardware_fit=hw_fit,
            ram_estimate_mb=ram_est,
            requires_cuda=requires_cuda,
            requires_network=requires_network,
            security_level=sec_level,
            security_verdict=sec_verdict,
            capabilities_provided=caps
        )


evaluator = RepositoryEvaluator()
