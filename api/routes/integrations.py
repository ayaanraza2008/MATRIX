"""MATRIX Integration Dashboard REST API.
Endpoint: /api/v1/integrations
Provides a real-time management dashboard covering all 65 GitHub repositories:
- Statuses: ACTIVE, AVAILABLE, INITIALIZING, DISABLED, INCOMPATIBLE, BLOCKED, FAILED
- Capabilities provided & health telemetry
- Dynamic resource telemetry (RAM, CPU) via AutonomousResourceManager
- Quick actions: Initialize, Test, Shutdown, View Docs
- Enable/disable toggles
"""
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from core.repository_intelligence.engine import repo_intelligence
from core.tool_adapters.manager import adapter_manager
from core.capability_registry.registry import capability_registry, CapabilityMaturity
from core.resource_manager import resource_manager
from core.repository_intelligence.hardware_guard import hardware_guard
from core.reference_knowledge.engine import reference_knowledge_engine
from config.logging_config import get_logger

logger = get_logger("api.integrations")

router = APIRouter(prefix="/integrations", tags=["Integration Dashboard"])

# In-memory toggle state for integrations
_integration_toggles: Dict[str, bool] = {}


class ToggleRequest(BaseModel):
    enabled: bool


class TestIntegrationRequest(BaseModel):
    operation: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def get_all_integrations():
    """Retrieve full dashboard inventory across all 65 GitHub repositories."""
    evals = repo_intelligence.list_all_evaluations()
    res_status = resource_manager.get_status_report()
    adapters_by_repo = {adp.source_repo: adp for adp in adapter_manager._adapters.values()}

    items = []
    for ev in evals:
        repo_name = ev.full_name
        adapter = adapters_by_repo.get(repo_name)
        enabled = _integration_toggles.get(repo_name, True)

        # Determine integration status
        if ev.maturity == CapabilityMaturity.REJECTED:
            status = "BLOCKED"
            health = "blocked"
            status_reason = "Security Rejected: Adversarial jailbreak and exploit framework."
        elif ev.maturity == CapabilityMaturity.INCOMPATIBLE:
            status = "INCOMPATIBLE"
            health = "incompatible"
            status_reason = "Requires NVIDIA CUDA GPU (>12GB VRAM). CPU fallback active."
        elif not enabled:
            status = "DISABLED"
            health = "disabled"
            status_reason = "Integration manually disabled by operator."
        elif ev.maturity == CapabilityMaturity.INSTALLED:
            status = "ACTIVE"
            health = adapter.health_status if adapter else "healthy"
            status_reason = "Core Active Integration"
        elif ev.maturity == CapabilityMaturity.REFERENCE_ONLY:
            status = "AVAILABLE"
            health = "healthy"
            status_reason = "Indexed in MATRIX Reference Knowledge Base."
        elif ev.maturity == CapabilityMaturity.AVAILABLE:
            if adapter:
                status = "ACTIVE"
                health = adapter.health_status
                status_reason = "Adapter loaded and ready for autonomous invocation."
            else:
                status = "AVAILABLE"
                health = "standby"
                status_reason = "Available on demand."
        else:
            status = "AVAILABLE"
            health = "standby"
            status_reason = "Available"

        # Resource consumption
        req = adapter.resource_requirements if adapter else {
            "ram_mb": ev.ram_estimate_mb,
            "cpu_threads": 1,
            "requires_gpu": ev.requires_cuda
        }

        # Last tested
        test_info = adapter.test_results if adapter else {}

        items.append({
            "repo_name": repo_name,
            "category": ev.category,
            "status": status,
            "status_reason": status_reason,
            "adapter_id": adapter.adapter_id if adapter else None,
            "capabilities": ev.capabilities_provided,
            "health_status": health,
            "resource_consumption": {
                "estimated_ram_mb": req.get("ram_mb", 100),
                "cpu_threads": req.get("cpu_threads", 1),
                "requires_gpu": req.get("requires_gpu", False)
            },
            "last_used": test_info.get("last_tested"),
            "error_log": None if health != "degraded" else "Degraded operation log",
            "quick_actions": ["initialize", "test", "shutdown", "view_docs"],
            "enabled": enabled,
            "license": ev.license,
            "stars": ev.stars
        })

    return {
        "total_repositories": len(items),
        "status_breakdown": {
            "ACTIVE": sum(1 for i in items if i["status"] == "ACTIVE"),
            "AVAILABLE": sum(1 for i in items if i["status"] == "AVAILABLE"),
            "INCOMPATIBLE": sum(1 for i in items if i["status"] == "INCOMPATIBLE"),
            "BLOCKED": sum(1 for i in items if i["status"] == "BLOCKED"),
            "DISABLED": sum(1 for i in items if i["status"] == "DISABLED"),
            "FAILED": sum(1 for i in items if i["status"] == "FAILED"),
        },
        "resource_manager": res_status,
        "integrations": items
    }


@router.get("/summary")
async def get_integrations_summary():
    """Summary metrics of all integrations."""
    data = await get_all_integrations()
    return {
        "total_repositories": data["total_repositories"],
        "status_breakdown": data["status_breakdown"],
        "resource_manager": data["resource_manager"]
    }


@router.post("/{repo_owner}/{repo_name}/toggle")
async def toggle_integration(repo_owner: str, repo_name: str, req: ToggleRequest):
    """Enable or disable a specific repository integration."""
    full_name = f"{repo_owner}/{repo_name}"
    _integration_toggles[full_name] = req.enabled
    return {"repo_name": full_name, "enabled": req.enabled, "status": "UPDATED"}


@router.post("/{repo_owner}/{repo_name}/test")
async def test_integration(repo_owner: str, repo_name: str, req: TestIntegrationRequest):
    """Trigger a live diagnostic test execution on a repository integration."""
    full_name = f"{repo_owner}/{repo_name}"
    adapter = adapter_manager.get_by_repo(full_name)
    if not adapter:
        # Check if reference repository
        ref_results = reference_knowledge_engine.query_reference_catalog(repo_name, limit=1)
        if ref_results.get("total_matches", 0) > 0:
            return {
                "repo_name": full_name,
                "type": "reference_knowledge",
                "success": True,
                "data": ref_results["results"][0]
            }
        # Check if hardware incompatible
        assess = hardware_guard.assess_repository(full_name)
        if assess:
            return {
                "repo_name": full_name,
                "type": "hardware_incompatible",
                "success": True,
                "assessment": assess.model_dump()
            }
        raise HTTPException(status_code=404, detail=f"No adapter or catalog entry for {full_name}")

    op = req.operation or (adapter.supported_operations[0] if adapter.supported_operations else "check_health")
    res = await adapter_manager.execute(adapter.adapter_id, op, req.parameters, is_user_confirmed=True)
    return {
        "repo_name": full_name,
        "adapter_id": adapter.adapter_id,
        "operation": op,
        "success": res.success,
        "data": res.data,
        "execution_time_ms": res.execution_time_ms,
        "error": res.error
    }


@router.get("/marketplace/all")
async def get_universal_marketplace(category: Optional[str] = None):
    """Retrieve full catalog of Universal Connectors (OS, Productivity, Communication, Information, IoT)."""
    from core.integrations.manager import integration_manager
    items = integration_manager.list_integrations(category=category)
    return {
        "status": "OK",
        "total_integrations": len(items),
        "connected_count": sum(1 for i in items if i["status"] == "CONNECTED"),
        "integrations": items
    }


@router.post("/marketplace/{integration_id}/test")
async def test_universal_integration(integration_id: str):
    """Trigger a live operational health test against a Universal Connector."""
    from core.integrations.manager import integration_manager
    res = await integration_manager.test_integration(integration_id)
    return res
