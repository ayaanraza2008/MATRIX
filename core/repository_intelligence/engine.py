"""MATRIX Repository Intelligence Engine.
Coordinates the autonomous discovery, multi-dimensional evaluation, selection,
gap detection, and lifecycle integration of all 65 GitHub starred repositories.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field
from core.repository_intelligence.evaluator import evaluator, RepositoryEvaluation
from core.capability_registry.registry import (
    capability_registry, ToolCapability, CapabilityMaturity, OperationSchema, ResourceRequirement
)
from core.autonomy_policy.policy import autonomy_policy, ActionCategory
from config.logging_config import get_logger

logger = get_logger("core.repo_intel.engine")


class SelectionResult(BaseModel):
    selected_tool_id: Optional[str] = None
    selected_repo: Optional[str] = None
    selected_adapter: Optional[str] = None
    target_agent: str
    category: str
    operations_to_invoke: List[str] = Field(default_factory=list)
    is_installed: bool
    requires_installation: bool
    requires_user_approval: bool
    reason: str
    compatibility_score: float = 1.0


class CapabilityGap(BaseModel):
    has_gap: bool
    required_capability: str
    suggested_repo: Optional[str] = None
    is_compatible: bool = True
    incompatibility_reason: Optional[str] = None
    alternative_suggestion: Optional[str] = None
    autonomy_level: int = 1
    can_autonomously_install: bool = True


class RepositoryIntelligenceEngine:
    """Core intelligence engine for autonomous repository discovery, selection, and capability gap analysis."""

    def __init__(self, inventory_path: Optional[Path] = None):
        self.inventory_path = inventory_path or Path("starred_repos_inventory.json")
        self._evaluations: Dict[str, RepositoryEvaluation] = {}
        self.load_and_evaluate_all()

    def load_and_evaluate_all(self) -> Dict[str, RepositoryEvaluation]:
        """Load and evaluate all 65 repositories from inventory, syncing to capability registry."""
        if not self.inventory_path.exists():
            logger.error(f"Inventory file not found at {self.inventory_path}")
            return {}

        try:
            with open(self.inventory_path, "r", encoding="utf-8") as f:
                raw_repos = json.load(f)

            for repo_dict in raw_repos:
                ev = evaluator.evaluate(repo_dict)
                self._evaluations[ev.full_name] = ev

                # Register corresponding ToolCapability into capability_registry
                cap_id = "cap_" + ev.full_name.split("/")[-1].lower().replace("-", "_")
                
                ops = [
                    OperationSchema(
                        name=op_name,
                        description=f"{op_name.replace('_', ' ').capitalize()} via {ev.full_name}",
                        risk_level=ev.security_level
                    )
                    for op_name in ev.capabilities_provided
                ]

                tool_cap = ToolCapability(
                    capability_id=cap_id,
                    name=ev.full_name.split("/")[-1],
                    description=ev.description,
                    category=ev.category,
                    source_repo=ev.full_name,
                    integration_method="adapter" if ev.maturity == CapabilityMaturity.INSTALLED else "service",
                    maturity=ev.maturity,
                    operations=ops,
                    dependencies=[ev.language],
                    permissions=["network"] if ev.requires_network else [],
                    resource_reqs=ResourceRequirement(
                        ram_mb=ev.ram_estimate_mb,
                        requires_gpu=ev.requires_cuda,
                        supports_avx2=not ev.requires_cuda
                    ),
                    health_status="healthy" if ev.maturity == CapabilityMaturity.INSTALLED else "uninstalled",
                    version="1.0.0"
                )
                capability_registry.register(tool_cap)

            logger.info(f"Evaluated and registered {len(self._evaluations)} repositories.")
            return self._evaluations
        except Exception as e:
            logger.exception(f"Error evaluating repository inventory: {e}")
            return {}

    def get_evaluation(self, full_name: str) -> Optional[RepositoryEvaluation]:
        return self._evaluations.get(full_name)

    def list_all_evaluations(self) -> List[RepositoryEvaluation]:
        return list(self._evaluations.values())

    def search_repositories(self, query: str, category: Optional[str] = None) -> List[RepositoryEvaluation]:
        """Find matching repositories based on keywords, description, or capability."""
        q = query.lower().strip()
        matched = []
        for ev in self._evaluations.values():
            if category and category != "All" and ev.category.lower() != category.lower():
                continue
            if (q in ev.full_name.lower() or
                q in ev.description.lower() or
                q in ev.language.lower() or
                any(q in cap.lower() for cap in ev.capabilities_provided)):
                matched.append(ev)
        return matched

    def select_best_tool(self, task_description: str, required_capabilities: Optional[List[str]] = None) -> SelectionResult:
        """Autonomously select the optimal repository/tool for a user task without asking the user."""
        q = task_description.lower()

        # 1. Check for specific high-value intent keywords
        candidates: List[RepositoryEvaluation] = []
        if any(w in q for w in ["browse", "web", "scrape", "search online", "url", "extract"]):
            candidates = self.search_repositories("browser", "Browser & Web")
        elif any(w in q for w in ["voice", "speak", "tts", "synthesize", "audio", "whisper", "dictation"]):
            candidates = self.search_repositories("voice", "Voice & Audio")
        elif any(w in q for w in ["security", "port", "vulnerability", "audit", "scan", "header", "cyber"]):
            candidates = self.search_repositories("security", "Security & MCP")
        elif any(w in q for w in ["code", "ast", "lint", "refactor", "syntax", "python script", "programming"]):
            candidates = self.search_repositories("coding", "Coding & DevTools")
        elif any(w in q for w in ["android", "mobile", "adb", "apk", "phone"]):
            candidates = self.search_repositories("mobile", "Mobile & Android")
        elif any(w in q for w in ["memory", "context", "history", "recall", "episodic"]):
            candidates = self.search_repositories("memory", "Memory & Context")
        elif any(w in q for w in ["diagram", "architecture", "svg", "flowchart", "penpot"]):
            candidates = self.search_repositories("creative", "Creative & Media")
        elif any(w in q for w in ["research", "paper", "scientific", "public api", "fact"]):
            candidates = self.search_repositories("research", "Research & Science")
        elif any(w in q for w in ["telemetry", "cpu", "ram", "hardware", "thermal"]):
            candidates = self.search_repositories("system", "System & Automation")
        else:
            candidates = self.search_repositories(task_description)

        if not candidates:
            # Fallback to general coding or system tools
            return SelectionResult(
                selected_tool_id="cap_ultron",
                selected_repo="AbuZar-Ansarii/Ultron",
                selected_adapter="SystemTelemetryAdapter",
                target_agent="system",
                category="System & Automation",
                operations_to_invoke=["hardware_telemetry"],
                is_installed=True,
                requires_installation=False,
                requires_user_approval=False,
                reason="Defaulted to core system telemetry for general task inspection.",
                compatibility_score=0.9
            )

        # 2. Ranking Algorithm:
        # Prioritize: Installed (100) > Available (50) > Lightweight CPU (+20) > Stars (+log stars) > Avoid GPU required (-100)
        def score(ev: RepositoryEvaluation) -> float:
            s = 0.0
            if ev.maturity == CapabilityMaturity.INSTALLED:
                s += 100.0
            elif ev.maturity == CapabilityMaturity.AVAILABLE:
                s += 50.0
            elif ev.maturity == CapabilityMaturity.REFERENCE_ONLY:
                s += 10.0
            elif ev.maturity == CapabilityMaturity.INCOMPATIBLE:
                s -= 100.0
            elif ev.maturity == CapabilityMaturity.REJECTED:
                s -= 500.0

            if "OPTIMAL_AVX2" in ev.hardware_fit or "LIGHTWEIGHT_CPU" in ev.hardware_fit:
                s += 25.0
            if ev.requires_cuda:
                s -= 80.0

            s += min(ev.stars / 10000.0, 15.0)
            return s

        candidates.sort(key=score, reverse=True)
        best = candidates[0]

        is_installed = (best.maturity == CapabilityMaturity.INSTALLED)
        needs_approval = (best.security_level >= 3)
        cap_id = "cap_" + best.full_name.split("/")[-1].lower().replace("-", "_")

        return SelectionResult(
            selected_tool_id=cap_id,
            selected_repo=best.full_name,
            selected_adapter=best.full_name.split("/")[-1] + "Adapter",
            target_agent=best.target_agent,
            category=best.category,
            operations_to_invoke=best.capabilities_provided[:2],
            is_installed=is_installed,
            requires_installation=not is_installed and best.maturity == CapabilityMaturity.AVAILABLE,
            requires_user_approval=needs_approval,
            reason=f"Selected '{best.full_name}' based on high capability match, license approval, and Ryzen 7 5700U compatibility.",
            compatibility_score=round(score(best) / 140.0, 2)
        )

    def detect_capability_gap(self, user_prompt: str) -> CapabilityGap:
        """Detect if the system lacks a needed capability, and determine if an evaluated repo can fulfill it."""
        p_low = user_prompt.lower()

        # Check for CUDA-exclusive tasks (e.g. 3D Scene Reconstruction, High-End Video Character Replacement)
        if any(w in p_low for w in ["3d scene", "single-view 3d", "diorama"]):
            return CapabilityGap(
                has_gap=True,
                required_capability="zero_shot_3d_modeling",
                suggested_repo="3dlg-hcvc/diorama",
                is_compatible=False,
                incompatibility_reason="Requires dedicated NVIDIA CUDA GPU with minimum 16GB VRAM. Ryzen 7 5700U integrated AMD Radeon graphics lacks required CUDA compute cores.",
                alternative_suggestion="Use SVG/Mermaid isometric projections or cloud-based neural rendering API instead.",
                autonomy_level=3,
                can_autonomously_install=False
            )

        if any(w in p_low for w in ["video character replacement", "mocha video", "replace person in video"]):
            return CapabilityGap(
                has_gap=True,
                required_capability="video_character_replacement",
                suggested_repo="Orange-3DV-Team/MoCha",
                is_compatible=False,
                incompatibility_reason="Requires NVIDIA PyTorch CUDA environment with >12GB GPU memory. Incompatible with CPU-only architecture.",
                alternative_suggestion="Generate multi-frame storyboard stills using lightweight SVG or cloud image synthesis APIs.",
                autonomy_level=3,
                can_autonomously_install=False
            )

        # Check for on-demand compatible install (e.g. SEO extraction, reverse engineering, geo-sleuth)
        if any(w in p_low for w in ["find photo location", "where photo taken", "geo sleuth", "openstreetmap image"]):
            return CapabilityGap(
                has_gap=True,
                required_capability="geospatial_photo_analysis",
                suggested_repo="Oldcircle/geo-sleuth",
                is_compatible=True,
                incompatibility_reason=None,
                alternative_suggestion=None,
                autonomy_level=2,
                can_autonomously_install=True
            )

        # Default: no gap or covered by existing adapters
        return CapabilityGap(
            has_gap=False,
            required_capability="native_capability",
            suggested_repo=None,
            is_compatible=True
        )

    def get_summary(self) -> Dict[str, Any]:
        """Statistical overview of repository intelligence catalog."""
        all_evals = list(self._evaluations.values())
        return {
            "total_cataloged": len(all_evals),
            "installed_adapters": sum(1 for e in all_evals if e.maturity == CapabilityMaturity.INSTALLED),
            "available_for_install": sum(1 for e in all_evals if e.maturity == CapabilityMaturity.AVAILABLE),
            "reference_only": sum(1 for e in all_evals if e.maturity == CapabilityMaturity.REFERENCE_ONLY),
            "hardware_incompatible": sum(1 for e in all_evals if e.maturity == CapabilityMaturity.INCOMPATIBLE),
            "security_rejected": sum(1 for e in all_evals if e.maturity == CapabilityMaturity.REJECTED),
            "categories": {
                cat: sum(1 for e in all_evals if e.category == cat)
                for cat in set(e.category for e in all_evals)
            }
        }


# Global repository intelligence singleton
repo_intelligence = RepositoryIntelligenceEngine()
