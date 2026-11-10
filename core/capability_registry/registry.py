"""MATRIX Machine-Readable Capability Registry.
Maintains persistent index of all repository capabilities, adapters, maturity statuses,
resource requirements, and operational schemas.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import json
from pathlib import Path
from config.logging_config import get_logger

logger = get_logger("core.capability_registry")


class CapabilityMaturity(str, Enum):
    DISCOVERED = "discovered"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    INSTALLED = "installed"
    ADAPTER_IMPLEMENTED = "adapter_implemented"
    TESTED = "tested"
    VERIFIED = "verified"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    # Legacy synonyms for backwards compatibility
    AVAILABLE = "available"
    REFERENCE_ONLY = "reference_only"
    INCOMPATIBLE = "incompatible"


class OperationSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)
    risk_level: int = 1  # 1 to 4


class ResourceRequirement(BaseModel):
    ram_mb: int = 250
    cpu_threads: int = 2
    disk_mb: int = 100
    requires_gpu: bool = False
    supports_avx2: bool = True


class ToolCapability(BaseModel):
    capability_id: str
    name: str
    description: str
    category: str
    source_repo: Optional[str] = None
    integration_method: str = "adapter"  # 'adapter', 'native', 'service', 'skill'
    maturity: CapabilityMaturity = CapabilityMaturity.AVAILABLE
    operations: List[OperationSchema] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    resource_reqs: ResourceRequirement = Field(default_factory=ResourceRequirement)
    health_status: str = "healthy"  # 'healthy', 'degraded', 'offline', 'uninstalled'
    version: str = "1.0.0"
    test_results: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CapabilityRegistry:
    """Persistent machine-readable registry and query engine for all MATRIX capabilities."""

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or (Path(__file__).parent / "capabilities_data.json")
        self._capabilities: Dict[str, ToolCapability] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """Load capabilities cache from JSON file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for k, v in raw.items():
                        self._capabilities[k] = ToolCapability(**v)
                logger.info(f"Loaded {len(self._capabilities)} capabilities from registry store.")
            except Exception as e:
                logger.error(f"Error reading capability cache: {e}")

    def save_to_disk(self) -> bool:
        """Persist capabilities cache to JSON file.

        Returns True only when the file was actually rewritten. Identical content is a
        no-op so that importing the application never dirties a tracked file.
        """
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                k: v.model_dump(mode="json")
                for k, v in self._capabilities.items()
            }
            if self.registry_file.exists():
                try:
                    with open(self.registry_file, "r", encoding="utf-8") as f:
                        if json.load(f) == serializable:
                            return False
                except (json.JSONDecodeError, OSError):
                    pass
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving capability cache: {e}")
            return False

    def register(self, cap: ToolCapability) -> bool:
        """Register or update a tool capability.

        Re-registering an identical capability is a no-op: ``last_updated`` is only
        bumped (and the file only rewritten) when something actually changed.
        """
        existing = self._capabilities.get(cap.capability_id)
        if existing is not None and existing.model_dump(exclude={"last_updated"}) == cap.model_dump(
            exclude={"last_updated"}
        ):
            return True

        cap.last_updated = datetime.now(timezone.utc)
        self._capabilities[cap.capability_id] = cap
        self.save_to_disk()
        logger.info(f"Registered capability '{cap.name}' ({cap.capability_id}) [Maturity: {cap.maturity.value}]")
        return True

    def get(self, capability_id: str) -> Optional[ToolCapability]:
        return self._capabilities.get(capability_id)

    def list_all(self, category: Optional[str] = None, maturity: Optional[CapabilityMaturity] = None) -> List[ToolCapability]:
        caps = list(self._capabilities.values())
        if category and category != "All":
            caps = [c for c in caps if c.category.lower() == category.lower()]
        if maturity:
            caps = [c for c in caps if c.maturity == maturity]
        return caps

    def search(self, query: str) -> List[ToolCapability]:
        """Perform search across capability name, description, category, and source repo."""
        q = query.lower().strip()
        matches = []
        for c in self._capabilities.values():
            if (q in c.name.lower() or
                q in c.description.lower() or
                q in c.category.lower() or
                (c.source_repo and q in c.source_repo.lower()) or
                any(q in op.name.lower() or q in op.description.lower() for op in c.operations)):
                matches.append(c)
        return matches

    def find_by_operation(self, op_name: str) -> List[ToolCapability]:
        """Find capabilities that provide a specific operation."""
        op_clean = op_name.lower().strip()
        matched = []
        for c in self._capabilities.values():
            if any(op.name.lower() == op_clean for op in c.operations):
                matched.append(c)
        return matched

    def get_summary(self) -> Dict[str, Any]:
        """Compute statistical summary of cataloged capabilities."""
        all_caps = list(self._capabilities.values())
        maturity_counts = {}
        for m in CapabilityMaturity:
            maturity_counts[m.value] = sum(1 for c in all_caps if c.maturity == m)

        category_counts = {}
        for c in all_caps:
            category_counts[c.category] = category_counts.get(c.category, 0) + 1

        return {
            "total_capabilities": len(all_caps),
            "installed_count": maturity_counts.get(CapabilityMaturity.INSTALLED.value, 0),
            "available_count": maturity_counts.get(CapabilityMaturity.AVAILABLE.value, 0),
            "reference_only_count": maturity_counts.get(CapabilityMaturity.REFERENCE_ONLY.value, 0),
            "incompatible_count": maturity_counts.get(CapabilityMaturity.INCOMPATIBLE.value, 0),
            "rejected_count": maturity_counts.get(CapabilityMaturity.REJECTED.value, 0),
            "by_maturity": maturity_counts,
            "by_category": category_counts
        }


# Global capability registry singleton
capability_registry = CapabilityRegistry()
