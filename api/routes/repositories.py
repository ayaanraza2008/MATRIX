"""MATRIX Repository Intelligence API Route.
Surfaces the audited 65 GitHub starred repositories with license, hardware, and integration assessments.
"""
from fastapi import APIRouter
from repository_engine.repository_analyzer import repository_analyzer
from core.model_manager import model_manager

router = APIRouter(prefix="/repositories", tags=["Repository Intelligence"])


@router.get("")
async def list_repositories():
    """Retrieve all 65 evaluated GitHub starred repositories with integration assessments."""
    assessments = repository_analyzer.analyze_all()
    return [a.model_dump() for a in assessments]


@router.get("/benchmarks")
async def get_benchmarks():
    """Retrieve live memory benchmarks and safe model parameter thresholds."""
    return model_manager.benchmark_memory().model_dump()
