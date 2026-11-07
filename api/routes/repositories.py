"""MATRIX Repository Intelligence REST API Routes.
Exposes repository evaluations, autonomous tool selection, adapter management,
execution endpoints, dependency installation, and capability manifests.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from core.repository_intelligence.engine import repo_intelligence
from core.tool_adapters.manager import adapter_manager
from core.capability_registry.registry import capability_registry, CapabilityMaturity
from core.autonomous_installer.installer import autonomous_installer
from core.repository_intelligence.resource_guard import resource_guard
from core.model_manager import model_manager

router = APIRouter(prefix="/repositories", tags=["Repository Intelligence"])


class ExecuteAdapterRequest(BaseModel):
    operation: str
    parameters: Dict[str, Any] = {}
    is_user_confirmed: bool = False


class TaskSelectionRequest(BaseModel):
    task_description: str


class InstallPackageRequest(BaseModel):
    package_name: str
    version: Optional[str] = None
    is_user_confirmed: bool = False


@router.get("")
async def list_repositories(category: Optional[str] = None, search: Optional[str] = None):
    """Retrieve all 65 evaluated GitHub repositories with license, hardware, and maturity metrics."""
    if search:
        evals = repo_intelligence.search_repositories(search, category=category)
    else:
        evals = repo_intelligence.list_all_evaluations()
        if category and category != "All":
            evals = [e for e in evals if e.category.lower() == category.lower()]
    return [e.model_dump() for e in evals]


@router.get("/summary")
async def get_summary():
    """Retrieve high-level statistical summary across all 65 repositories."""
    repo_sum = repo_intelligence.get_summary()
    cap_sum = capability_registry.get_summary()
    _, _, res_metrics = resource_guard.check_headroom(0)
    return {
        "repository_catalog": repo_sum,
        "capabilities": cap_sum,
        "active_adapters_count": len(adapter_manager.list_adapters()),
        "host_headroom": res_metrics
    }


@router.get("/adapters")
async def list_adapters():
    """List all registered tool adapters, operational schemas, health status, and test metrics."""
    return adapter_manager.list_adapters()


@router.post("/adapters/{adapter_id}/execute")
async def execute_adapter(adapter_id: str, req: ExecuteAdapterRequest):
    """Execute an operation on a specific repository tool adapter."""
    res = await adapter_manager.execute(
        adapter_id=adapter_id,
        operation=req.operation,
        parameters=req.parameters,
        is_user_confirmed=req.is_user_confirmed
    )
    if not res.success and "Policy Block" in (res.error or ""):
        raise HTTPException(status_code=403, detail=res.error)
    return res.model_dump()


@router.post("/select-tool")
async def select_best_tool(req: TaskSelectionRequest):
    """Autonomously select the optimal repository and tool adapter for a task."""
    selection = repo_intelligence.select_best_tool(req.task_description)
    gap = repo_intelligence.detect_capability_gap(req.task_description)
    return {
        "selection": selection.model_dump(),
        "capability_gap": gap.model_dump()
    }


@router.post("/detect-gap")
async def detect_capability_gap(req: TaskSelectionRequest):
    """Analyze if the system lacks a capability required by the prompt."""
    return repo_intelligence.detect_capability_gap(req.task_description).model_dump()


@router.post("/install")
async def install_dependency(req: InstallPackageRequest):
    """Autonomously install a verified package within policy limits."""
    res = await autonomous_installer.install_package(
        package_name=req.package_name,
        version=req.version,
        is_user_confirmed=req.is_user_confirmed
    )
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error)
    return res.model_dump()


@router.get("/manifest")
async def get_dependency_manifest():
    """Retrieve the autonomous installer's installed package manifest."""
    return autonomous_installer.list_installed_manifest()


@router.get("/benchmarks")
async def get_benchmarks():
    """Retrieve live memory benchmarks and safe model parameter thresholds."""
    return model_manager.benchmark_memory().model_dump()
