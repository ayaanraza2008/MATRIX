"""MATRIX Repository Intelligence: Repository Analyzer.
Performs end-to-end evaluation of repositories across identity, license, security, and hardware.
"""
from typing import Dict, Any, List
from pydantic import BaseModel
from repository_engine.github_scanner import github_scanner, StarredRepository
from repository_engine.license_checker import license_checker
from repository_engine.hardware_compatibility import hardware_checker


class RepositoryAssessment(BaseModel):
    full_name: str
    html_url: str
    stars: int
    language: str
    category: str
    integration_method: str
    license_status: Dict[str, Any]
    hardware_status: Dict[str, Any]
    security_clearance: str


class RepositoryAnalyzer:
    """Evaluates repositories according to the 19-step ingestion pipeline."""

    def analyze_repository(self, repo: StarredRepository) -> RepositoryAssessment:
        lic_eval = license_checker.evaluate_license(repo.license)
        hw_eval = hardware_checker.evaluate_compatibility(repo.full_name, repo.language, repo.description)

        # Categorize
        name_low = repo.full_name.lower()
        desc_low = repo.description.lower()

        if any(k in name_low or k in desc_low for k in ["security", "hexstrike", "cyber", "kali", "nightcrawler"]):
            cat = "Security & MCP"
            method = "Method C (Controlled Tool Adapter)"
            security_clearance = "Sandboxed / Requires Explicit Consent"
        elif any(k in name_low or k in desc_low for k in ["voice", "tts", "speech", "chatterbox", "whisper", "handy"]):
            cat = "Voice & Audio"
            method = "Method A/B (Native / Local Service)"
            security_clearance = "Approved"
        elif any(k in name_low or k in desc_low for k in ["browser", "scrape", "ego-lite", "obscura"]):
            cat = "Browser & Web"
            method = "Method A/B (Native / Headless Service)"
            security_clearance = "Approved"
        elif any(k in name_low or k in desc_low for k in ["mobile", "android", "ios"]):
            cat = "Mobile & Android"
            method = "Method B (Mobile-MCP Service)"
            security_clearance = "Approved"
        elif any(k in name_low or k in desc_low for k in ["memory", "viking"]):
            cat = "Memory & Context"
            method = "Method A/B (Native / Context Engine)"
            security_clearance = "Approved"
        elif any(k in name_low or k in desc_low for k in ["free", "provider", "airllm", "strata"]):
            cat = "Free LLM Providers"
            method = "Method A (Dynamic Provider Adapter)"
            security_clearance = "Approved"
        elif any(k in name_low or k in desc_low for k in ["comfy", "design", "penpot", "video"]):
            cat = "Creative & Media"
            method = "Method B (External REST/WS Bridge)"
            security_clearance = "Approved (Resource-gated)"
        else:
            cat = "Developer Tools"
            method = "Method C (Skill Adapter)"
            security_clearance = "Approved"

        return RepositoryAssessment(
            full_name=repo.full_name,
            html_url=repo.html_url,
            stars=repo.stars,
            language=repo.language,
            category=cat,
            integration_method=method,
            license_status=lic_eval,
            hardware_status=hw_eval,
            security_clearance=security_clearance
        )

    def analyze_all(self) -> List[RepositoryAssessment]:
        repos = github_scanner.load_inventory()
        return [self.analyze_repository(r) for r in repos]


repository_analyzer = RepositoryAnalyzer()
